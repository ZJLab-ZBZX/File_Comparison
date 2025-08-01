# -*- coding: utf-8 -*-
"""
@Time: 2025/7/31 10:23
@Auth: Liu Ji
"""

import logging
from logging.handlers import RotatingFileHandler
import sys


def setup_logger(module_name=None, log_file='latex_comparison.log'):
    """
    创建并配置具有模块信息的日志记录器

    参数:
        module_name (str): 调用模块的名称（通常使用__name__）
        log_file (str): 日志文件路径（默认: application.log）
    """
    # 获取模块名（如果未提供则使用'root'）
    name = module_name if module_name else 'root'

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 设置最低日志级别

    # 如果日志器已有处理器则不再添加（避免重复记录）
    if logger.hasHandlers():
        return logger

    # 设置日志格式 - 包含模块信息
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)04d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建控制台处理器（INFO级别）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 创建文件处理器（DEBUG级别，日志滚动）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
