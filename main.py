import asyncio
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from utils.difflib_modified import SequenceMatcher
import os
import shutil
import logging
import traceback
from comparison_modules.image_comparison.image_comparsion import compare_image_list

from utils.tokenize import tokenize_files,get_mf_token,special_tokenize
from utils.postprocessor import process_result,write_diff,show_diff
from utils.precheck import find_files
import json

logging.basicConfig(
    level=logging.INFO,  # 记录info及以上级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 终端输出
        logging.FileHandler("diff.log")  # 文件输出
    ]
)

async def async_call(func, *args):
    """通用异步调用封装"""
    return await asyncio.to_thread(func, *args)

async def main(version1_dir,version2_dir,output_dir):
    logging.info(f"开始对比：{version1_dir}和{version2_dir}")
    try:
        md_file_verison1,images_dir_version1 = find_files(version1_dir)
        md_file_verison2,images_dir_version2 = find_files(version2_dir)
        version1_tokens, version1_spans, version1_token_is_sp,version2_tokens, version2_spans, version2_token_is_sp =tokenize_files(md_file_verison1,md_file_verison2,debug = True,output_dir=output_dir)
        get_mf_token(version1_tokens, version1_token_is_sp,output_path = os.path.join(output_dir,os.path.basename(version1_dir).split(".")[0]+"_mf.txt"))
        get_mf_token(version2_tokens, version2_token_is_sp,output_path = os.path.join(output_dir,os.path.basename(version2_dir).split(".")[0]+"_mf.txt"))
        tasks = [
            async_call(compare_image_list, images_dir_version1,images_dir_version2,os.path.join(output_dir,"图片对比结果")),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logging.info(f"数据对比识别结果:{results}")
        if False in results :
            raise RuntimeError(f"数据对比识别，{results}")
        image_path = results[0]
        with open(image_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            # print(json_data)
        new_image1_map = json_data["map1"]
        new_image2_map = json_data["map2"]
        version1_new_token = special_tokenize(version1_tokens, version1_token_is_sp,new_image1_map)
        version2_new_token = special_tokenize(version2_tokens, version2_token_is_sp,new_image2_map)
        with open(os.path.join(output_dir,os.path.basename(version1_dir)+"_new_token.txt"), 'w', encoding='utf-8') as f:
            for item in version1_new_token:
                f.write(f"{item}\n")
        with open(os.path.join(output_dir,os.path.basename(version2_dir)+"_new_token.txt"), 'w', encoding='utf-8') as f:
            for item in version2_new_token:
                f.write(f"{item}\n")
        matcher = SequenceMatcher(None, version1_tokens, version2_tokens)
        res = list(matcher.get_opcodes())
        diff_dir = os.path.join(output_dir,"diff中间结果")
        show_diff(version1_tokens,version2_tokens,output_dir=diff_dir,is_processed=True,opcodes=res,name="diff.html")
        write_diff(res,version1_tokens,version2_tokens,diff_dir)
        result_dir = os.path.join(output_dir,"后处理结果")
        result = process_result(res,version1_tokens, version1_spans, version1_token_is_sp,version2_tokens, version2_spans, version2_token_is_sp)
        write_diff(result,version1_tokens,version2_tokens,result_dir)
        show_diff(version1_tokens,version2_tokens,output_dir=result_dir,is_processed=True,opcodes=result,name="diff_processed.html")
        shutil.copy2(os.path.join(result_dir,"diff_processed.html"),os.path.join(output_dir,"diff_processed.html"))
    except Exception as e:
        tb_str = traceback.format_exc()  # 返回 Traceback 字符串
        logging.error(f"对比失败：{version1_dir}和{version2_dir}: {e}\n{tb_str}")
        return False
    logging.info(f"对比结束，结果保存在{output_dir}")




if __name__ == "__main__":
    version1_dir = "Print_of_CPS1000_W_中英对照_内部.pdf"
    version2_dir = "Print_of_CPS1000_V_中英对照_内部.pdf"
    output_dir = "./output"
    os.makedirs(output_dir,exist_ok=True)
    # root_dir = "./"
# subfolders = []
# # 列出所有待对比的文件夹
# for entry in os.listdir(root_dir):
#     print(entry)
#     entry_path = os.path.join(root_dir, entry)
#     if os.path.isdir(entry_path):
#         subfolders.append(entry_path)
#     print(subfolders)
# for subfolder in subfolders:
#     # 每个子文件夹下，有多个不同版本的文件夹
#     versions = os.listdir(subfolder)
#     if len(versions) != 2:
#         logging.warning(f"{subfolder}文件夹下有{len(versions)}个版本")
#         continue
#     sorted_versions = sorted(versions)


    asyncio.run(main(version1_dir,version2_dir,output_dir))