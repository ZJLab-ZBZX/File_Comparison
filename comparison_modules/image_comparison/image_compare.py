import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity as ssim
import logging
import os
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import torch.nn.functional as F
from pathlib import Path
from datetime import datetime
import json
import traceback

logging.basicConfig(
    level=logging.INFO,  # 记录info及以上级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 终端输出
        logging.FileHandler("image_compare.log")  # 文件输出
    ]
)


def init_child_process(lock):
    """初始化子进程资源（全局锁）"""
    global global_file_lock
    global_file_lock = lock

def compare_images_SSIM(image_path1, image_path2,result_output_path,threshold=0.95):
    logging.info(f"SSIM开始对比图片：{image_path1}和{image_path2}")
    # 1. 读取图片并统一尺寸
    with open(image_path1, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
        img1 = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
    with open(image_path2, "rb") as f:
        img_data = np.frombuffer(f.read(), dtype=np.uint8)
        img2 = cv2.imdecode(img_data, cv2.IMREAD_COLOR)    
    if img1 is None or img2 is None:
        logging.error(f"图片读取失败，请检查路径:{image_path1}和{image_path2}")
        raise ValueError("图片读取失败，请检查路径")
    
    # 自动调整至相同尺寸（取最小尺寸）
    h, w = min(img1.shape[0], img2.shape[0]), min(img1.shape[1], img2.shape[1])
    img1_resized = cv2.resize(img1, (w//2, h//2))
    img2_resized = cv2.resize(img2, (w//2, h//2))
    
    # 2. 转为灰度图（SSIM计算要求）
    gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
    
    # 3. 计算SSIM值和差异图
    score = ssim(gray1, gray2, full=False, win_size=11, data_range=255)
    is_similar = score >= threshold
    
    logging.info(f"SSIM对比结束：{image_path1}和{image_path2}，分数：{score},阈值:{threshold}")
    return score, is_similar



def resnet_cosine_similarity(img_path1, img_path2,threshold=0.95):
    logging.info(f"余弦相似度开始对比图片：{img_path1}和{img_path2}")
    # 1. 加载预训练ResNet50模型（移除全连接层）
    model = models.resnet50(pretrained=True)
    model = torch.nn.Sequential(*list(model.children())[:-1])  # 移除最后一层分类层
    model.eval()  # 设为评估模式

    # 2. 定义图像预处理流程
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 3. 加载并预处理图像
    def load_image(image_path):
        img = Image.open(image_path).convert('RGB')
        return preprocess(img).unsqueeze(0)  # 增加batch维度

    img1 = load_image(img_path1)
    img2 = load_image(img_path2)

    # 4. 提取特征向量
    with torch.no_grad():
        features1 = model(img1).flatten()  # 展平为1D向量 [2048]
        features2 = model(img2).flatten()

    # 5. 计算余弦相似度 [-1, 1]
    similarity = F.cosine_similarity(features1.unsqueeze(0), features2.unsqueeze(0), dim=1)
    score = similarity.item()
    is_similar = score >= threshold
    logging.info(f"余弦相似度对比结束：{img_path1}和{img_path2}，分数：{score},阈值:{threshold}")
    return score,is_similar

def compare_together(image1,image2,outputdir):
    os.makedirs(outputdir,exist_ok=True)
    output_path = os.path.join(outputdir,os.path.splitext(os.path.basename(image1))[0]
                               +"_and_"+os.path.splitext(os.path.basename(image2))[0]+".jpg")
    score_SSIM,is_similar_SSIM = compare_images_SSIM(image1, image2,output_path)
    score_ResNet,is_similar_ResNet = resnet_cosine_similarity(image1, image2)
    with open(os.path.join(outputdir,"compare_score.txt"), 'a', encoding='utf-8') as file:
        file.write(f"{datetime.now()}  {os.path.splitext(os.path.basename(image1))[0]}和 \
                   {os.path.splitext(os.path.basename(image2))[0]}的SSIM分数是{score_SSIM}，\
                   是否相似：{is_similar_SSIM}，余弦相似度分数是{score_ResNet}，是否相似：{is_similar_ResNet}\n")
    if is_similar_SSIM and is_similar_ResNet:
        return (score_SSIM+score_ResNet)/2
    else:
        return 0

def convert_token(image_list1,image_list2,same_pairs):
    number = 276352563
    new_image1_map = {}
    new_image2_map = {}
    for pairs in same_pairs:
        new_image1_map[image_list1[pairs[0]]] = "<image" + str(number) + ">"
        new_image2_map[image_list2[pairs[0]]] = "<image" + str(number) + ">"
        number = number + 1
    return new_image1_map,new_image2_map

def compare_image_list(image_dir1,image_dir2,outputdir):
    try:
        logging.info(f"开始对比图片文件夹:{image_dir1}{image_dir2}")
        image_exts = ('.jpg', '.jpeg', '.png')
        image_list1 = [os.path.join(image_dir1, f)
            for f in os.listdir(image_dir1)
            if f.lower().endswith(image_exts) 
        ]
        image_list2 = [os.path.join(image_dir2, f)
            for f in os.listdir(image_dir2)
            if f.lower().endswith(image_exts) 
        ]
        # 1. 生成对比结果矩阵
        diff_matrix = [
            [compare_together(images1,images2,outputdir) for images2 in image_list2]
            for images1 in image_list1
        ]
        
        # 2. 匹配图片
        same_pairs = []
        for i, image1 in enumerate(image_list1):
            max_score = 0
            for j, image2 in enumerate(image_list2):
                current_score = diff_matrix[i][j]
                if current_score > max_score:
                    max_score = current_score
                    max_image2 = image2
                    logging.info(f"图片{image1}和图片{max_image2}匹配")
                elif current_score == max_score:
                    logging.warning(f"图片{image1}和两张图片相似度一样：{image2}{max_image2}")
            if max_score > 0:
                same_pairs.append((i, j))
        new_image1_map,new_image2_map = convert_token(image_list1,image_list2,same_pairs)
        with open(os.path.join(outputdir,"compare_same_images.txt"), 'w', encoding='utf-8') as file:
            json.dump(new_image1_map, file, indent=4, ensure_ascii=False)
            json.dump(new_image2_map, file, indent=4, ensure_ascii=False)
        logging.info(f"结束对比图片文件夹:{image_dir1}{image_dir2}")
        return new_image1_map,new_image2_map
    except Exception as e:
        tb_str = traceback.format_exc()  # 返回 Traceback 字符串
        logging.error(f"对比失败：{image_dir1}和{image_dir2}: {e}\n{tb_str}")
        raise RuntimeError(f"对比失败：{image_dir1}和{image_dir2}: {e}\n{tb_str}")

    