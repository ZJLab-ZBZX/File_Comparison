import asyncio
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from utils.difflib_modified import SequenceMatcher
import os
import shutil
import logging
import traceback
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from datetime import datetime
from utils.tokenize import tokenize_doc,get_mf_token,special_tokenize_replace,convert_mf_token
from utils.postprocessor import process_result,write_diff,show_diff,locate_diff
from utils.precheck import find_files
from utils.deal_text import read_txt_to_2d_list
import json
from comparison_modules.latex_comparison.batch_compare import batch_compare
import argparse
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
import re
import json
import numpy as np
from utils.draw_result import draw_result

with open('./configs/categories.json', 'r') as f:
    config = json.load(f)
    ocr_categories = config["ocr_categories"]
    filter_categories = config["filter_categories"]
    


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

async def compare(src_dir,dst_dir,output_dir):
    main_logger.info(f"开始对比：{src_dir}和{dst_dir}")
    try:
        # 预检查文件是否存在
        src_debug_dir,src_images_dir = find_files(src_dir)
        dst_debug_dir,dst_images_dir = find_files(dst_dir)
        # token化
        token_output_dir = os.path.join(output_dir,"token处理结果")
        os.makedirs(token_output_dir,exist_ok=True)
        src_doc_segs, src_doc_rects, src_doc_seg_tokens, src_doc_seg_token_spans, src_doc_seg_page_ids, src_doc_tokens,src_doc_token_is_sp, src_doc_token_rect_ids = tokenize_doc(src_debug_dir,ocr_categories,filter_categories,debug = True,output_dir=token_output_dir)
        dst_doc_segs, dst_doc_rects, dst_doc_seg_tokens, dst_doc_seg_token_spans, dst_doc_seg_page_ids, dst_doc_tokens,dst_doc_token_is_sp, dst_doc_token_rect_ids = tokenize_doc(dst_debug_dir,ocr_categories,filter_categories,debug = True,output_dir=token_output_dir)

        main_logger.info(f"完成token化：{src_dir}和{dst_dir}")
        # 获取mf的token
        mf_path1 = os.path.join(src_dir,os.path.basename(src_dir).split(".")[0]+"_mf.txt")
        mf_path2 = os.path.join(dst_dir,os.path.basename(dst_dir).split(".")[0]+"_mf.txt")
        mf_index1 = get_mf_token(src_doc_tokens, src_doc_token_is_sp,output_path = mf_path1)
        mf_index2 = get_mf_token(dst_doc_tokens, dst_doc_token_is_sp,output_path = mf_path2)
        # 依次调用图片处理模块、公式处理模块和表格处理模块
        tasks = [
            async_call(compare_image_list, src_images_dir,dst_images_dir,os.path.join(output_dir,"图片对比结果"),os.cpu_count()+1),
            async_call(batch_compare,mf_path1,mf_path2)
        ]
        # 获取处理结果
        main_logger.info(f"完成图片、公式和表格处理：{src_dir}和{dst_dir}")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        if False in results :
            raise RuntimeError(f"数据对比失败，图片处理模块、公式处理模块和表格处理模块处理结果依次为：{results}")
        main_logger.info(f"开始特殊token处理，开始diff：{src_dir}和{dst_dir}")
        image_result_path = results[0]
        with open(image_result_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        new_image1_map = json_data[os.path.basename(src_dir)]
        new_image2_map = json_data[os.path.basename(dst_dir)]
        mf_result = read_txt_to_2d_list(results[1])
        new_mf1_map,new_mf2_map = convert_mf_token(mf_result,
                                                   mf_index1=mf_index1,mf_index2=mf_index2,
                                                   prefix1=os.path.basename(src_dir).split(".")[0],
                                                   prefix2=os.path.basename(dst_dir).split(".")[0],
                                                   outputdir=token_output_dir)
        # 特殊token处理
        src_new_token = special_tokenize_replace(src_doc_tokens, src_doc_token_is_sp,new_image1_map,new_mf1_map,token_output=os.path.join(token_output_dir,os.path.basename(src_dir)+"_new_token.txt"))
        dst_new_token = special_tokenize_replace(dst_doc_tokens, dst_doc_token_is_sp,new_image2_map,new_mf2_map,token_output=os.path.join(token_output_dir,os.path.basename(dst_dir)+"_new_token.txt"))
        main_logger.info(f"完成特殊token处理，开始diff：{src_dir}和{dst_dir}")
        # diff
        matcher = SequenceMatcher(None, src_new_token, dst_new_token)
        opcodes = list(matcher.get_opcodes())
        diff_dir = os.path.join(output_dir,"diff中间结果")
        show_diff(src_new_token,dst_new_token,output_dir=diff_dir,is_processed=True,opcodes=opcodes,name="diff.html")
        write_diff(opcodes,src_new_token,dst_new_token,diff_dir)
        # diff后处理
        result_dir = os.path.join(output_dir,"后处理结果")
        processed_opcodes = process_result(opcodes,src_new_token, dst_new_token)
        write_diff(processed_opcodes,src_new_token,dst_new_token,result_dir)
        show_diff(src_new_token,dst_new_token,output_dir=result_dir,is_processed=True,opcodes=processed_opcodes,name="diff_processed.html")
        shutil.copy2(os.path.join(result_dir,"diff_processed.html"),os.path.join(output_dir,"diff_processed.html"))
        # diff结果转化为坐标+说明
        main_logger.info(f"开始转化坐标：{src_dir}和{dst_dir}")
        diff_cats, src_diff_start_tids, src_diff_end_tids, dst_diff_start_tids, dst_diff_end_tids = list(map(lambda x: np.array(list(x)), zip(*processed_opcodes)))
        src_diff_end_tids = src_diff_end_tids - 1
        dst_diff_end_tids = dst_diff_end_tids - 1
        diff_cats = diff_cats.astype(object)
        src_diff_rects, src_diff_seg_page_ids, src_diff_texts = locate_diff(
            src_doc_segs, src_doc_seg_tokens, src_doc_seg_token_spans, src_doc_rects, src_doc_seg_page_ids, 
            src_doc_tokens, src_doc_token_is_sp,src_doc_token_rect_ids, src_diff_start_tids, src_diff_end_tids)
        dst_diff_rects, dst_diff_seg_page_ids, dst_diff_texts = locate_diff(
            dst_doc_segs, dst_doc_seg_tokens, dst_doc_seg_token_spans, dst_doc_rects, dst_doc_seg_page_ids, 
            dst_doc_tokens, dst_doc_token_is_sp, dst_doc_token_rect_ids, dst_diff_start_tids, dst_diff_end_tids) 
        result = []
        for i_diff, cat in enumerate(diff_cats):
            if cat == 'equal':
                continue
            elif cat == 'replace':
                msg = f'从“{src_diff_texts[i_diff]}”变更为“{dst_diff_texts[i_diff]}”'
            elif cat == 'delete':
                msg = f'删除“{src_diff_texts[i_diff]}”'
            else:
                msg = f'新增“{dst_diff_texts[i_diff]}”'
            result.append({
                'edit_op': cat,
                'src_rects': src_diff_rects[i_diff].tolist(),
                'src_page_ids': src_diff_seg_page_ids[i_diff].tolist(),
                'dst_rects': dst_diff_rects[i_diff].tolist(),
                'dst_page_ids': dst_diff_seg_page_ids[i_diff].tolist(),
                'msg': msg
                })
        with open(os.path.join(output_dir,'result.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        main_logger.info(f"开始绘制结果文件：{src_dir}和{dst_dir}")
        draw_output = os.path.join(output_dir,"最终结果_图片")
        os.makedirs(draw_output,exist_ok=True)
        draw_result(diff_cats,src_dir,src_diff_seg_page_ids,src_diff_rects,src_diff_texts,draw_output)
        draw_result(diff_cats,dst_dir,dst_diff_seg_page_ids,dst_diff_rects,dst_diff_texts,draw_output)
    except Exception as e:
        tb_str = traceback.format_exc()  # 返回 Traceback 字符串
        main_logger.error(f"对比失败：{src_dir}和{dst_dir}: {e}\n{tb_str}")
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
    main_logger.info(f"对比文件夹目录：{root_dir}，结果输出目录：{output_dir}")
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
            try:
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
                asyncio.run(compare(pair[0],pair[1],output_sub_dir))
            except Exception as e:
                tb_str = traceback.format_exc()  # 返回 Traceback 字符串
                main_logger.error(f"对比失败：{pair}: {e}\n{tb_str}")
                continue
    listener.stop()


if __name__ == "__main__":
    main()
    