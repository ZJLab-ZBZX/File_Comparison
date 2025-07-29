import asyncio
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from utils.difflib_modified import SequenceMatcher
import os
import shutil
import logging
import traceback
from comparison_modules.image_comparison.image_comparsion import compare_image_list

logging.basicConfig(
    level=logging.INFO,  # 记录info及以上级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 终端输出
        logging.FileHandler("diff.log")  # 文件输出
    ]
)


if __name__ == "__main__":
    num_pools = os.cpu_count() + 1  # 根据CPU核心数设置
    compare_image_list("D:/文件对比/西子数据/CPS1000/Print_of_CPS1000_V_中英对照_内部.pdf/figures", "D:/文件对比/西子数据/CPS1000/Print_of_CPS1000_W_中英对照_内部.pdf/figures", "D:/文件对比/图片对比结果_new", num_pools)