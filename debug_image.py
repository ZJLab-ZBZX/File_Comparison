import asyncio
from comparison_modules.image_comparison.image_comparsion import compare_image_list
from utils.difflib_modified import SequenceMatcher
import os
import shutil
import logging
import traceback
from comparison_modules.image_comparison.image_comparsion import compare_image_list,tets
from logging.handlers import QueueHandler, QueueListener
from queue import Queue


# 创建内存队列和异步监听器
log_queue = Queue(maxsize=1000)  # 限制队列大小防溢出
file_handler = logging.FileHandler("diff22.log", encoding='utf-8')

# 创建格式化器（新增部分）
formatter = logging.Formatter(
    fmt='[main]%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 将格式化器应用到处理器（新增部分）
file_handler.setFormatter(formatter)

# 创建队列监听器
listener = QueueListener(log_queue, file_handler)
listener.start()

# 配置Logger
main_logger = logging.getLogger()
main_logger.setLevel(logging.INFO)
main_logger.addHandler(QueueHandler(log_queue))  # 主线程仅推队列



if __name__ == "__main__":
    num_pools = os.cpu_count() + 1  # 根据CPU核心数设置
    main_logger.info("test")
    # compare_image_list("D:/文件对比/西子数据/CPS1000/Print_of_CPS1000_V_中英对照_内部.pdf/figures", "D:/文件对比/西子数据/CPS1000/Print_of_CPS1000_W_中英对照_内部.pdf/figures", "D:/文件对比/图片对比结果_new22", num_pools)