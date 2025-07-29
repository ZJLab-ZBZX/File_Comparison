# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 09:40:00 2025

@author: ZJ
"""
import os, glob, json, argparse
from .modules.latex2bbox_color import latex2bbox_color_simple
from .evaluation import batch_evaluation_multiple_pools
from .mf_parse_tree import handle_latex
from multiprocessing import Pool
from .data_processor import generate_passed_pairs
import shutil


def delete_specific_files(root_dir, file_names):
    """
    在指定目录及其子目录中删除特定的文件

    参数:
        root_dir (str): 要搜索的根目录
        file_names (list): 要删除的文件名列表

    返回:
        list: 已删除的文件路径列表
    """
    deleted_files = []

    # 遍历目录树
    for foldername, subfolders, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename in file_names:
                file_path = os.path.join(foldername, filename)
                try:
                    # 删除文件
                    os.unlink(file_path)
                    deleted_files.append(file_path)
                    print(f"已删除: {file_path}")
                except Exception as e:
                    print(f"删除失败 {file_path}: {str(e)}")
                    continue

    return deleted_files


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

def batch_compare(input_dir):
    try:
        # ketax 进行normalize
        delete_specific_files(input_dir,["passed.jsonl","failed.jsonl","passed_pairs_chain.txt"])
        mf_file_names = [name for name in glob.glob(os.path.join(input_dir, '**/*'), recursive=True)
                         if name.lower().endswith('.txt') and '_mf' in os.path.basename(name)]
        print(mf_file_names)
        print("size", len(mf_file_names))
        pool = Pool(36)
        total_latex_number = 0
        for i, mf_file_name in enumerate(mf_file_names):
            with open(mf_file_name, 'r', encoding='utf-8') as f:
                latex_list = json.load(f)
                print(f'第{i}个文件{mf_file_name}包含公式{len(latex_list)}')
                total_latex_number = total_latex_number + len(latex_list)
                for j, latex_code in enumerate(latex_list):
                    pool.apply_async(handle_latex, args=(mf_file_name, latex_code, j))
        pool.close()
        pool.join()

        print(f"{total_latex_number}个公式的katax normalize 完成")

        # 转pdf并且提取token 和对应的bbox
        output_path = os.path.join(input_dir, "output_mf")

        temp_dir = os.path.join(output_path, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        total_color_list = gen_color_list(num=5800)

        os.makedirs(os.path.join(output_path, 'vis'), exist_ok=True)
        os.makedirs(os.path.join(output_path, 'bbox'), exist_ok=True)

        myP = Pool(30)
        passed_file_names = [name for name in glob.glob(os.path.join(input_dir, '**/*'), recursive=True)
                             if name.lower().endswith('.jsonl') and 'passed' in name]
        for i, passed_file in enumerate(passed_file_names):
            with open(passed_file, 'r', encoding='utf-8') as f1:
                lines = f1.readlines()
                for i, line in enumerate(lines):
                    label = json.loads(line)
                    filename, latex = next(iter(label.items()))
                    input_arg = (latex, filename, output_path, temp_dir, total_color_list)
                    myP.apply_async(latex2bbox_color_simple, args=(input_arg,))
        myP.close()
        myP.join()

        # 两个文件生成笛卡尔积对比对，然后进行对比
        metrics_res, metric_res_path, match_vis_dir, gt_list, pred_list = batch_evaluation_multiple_pools(output_path,
                                                                                                          passed_file_names[
                                                                                                              0],
                                                                                                          passed_file_names[
                                                                                                              1])
        generate_passed_pairs(metric_res_path, gt_list, pred_list, os.path.join(output_path, "passed_pairs_chain.txt"))
        return os.path.join(output_path, "passed_pairs_chain.txt")
    except Exception as e:
        print("batch_compare error")
        return False


if __name__ == '__main__':
    out = batch_compare("D:\\cdm\\xiziData")
    print(out)


