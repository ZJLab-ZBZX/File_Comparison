import asyncio
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from utils.difflib_modified import SequenceMatcher
import os
import shutil
import logging
import traceback
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from datetime import datetime
from utils.tokenize import tokenize_files,get_mf_token,special_tokenize,convert_mf_token
from utils.postprocessor import process_result,write_diff,show_diff
from utils.precheck import find_files
from utils.deal_text import read_txt_to_2d_list
import json
from comparison_modules.latex_comparison.batch_compare import batch_compare
import argparse
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
import re

# 创建内存队列和异步监听器
log_queue = Queue(maxsize=1000)  # 限制队列大小防溢出
file_handler = logging.FileHandler("diff.log", encoding='utf-8')
stream_handler = logging.StreamHandler()

# 创建格式化器（新增部分）
formatter = logging.Formatter(
    fmt='[main]%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 将格式化器应用到处理器（新增部分）
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
# 创建队列监听器
listener = QueueListener(log_queue, file_handler,stream_handler)
listener.start()

# 配置Logger
main_logger = logging.getLogger()
main_logger.setLevel(logging.INFO)
main_logger.addHandler(QueueHandler(log_queue))  # 主线程仅推队列


async def async_call(func, *args):
    """通用异步调用封装"""
    return await asyncio.to_thread(func, *args)

async def compare(subfolder,version1_dir,version2_dir,output_dir):
    main_logger.info(f"开始对比：{version1_dir}和{version2_dir}")
    try:
        # 预检查文件是否存在
        md_file_verison1,images_dir_version1 = find_files(version1_dir)
        md_file_verison2,images_dir_version2 = find_files(version2_dir)
        # token化
        token_output_dir = os.path.join(output_dir,"token处理结果")
        os.makedirs(output_dir,exist_ok=True)
        version1_tokens, version1_spans, version1_token_is_sp,version2_tokens, version2_spans, version2_token_is_sp =tokenize_files(md_file_verison1,md_file_verison2,debug = True,output_dir=token_output_dir)
        main_logger.info(f"完成token化：{version1_dir}和{version2_dir}")
        # 获取mf的token
        mf_path1 = os.path.join(version1_dir,os.path.basename(version1_dir).split(".")[0]+"_mf.txt")
        mf_path2 = os.path.join(version2_dir,os.path.basename(version2_dir).split(".")[0]+"_mf.txt")
        mf_index1 = get_mf_token(version1_tokens, version1_token_is_sp,output_path = mf_path1)
        mf_index2 = get_mf_token(version2_tokens, version2_token_is_sp,output_path = mf_path2)
        # 依次调用图片处理模块、公式处理模块和表格处理模块
        tasks = [
            async_call(compare_image_list, images_dir_version1,images_dir_version2,os.path.join(output_dir,"图片对比结果"),os.cpu_count()+1),
            async_call(batch_compare,mf_path1,mf_path2)
        ]
        # 获取处理结果
        main_logger.info(f"完成图片、公式和表格处理：{version1_dir}和{version2_dir}")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        if False in results :
            raise RuntimeError(f"数据对比失败，图片处理模块、公式处理模块和表格处理模块处理结果依次为：{results}")
        image_result_path = results[0]
        with open(image_result_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        new_image1_map = json_data[os.path.basename(version1_dir)]
        new_image2_map = json_data[os.path.basename(version2_dir)]
        mf_result = read_txt_to_2d_list(results[1])
        new_mf1_map,new_mf2_map = convert_mf_token(mf_result,
                                                   mf_index1=mf_index1,mf_index2=mf_index2,
                                                   prefix1=os.path.basename(version1_dir).split(".")[0],
                                                   prefix2=os.path.basename(version2_dir).split(".")[0],
                                                   outputdir=token_output_dir)
        # 特殊token处理
        version1_new_token = special_tokenize(version1_tokens, version1_token_is_sp,new_image1_map,new_mf1_map,token_output=os.path.join(token_output_dir,os.path.basename(version1_dir)+"_new_token.txt"))
        version2_new_token = special_tokenize(version2_tokens, version2_token_is_sp,new_image2_map,new_mf2_map,token_output=os.path.join(token_output_dir,os.path.basename(version2_dir)+"_new_token.txt"))
        main_logger.info(f"完成特殊token处理，开始diff：{version1_dir}和{version2_dir}")
        # diff
        matcher = SequenceMatcher(None, version1_new_token, version2_new_token)
        res = list(matcher.get_opcodes())
        diff_dir = os.path.join(output_dir,"diff中间结果")
        show_diff(version1_new_token,version2_new_token,output_dir=diff_dir,is_processed=True,opcodes=res,name="diff.html")
        write_diff(res,version1_new_token,version2_new_token,diff_dir)
        # diff后处理
        result_dir = os.path.join(output_dir,"后处理结果")
        result = process_result(res,version1_new_token, version1_spans, version1_token_is_sp,version2_new_token, version2_spans, version2_token_is_sp)
        write_diff(result,version1_new_token,version2_new_token,result_dir)
        show_diff(version1_new_token,version2_new_token,output_dir=result_dir,is_processed=True,opcodes=result,name="diff_processed.html")
        shutil.copy2(os.path.join(result_dir,"diff_processed.html"),os.path.join(output_dir,"diff_processed.html"))
    except Exception as e:
        tb_str = traceback.format_exc()  # 返回 Traceback 字符串
        main_logger.error(f"对比失败：{version1_dir}和{version2_dir}: {e}\n{tb_str}")
        return False
    main_logger.info(f"对比结束，结果保存在{output_dir}")


def main():
    parser = argparse.ArgumentParser(description='处理文件夹对比任务')
    parser.add_argument('root_dir', 
                        type=str, 
                        help='根目录路径，包含需要对比的子文件夹')
    parser.add_argument('output_dir', 
                        type=str, 
                        help='结果输出路径',
                        default="./")
    
    # 解析命令行参数
    args = parser.parse_args()
    # 使用命令行输入的路径
    root_dir = args.root_dir
    output_dir = args.output_dir
    if not os.path.exists(root_dir):
        main_logger.error(f"指定的路径不存在: {root_dir}")
        exit(1)
    subfolders = []
    # 列出所有待对比的文件夹
    for entry in os.listdir(root_dir):
        entry_path = os.path.join(root_dir, entry)
        if os.path.isdir(entry_path):
            subfolders.append(entry_path)
    sorted_subfolders = sorted(subfolders)
    for subfolder in sorted_subfolders:
        # 每个子文件夹下，有多个不同版本的文件夹
        files = os.listdir(subfolder)
        versions = []
        for file in files:
            file_path = os.path.join(subfolder, file)
            if os.path.isdir(file_path) and ".pdf" in file:
                versions.append(file_path)
        if len(versions) < 2:
            main_logger.warning(f"{subfolder}文件夹下有{len(versions)}个版本")
            continue
        sorted_versions = sorted(versions)
        compare_dirs = [list(pair) for pair in zip(sorted_versions, sorted_versions[1:])]
        num = 1
        for pair in compare_dirs:
            now = datetime.now()
            time_str = now.strftime("%Y%m%d_%H%M")
            pattern = os.path.basename(subfolder)+r"[^A-Za-z]*([A-Za-z]+)[^A-Za-z]*\.pdf"
            prestr = ""
            match_num = 0
            for filename in pair:
                match = re.search(pattern, filename)
                if match:
                    prestr = prestr + "_" + match.group(1)
                    match_num = match_num + 1
            if match_num !=2:
                logging.warning(f"{subfolder}{pair}目录下获取版本号失败")
                prestr = os.path.basename(subfolder) + str(num)
                num = num + 1
            output_sub_dir = os.path.join(output_dir,os.path.basename(subfolder)+prestr+time_str)
            os.makedirs(output_sub_dir,exist_ok=True)
            asyncio.run(compare(subfolder,sorted_versions[0],sorted_versions[1],output_sub_dir))
    listener.stop()


if __name__ == "__main__":
    main()
    