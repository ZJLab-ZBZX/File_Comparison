# logging_system.py
import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Dict, Tuple

def setup_logging_system(modules: list) -> Tuple[logging.Logger, Dict[str, logging.Logger]]:
    """
    初始化异步日志系统（主模块+子模块分离）
    
    :param modules: 子模块名称列表，如 ["module1", "module2"]
    :return: (主日志记录器, 子模块日志记录器字典)
    """
    # 收集所有处理器（主模块+子模块）
    all_handlers = []
    
    # 1. 主模块日志配置
    def _setup_main_logger():
        main_handler = logging.FileHandler("diff.log", encoding='utf-8')
        main_formatter = logging.Formatter(
            fmt='[MAIN] %(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        main_handler.setFormatter(main_formatter)
        all_handlers.append(main_handler)
    
    # 2. 子模块日志配置
    module_loggers = {}
    def _setup_module_logger(module_name: str) -> logging.Logger:
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # 阻止向上传播[6](@ref)
        
        file_handler = logging.FileHandler(f"{module_name}.log", encoding='utf-8')
        module_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(module_formatter)
        all_handlers.append(file_handler)
        
        return logger

    # 初始化处理器
    _setup_main_logger()
    for module in modules:
        module_loggers[module] = _setup_module_logger(module)

    # 3. 创建异步队列架构
    log_queue = Queue(maxsize=1000)
    listener = QueueListener(log_queue, *all_handlers)  # 一次性传入所有处理器
    listener.start()

    # 4. 配置根记录器（主模块入口）
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(QueueHandler(log_queue))  # 主线程日志推入队列[1](@ref)
    
    return root_logger, module_loggers, listener