# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 09:40:00 2025

@author: ZJ
"""
import os, glob, json, argparse
from .modules.latex2bbox_color import latex2bbox_color_simple
from .evaluation import batch_evaluation,batch_evaluation_multiple_pools
from .mf_parse_tree import handle_latex
from multiprocessing import Pool
from .data_processor import generate_passed_pairs
import traceback
from .logger import setup_logger

import logging


logger = setup_logger(__name__)
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

def is_normalized(file_path):
    target_path = os.path.join(os.path.dirname(file_path),"passed.jsonl")
    if os.path.exists(target_path):
        logger.info(f"文件{target_path}已经存在,不需要normalize")
        return True
    else:
        logger.info(f"文件{file_path}未规范化,开始normalize")
        return False


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

def normalize_by_katex(file_path):
    logger.info(f"文件{os.path.basename(file_path)}开始normalize")
    try:
        pool = Pool(36)
        with open(file_path, 'r', encoding='utf-8') as f:
            latex_list = json.load(f)
            logger.info(f'文件{os.path.basename(file_path)}包含公式{len(latex_list)}')
            for j, latex_code in enumerate(latex_list):
                pool.apply_async(handle_latex, args=(file_path, latex_code, j))
        pool.close()
        pool.join()
        return True
    except Exception as e:
        logger.error(f"normalize_by_katex处理失败: {str(e)}", exc_info=True)
        logger.exception("完整异常信息:")
        return False

def latex2pdf(file_path,temp_dir):
    if not os.path.exists(file_path):
        logger.error(f"文件{file_path}不存在")
        return False
    logger.info(f"开始对文件{file_path}进行latex2pdf的处理")
    output_path = os.path.dirname(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    total_color_list = gen_color_list(num=5800)
    os.makedirs(os.path.join(output_path, 'vis'), exist_ok=True)
    os.makedirs(os.path.join(output_path, 'bbox'), exist_ok=True)
    try:
        # myP = Pool(30)
        with open(file_path, 'r', encoding='utf-8') as f1:
            lines = f1.readlines()
            for i, line in enumerate(lines):
                label = json.loads(line)
                filename, latex = next(iter(label.items()))
                input_arg = (latex, filename, output_path, temp_dir, total_color_list)
                latex2bbox_color_simple(latex, filename, output_path, temp_dir, total_color_list)
                # myP.apply_async(latex2bbox_color_simple, args=(input_arg,))
        # myP.close()
        # myP.join()
        logger.info(f"文件{file_path}已经处理完毕，共转换{len(lines)}个Latex")
    except Exception as e:
        logger.error(f"latex2pdf处理失败: {str(e)}", exc_info=True)
        logger.exception("完整异常信息:")
        return False
def batch_compare(file_path_1,file_path_2):
    try:
        if not os.path.exists(file_path_1):
            logging.error(f"txt 文件不存在: {file_path_1}")
            return False
        if not os.path.exists(file_path_2):
            logging.error(f"txt 文件不存在: {file_path_2}")
            return False
        directory_path = os.path.dirname(os.path.dirname(file_path_1))
        if directory_path != os.path.dirname(os.path.dirname(file_path_2)):
            logging.error(f"{file_path_1}和{file_path_2}的祖父节点不一致，无法比较")
            return False
        # 1.0 ketax 进行normalize
        if not is_normalized(file_path_1):
            normalize_by_katex(file_path_1)
        if not is_normalized(file_path_2):
            normalize_by_katex(file_path_2)

        # 2.0 转pdf并且提取token 和对应的bbox
        output_path = os.path.join(directory_path, "output_mf")
        folder_name_1 = os.path.basename( os.path.dirname(file_path_1))
        temp_dir1 = os.path.join(output_path, folder_name_1, "temp")
        passed_file_path_1 = os.path.join(os.path.dirname(file_path_1), "passed.jsonl")
        if os.path.exists(temp_dir1):
            file_count_1 = len(os.listdir(temp_dir1))
            print(len(os.listdir(temp_dir1)))
            logger.info(f"文件夹{temp_dir1}下已经包含{file_count_1}个文件")
            logger.info(f"跳过latex2pdf阶段")
        else:
            latex2pdf(passed_file_path_1,temp_dir1)

        folder_name_2 = os.path.basename(os.path.dirname(file_path_2))
        temp_dir2 = os.path.join(output_path, folder_name_2,"temp")
        passed_file_path_2 = os.path.join(os.path.dirname(file_path_2), "passed.jsonl")
        if os.path.exists(temp_dir2):
            file_count_2 = len(os.listdir(temp_dir2))
            logger.info(f"文件夹{temp_dir2}下已经包含{file_count_2}个文件")
            logger.info(f"跳过latex2pdf阶段")
        else:
            latex2pdf(passed_file_path_2, temp_dir2)

        # 两个文件生成笛卡尔积对比对，然后进行对比
        metric_res_path,test_cases_file_path = batch_evaluation_multiple_pools(os.path.join(output_path, folder_name_1),os.path.join(output_path, folder_name_2),passed_file_path_1,passed_file_path_2)
        final_res = generate_passed_pairs(metric_res_path,test_cases_file_path, os.path.join(os.path.dirname(metric_res_path), "passed_pairs_chain.txt"))
        if final_res:
            logger.info(f"成功返回结果到文件{final_res}")
        else:
            logger.debug(f"返回结果异常{str(final_res)}")
        return final_res
    except Exception as e:
        print("batch_compare error", traceback.format_exc())
        return False


if __name__ == '__main__':
    batch_compare("D:\\cdm\\xiziData\\Print_of_CPS1000_V_中英对照_内部.pdf\\Print_of_CPS1000_V_中英对照_内部_mf.txt","D:\\cdm\\xiziData\\Print_of_CPS1000_W_中英对照_内部.pdf\\Print_of_CPS1000_W_中英对照_内部_mf.txt")
    # print(out)


