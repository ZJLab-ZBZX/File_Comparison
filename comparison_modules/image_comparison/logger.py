import logging

def setup_logger():
    # 1. 创建子Logger并禁用传播
    app_logger = logging.getLogger(__name__)
    app_logger.propagate = False
    app_logger.setLevel(logging.DEBUG)  

    formatter = logging.Formatter(
        fmt='[image]%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = logging.FileHandler("image_compare.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    # 4. 添加Handler到Logger
    app_logger.addHandler(file_handler)
    app_logger.addHandler(stream_handler)
    return app_logger
