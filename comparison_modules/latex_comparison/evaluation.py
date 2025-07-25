import sys
import os
import re
import json
import time
import shutil
import argparse
import numpy as np
import matplotlib.pyplot as plt

from tqdm import tqdm
from datetime import datetime
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool 
from PIL import Image, ImageDraw
from skimage.measure import ransac

from modules.latex2bbox_color import latex2bbox_color
from modules.tokenize_latex.tokenize_latex import tokenize_latex
from modules.visual_matcher import HungarianMatcher, SimpleAffineTransform


def gen_color_list(num=10, gap=15):
    num += 1
    single_num = 255 // gap + 1
    max_num = single_num ** 3
    num = min(num, max_num)
    color_list = []
    for idx in range(num):
        R = idx // single_num**2
        GB = idx % single_num**2
        G = GB // single_num
        B = GB % single_num
        
        color_list.append((R*gap, G*gap, B*gap))
    return color_list[1:]

def update_inliers(ori_inliers, sub_inliers):
    inliers = np.copy(ori_inliers)
    sub_idx = -1
    for idx in range(len(ori_inliers)):
        if ori_inliers[idx] == False:
            sub_idx += 1
            if sub_inliers[sub_idx] == True:
                inliers[idx] = True
    return inliers

def reshape_inliers(ori_inliers, sub_inliers):
    inliers = np.copy(ori_inliers)
    sub_idx = -1
    for idx in range(len(ori_inliers)):
        if ori_inliers[idx] == False:
            sub_idx += 1
            if sub_inliers[sub_idx] == True:
                inliers[idx] = True
        else:
            inliers[idx] = False
    return inliers

def gen_token_order(box_list):
    new_box_list = copy.deepcopy(box_list)
    for idx, box in enumerate(new_box_list):
        new_box_list[idx]['order'] = idx / len(new_box_list)
    return new_box_list

def evaluation(data_root):#, user_id="test"):
    # data_root = os.path.join(data_root, user_id)
    bbox_dir = os.path.join(data_root, "bbox")
    gt_box_dir = os.path.join(data_root, "gt")
    pred_box_dir = os.path.join(data_root, "pred")
    match_vis_dir = os.path.join(data_root, "vis_match")
    os.makedirs(match_vis_dir, exist_ok=True)
    os.makedirs(bbox_dir,exist_ok=True)
    
    max_iter = 3
    min_samples = 3
    residual_threshold = 25
    max_trials = 50
    
    metrics_per_img = {}
    gt_basename_list = [item.split(".jsonl")[0] for item in os.listdir(os.path.join(gt_box_dir, 'bbox'))]
    # print('gt_basename_list', gt_basename_list)
    for basename in tqdm(gt_basename_list):
        # print(basename)
        # print(os.path.join(gt_box_dir, 'bbox', basename+".jsonl"))
        gt_valid, pred_valid = True, True
        if not os.path.exists(os.path.join(gt_box_dir, 'bbox', basename+".jsonl")):
            gt_valid = False
        else:
            with open(os.path.join(gt_box_dir, 'bbox', basename+".jsonl"), 'r') as f:
                box_gt = []
                for line in f:
                    info = json.loads(line)
                    if info['bbox']:
                        box_gt.append(info)
            # print('box_gt', box_gt)
            if not box_gt:
                gt_valid = False
        if not gt_valid:
            continue
        
        if not os.path.exists(os.path.join(pred_box_dir, 'bbox', basename+".jsonl")):
            pred_valid = False
        else:
            with open(os.path.join(pred_box_dir, 'bbox', basename+".jsonl"), 'r') as f:
                box_pred = []
                for line in f:
                    info = json.loads(line)
                    if info['bbox']:
                        box_pred.append(info)
            if not box_pred:
                pred_valid = False
        if not pred_valid:
            metrics_per_img[basename] = {
                "recall": 0,
                "precision": 0,
                "F1_score": 0,
            }
            continue       
        gt_img_path = os.path.join(gt_box_dir, 'vis', basename+"_base.png")
        pred_img_path = os.path.join(pred_box_dir, 'vis', basename+"_base.png")
        
        img_gt = Image.open(gt_img_path)
        img_pred = Image.open(pred_img_path)
        
        matcher = HungarianMatcher()
        matched_idxes = matcher(box_gt, box_pred, img_gt.size, img_pred.size)
        src = []
        dst = []
        for (idx1, idx2) in matched_idxes:
            x1min, y1min, x1max, y1max = box_gt[idx1]['bbox']
            x2min, y2min, x2max, y2max = box_pred[idx2]['bbox']
            x1_c, y1_c = float((x1min+x1max)/2), float((y1min+y1max)/2)
            x2_c, y2_c = float((x2min+x2max)/2), float((y2min+y2max)/2)
            src.append([y1_c, x1_c])
            dst.append([y2_c, x2_c])
            
        src = np.array(src)
        dst = np.array(dst)
        if src.shape[0] <= min_samples:
            inliers = np.array([True for _ in matched_idxes])
        else:
            inliers = np.array([False for _ in matched_idxes])
            for i in range(max_iter):
                if src[inliers==False].shape[0] <= min_samples:
                    break
                model, inliers_1 = ransac((src[inliers==False], dst[inliers==False]), SimpleAffineTransform, min_samples=min_samples, residual_threshold=residual_threshold, max_trials=max_trials, random_state=42)
                if inliers_1 is not None and inliers_1.any():
                    inliers = update_inliers(inliers, inliers_1)
                else:
                    break
                if len(inliers[inliers==True]) >= len(matched_idxes):
                    break

        for idx, (a,b) in enumerate(matched_idxes):
            if inliers[idx] == True and matcher.cost['token'][a, b] == 1:
                inliers[idx] = False
        
        final_match_num = len(inliers[inliers==True])
        recall = round(final_match_num/(len(box_gt)), 3)
        precision = round(final_match_num/(len(box_pred)), 3)
        F1_score = round(2*final_match_num/(len(box_gt)+len(box_pred)), 3)
        metrics_per_img[basename] = {
            "recall": recall,
            "precision": precision,
            "F1_score": F1_score,
        }
        
        if True:
            gap = 5
            W1, H1 = img_gt.size
            W2, H2 = img_pred.size
            H = H1 + H2 + gap
            W = max(W1, W2)

            vis_img = Image.new('RGB', (W, H), (255, 255, 255))
            vis_img.paste(img_gt, (0, 0))
            vis_img.paste(Image.new('RGB', (W, gap), (120, 120, 120)), (0, H1))
            vis_img.paste(img_pred, (0, H1+gap))
            
            match_img = vis_img.copy()
            match_draw = ImageDraw.Draw(match_img)

            gt_matched_idx = {
                a: flag
                for (a,b), flag in 
                zip(matched_idxes, inliers)
            }
            pred_matched_idx = {
                b: flag
                for (a,b), flag in 
                zip(matched_idxes, inliers)
            }
            
            for idx, box in enumerate(box_gt):
                if idx in gt_matched_idx and gt_matched_idx[idx]==True:
                    color = "green"
                else:
                    color = "red"
                x_min, y_min, x_max, y_max = box['bbox']
                match_draw.rectangle([x_min-1, y_min-1, x_max+1, y_max+1], fill=None, outline=color, width=2)
                
            for idx, box in enumerate(box_pred):
                if idx in pred_matched_idx and pred_matched_idx[idx]==True:
                    color = "green"
                else:
                    color = "red"
                x_min, y_min, x_max, y_max = box['bbox']
                match_draw.rectangle([x_min-1, y_min-1+H1+gap, x_max+1, y_max+1+H1+gap], fill=None, outline=color, width=2)
            
            vis_img.save(os.path.join(match_vis_dir, basename+"_base.png"))
            match_img.save(os.path.join(match_vis_dir, basename+".png"))
     
    # print('metrics_per_img', metrics_per_img)
    score_list = [val['F1_score'] for _, val in metrics_per_img.items()]
    exp_list = [1 if score==1 else 0 for score in score_list]
    metrics_res = {
        "mean_score": round(np.mean(score_list), 3),
        "exp_rate": round(np.mean(exp_list), 3),
        "details": metrics_per_img
    }
    metric_res_path = os.path.join(data_root, "metrics_res.json")
    with open(metric_res_path, "w") as f:
        f.write(json.dumps(metrics_res, indent=2))
    return metrics_res, metric_res_path, match_vis_dir


def batch_evaluation(data_root,file1,file2):
    with open(file1, 'r', encoding='utf-8') as f1:
        list1 = f1.readlines()
    with open(file2, 'r', encoding='utf-8') as f2:
        list2 = f2.readlines()
    bbox_dir = os.path.join(data_root, "bbox")
    vis_dir = os.path.join(data_root, "vis")
    match_vis_dir = os.path.join(data_root, "vis_match")
    os.makedirs(match_vis_dir, exist_ok=True)

    max_iter = 3
    min_samples = 3
    residual_threshold = 25
    max_trials = 50

    list1 = [
        next(iter(json.loads(item).items()))[0].replace('\\', '_')
        for item in list1
    ]
    list2 = [
        next(iter(json.loads(item).items()))[0].replace('\\', '_')
        for item in list2
    ]

    gt_list = [a for a in list1 for b in list2]
    pred_list = [b for a in list1 for b in list2]

    print(f"文件1包含公式{len(list1)},文件2包含公式{len(list2)},对比的公式个数应该是:{len(list1)*len(list2)},实际为:{len(gt_list)}")
    metrics_per_img = {}
    for i, gt_item in enumerate(tqdm(gt_list)):
        pred_item = pred_list[i]
        gt_valid, pred_valid = True, True
        gt_item_bbox_file_path = os.path.join(bbox_dir, gt_item+".jsonl")
        pred_item_bbox_file_path = os.path.join(bbox_dir, pred_item+'.jsonl')
        if not os.path.exists(gt_item_bbox_file_path):
            gt_valid = False
        else:
            with open(gt_item_bbox_file_path, 'r') as f:
                box_gt = []
                for line in f:
                    info = json.loads(line)
                    if info['bbox']:
                        box_gt.append(info)
            # print('box_gt', box_gt)
            if not box_gt:
                gt_valid = False
        if not gt_valid:
            continue

        if not os.path.exists(pred_item_bbox_file_path):
            pred_valid = False
        else:
            with open(pred_item_bbox_file_path, 'r') as f:
                box_pred = []
                for line in f:
                    info = json.loads(line)
                    if info['bbox']:
                        box_pred.append(info)
            if not box_pred:
                pred_valid = False
        if not pred_valid:
            metrics_per_img[i] = {
                "recall": 0,
                "precision": 0,
                "F1_score": 0,
            }
            continue
        gt_img_path = os.path.join(vis_dir, gt_item + "_base.png")
        pred_img_path = os.path.join(vis_dir, pred_item + "_base.png")

        img_gt = Image.open(gt_img_path)
        img_pred = Image.open(pred_img_path)

        matcher = HungarianMatcher()
        matched_idxes = matcher(box_gt, box_pred, img_gt.size, img_pred.size)
        src = []
        dst = []
        for (idx1, idx2) in matched_idxes:
            x1min, y1min, x1max, y1max = box_gt[idx1]['bbox']
            x2min, y2min, x2max, y2max = box_pred[idx2]['bbox']
            x1_c, y1_c = float((x1min + x1max) / 2), float((y1min + y1max) / 2)
            x2_c, y2_c = float((x2min + x2max) / 2), float((y2min + y2max) / 2)
            src.append([y1_c, x1_c])
            dst.append([y2_c, x2_c])

        src = np.array(src)
        dst = np.array(dst)
        if src.shape[0] <= min_samples:
            inliers = np.array([True for _ in matched_idxes])
        else:
            inliers = np.array([False for _ in matched_idxes])
            for i in range(max_iter):
                if src[inliers == False].shape[0] <= min_samples:
                    break
                model, inliers_1 = ransac((src[inliers == False], dst[inliers == False]), SimpleAffineTransform,
                                          min_samples=min_samples, residual_threshold=residual_threshold,
                                          max_trials=max_trials, random_state=42)
                if inliers_1 is not None and inliers_1.any():
                    inliers = update_inliers(inliers, inliers_1)
                else:
                    break
                if len(inliers[inliers == True]) >= len(matched_idxes):
                    break

        for idx, (a, b) in enumerate(matched_idxes):
            if inliers[idx] == True and matcher.cost['token'][a, b] == 1:
                inliers[idx] = False

        final_match_num = len(inliers[inliers == True])
        recall = round(final_match_num / (len(box_gt)), 3)
        precision = round(final_match_num / (len(box_pred)), 3)
        F1_score = round(2 * final_match_num / (len(box_gt) + len(box_pred)), 3)
        metrics_per_img[i] = {
            "recall": recall,
            "precision": precision,
            "F1_score": F1_score,
        }

        if True:
            gap = 5
            W1, H1 = img_gt.size
            W2, H2 = img_pred.size
            H = H1 + H2 + gap
            W = max(W1, W2)

            vis_img = Image.new('RGB', (W, H), (255, 255, 255))
            vis_img.paste(img_gt, (0, 0))
            vis_img.paste(Image.new('RGB', (W, gap), (120, 120, 120)), (0, H1))
            vis_img.paste(img_pred, (0, H1 + gap))

            match_img = vis_img.copy()
            match_draw = ImageDraw.Draw(match_img)

            gt_matched_idx = {
                a: flag
                for (a, b), flag in
                zip(matched_idxes, inliers)
            }
            pred_matched_idx = {
                b: flag
                for (a, b), flag in
                zip(matched_idxes, inliers)
            }

            for idx, box in enumerate(box_gt):
                if idx in gt_matched_idx and gt_matched_idx[idx] == True:
                    color = "green"
                else:
                    color = "red"
                x_min, y_min, x_max, y_max = box['bbox']
                match_draw.rectangle([x_min - 1, y_min - 1, x_max + 1, y_max + 1], fill=None, outline=color, width=2)

            for idx, box in enumerate(box_pred):
                if idx in pred_matched_idx and pred_matched_idx[idx] == True:
                    color = "green"
                else:
                    color = "red"
                x_min, y_min, x_max, y_max = box['bbox']
                match_draw.rectangle([x_min - 1, y_min - 1 + H1 + gap, x_max + 1, y_max + 1 + H1 + gap], fill=None,
                                     outline=color, width=2)

            vis_img.save(os.path.join(match_vis_dir, str(i) + "_base.png"))
            match_img.save(os.path.join(match_vis_dir, str(i) + ".png"))

    # print('metrics_per_img', metrics_per_img)
    score_list = [val['F1_score'] for _, val in metrics_per_img.items()]
    exp_list = [1 if score == 1 else 0 for score in score_list]
    metrics_res = {
        "mean_score": round(np.mean(score_list), 3),
        "exp_rate": round(np.mean(exp_list), 3),
        "details": metrics_per_img
    }
    metric_res_path = os.path.join(data_root, "metrics_res.json")
    with open(metric_res_path, "w") as f:
        f.write(json.dumps(metrics_res, indent=2))
    return metrics_res, metric_res_path, match_vis_dir,gt_list,pred_list


def process_one_pair(args):
    i, gt_item, pred_item, data_root, min_samples, residual_threshold, max_trials, max_iter = args
    bbox_dir = os.path.join(data_root, "bbox")
    vis_dir = os.path.join(data_root, "vis")
    match_vis_dir = os.path.join(data_root, "vis_match")

    gt_item_bbox_file_path = os.path.join(bbox_dir, gt_item + ".jsonl")
    pred_item_bbox_file_path = os.path.join(bbox_dir, pred_item + '.jsonl')

    # 处理GT bbox
    if not os.path.exists(gt_item_bbox_file_path):
        return i, {"recall": 0, "precision": 0, "F1_score": 0}
    with open(gt_item_bbox_file_path, 'r') as f:
        box_gt = [json.loads(line) for line in f if json.loads(line).get('bbox')]
    if not box_gt:
        return i, {"recall": 0, "precision": 0, "F1_score": 0}

    # 处理Pred bbox
    if not os.path.exists(pred_item_bbox_file_path):
        return i, {"recall": 0, "precision": 0, "F1_score": 0}
    with open(pred_item_bbox_file_path, 'r') as f:
        box_pred = [json.loads(line) for line in f if json.loads(line).get('bbox')]
    if not box_pred:
        return i, {"recall": 0, "precision": 0, "F1_score": 0}

    # 加载图像
    gt_img_path = os.path.join(vis_dir, gt_item + "_base.png")
    pred_img_path = os.path.join(vis_dir, pred_item + "_base.png")
    img_gt = Image.open(gt_img_path)
    img_pred = Image.open(pred_img_path)

    # 匈牙利匹配
    matcher = HungarianMatcher()
    matched_idxes = matcher(box_gt, box_pred, img_gt.size, img_pred.size)

    # 准备RANSAC数据
    src, dst = [], []
    for (idx1, idx2) in matched_idxes:
        x1min, y1min, x1max, y1max = box_gt[idx1]['bbox']
        x2min, y2min, x2max, y2max = box_pred[idx2]['bbox']
        src.append([(x1min + x1max) / 2, (y1min + y1max) / 2])
        dst.append([(x2min + x2max) / 2, (y2min + y2max) / 2])

    src = np.array(src)
    dst = np.array(dst)

    if src.shape[0] <= min_samples:
        inliers = np.array([True for _ in matched_idxes])
    else:
        inliers = np.array([False for _ in matched_idxes])
        for i in range(max_iter):
            if src[inliers == False].shape[0] <= min_samples:
                break
            model, inliers_1 = ransac((src[inliers == False], dst[inliers == False]), SimpleAffineTransform,
                                      min_samples=min_samples, residual_threshold=residual_threshold,
                                      max_trials=max_trials, random_state=42)
            if inliers_1 is not None and inliers_1.any():
                inliers = update_inliers(inliers, inliers_1)
            else:
                break
            if len(inliers[inliers == True]) >= len(matched_idxes):
                break

    # 过滤无效匹配
    for idx, (a, b) in enumerate(matched_idxes):
        if inliers[idx] and matcher.cost['token'][a, b] == 1:
            inliers[idx] = False

    # 计算指标
    final_match_num = np.sum(inliers)
    recall = final_match_num / len(box_gt)
    precision = final_match_num / len(box_pred)
    F1_score = 2 * final_match_num / (len(box_gt) + len(box_pred)) if (len(box_gt) + len(box_pred)) > 0 else 0

    # 可视化（可选）
    gap = 5
    W1, H1 = img_gt.size
    W2, H2 = img_pred.size
    H = H1 + H2 + gap
    W = max(W1, W2)
    vis_img = Image.new('RGB', (W, H), (255, 255, 255))
    vis_img.paste(img_gt, (0, 0))
    vis_img.paste(Image.new('RGB', (W, gap), (120, 120, 120)), (0, H1))
    vis_img.paste(img_pred, (0, H1 + gap))

    match_img = vis_img.copy()
    match_draw = ImageDraw.Draw(match_img)

    gt_matched_idx = {
        a: flag
        for (a, b), flag in
        zip(matched_idxes, inliers)
    }
    pred_matched_idx = {
        b: flag
        for (a, b), flag in
        zip(matched_idxes, inliers)
    }

    for idx, box in enumerate(box_gt):
        if idx in gt_matched_idx and gt_matched_idx[idx] == True:
            color = "green"
        else:
            color = "red"
        x_min, y_min, x_max, y_max = box['bbox']
        match_draw.rectangle([x_min - 1, y_min - 1, x_max + 1, y_max + 1], fill=None, outline=color, width=2)

    for idx, box in enumerate(box_pred):
        if idx in pred_matched_idx and pred_matched_idx[idx] == True:
            color = "green"
        else:
            color = "red"
        x_min, y_min, x_max, y_max = box['bbox']
        match_draw.rectangle([x_min - 1, y_min - 1 + H1 + gap, x_max + 1, y_max + 1 + H1 + gap], fill=None,
                             outline=color, width=2)
    os.makedirs(match_vis_dir, exist_ok=True)
    match_img.save(os.path.join(match_vis_dir, f"{i}.png"))
    vis_img.save(os.path.join(match_vis_dir, f"{i}_base.png"))

    return i, {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "F1_score": round(F1_score, 3)
    }


def batch_evaluation_multiple_pools(data_root, file1, file2):
    with open(file1, 'r', encoding='utf-8') as f1:
        list1 = [next(iter(json.loads(item).items()))[0].replace('\\', '_') for item in f1]
    with open(file2, 'r', encoding='utf-8') as f2:
        list2 = [next(iter(json.loads(item).items()))[0].replace('\\', '_') for item in f2]

    # 创建笛卡尔积
    gt_list = [a for a in list1 for b in list2]
    pred_list = [b for a in list1 for b in list2]
    print(f"文件1包含公式{len(list1)}, 文件2包含公式{len(list2)}, 对比公式数: {len(gt_list)}")

    # 准备多进程参数
    tasks = []
    for i, (gt_item, pred_item) in enumerate(zip(gt_list, pred_list)):
        tasks.append((
            i, gt_item, pred_item, data_root,
            3,  # min_samples
            25,  # residual_threshold
            50,  # max_trials
            3  # max_iter
        ))

    # 使用多进程池处理
    metrics_per_img = {}
    with Pool(processes=8) as pool:
        results = list(tqdm(pool.imap(process_one_pair, tasks), total=len(tasks)))
        for i, metrics in results:
            metrics_per_img[i] = metrics

    # 计算总体指标
    score_list = [val['F1_score'] for val in metrics_per_img.values()]
    exp_list = [1 if score == 1 else 0 for score in score_list]
    metrics_res = {
        "mean_score": round(np.mean(score_list), 3),
        "exp_rate": round(np.mean(exp_list), 3),
        "details": metrics_per_img
    }

    # 保存结果
    metric_res_path = os.path.join(data_root, "metrics_res.json")
    with open(metric_res_path, "w") as f:
        json.dump(metrics_res, f, indent=2)

    return metrics_res, metric_res_path, os.path.join(data_root, "vis_match"), gt_list, pred_list
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', type=str, default="assets/example/input_example.json")
    parser.add_argument('--output', '-o', type=str, default="output")
    parser.add_argument('--pools', '-p', type=int, default=240)
    args = parser.parse_args()
    print(args)
    
    json_input, data_root, pool_num = args.input, args.output, args.pools
    temp_dir = os.path.join(data_root, "temp_dir")
    exp_name = os.path.basename(json_input).split('.')[0]
    with open(json_input, "r") as f:
        input_data = json.load(f)
    img_ids = []
    groundtruths = []
    predictions = []
    for idx, item in enumerate(input_data):
        if "img_id" in item:
            img_ids.append(item["img_id"])
        else:
            img_ids.append(f"sample_{idx}")
        groundtruths.append(item['gt'])
        predictions.append(item['pred'])

    a = time.time()
    user_id = exp_name
    
    total_color_list = gen_color_list(num=5800)
    
    data_root = os.path.join(data_root, user_id)
    output_dir_info = {}
    input_args = []
    for subset, latex_list in zip(['gt', 'pred'], [groundtruths, predictions]):
        sub_temp_dir = os.path.join(temp_dir, f"{exp_name}_{subset}")
        os.makedirs(sub_temp_dir, exist_ok=True)
        output_path = os.path.join(data_root, subset)
        output_dir_info[output_path] = []
    
        os.makedirs(os.path.join(output_path, 'bbox'), exist_ok=True)
        os.makedirs(os.path.join(output_path, 'vis'), exist_ok=True)
        
        for idx, latex in tqdm(enumerate(latex_list), desc=f"collect {subset} latex ..."):
            basename = img_ids[idx]
            input_arg = latex, basename, output_path, sub_temp_dir, total_color_list
            input_args.append(input_arg)
    
    if pool_num > 1:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "using processpool, pool num:", pool_num, ", job num:", len(input_args))
        myP = Pool(args.pools)
        for input_arg in input_args:
            myP.apply_async(latex2bbox_color, args=(input_arg,))
        myP.close()
        myP.join()
    else:
        for input_arg in input_args:
            latex2bbox_color(input_arg)
    b = time.time()
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "extract bbox done, time cost:", round(b-a, 3), "s")
    
    for subset in ['gt', 'pred']:
        shutil.rmtree(os.path.join(temp_dir, f"{exp_name}_{subset}"))
    
    c = time.time()
    metrics_res, metric_res_path, match_vis_dir = evaluation(args.output, exp_name)
    d = time.time()
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "calculate metrics done, time cost:", round(d-c, 3), "s")
    
    print(f"=> process done, mean f1 score: {metrics_res['mean_score']}.")
    print(f"=> more details of metrics are saved in `{metric_res_path}`")
    print(f"=> visulization images are saved under `{match_vis_dir}`")
    # print('c', os.listdir('output/temp_dir/test_cdm_gt'))