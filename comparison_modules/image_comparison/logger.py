import logging

def setup_logger(log_name ="image_compare",log_path = "image_compare.log"):
    # 1. 创建子Logger并禁用传播
    app_logger = logging.getLogger(log_name)
    app_logger.propagate = False
    app_logger.setLevel(logging.DEBUG)  

    formatter = logging.Formatter(
        fmt='[image]%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    # 4. 添加Handler到Logger
    # 清除旧处理器避免重复
    if app_logger.hasHandlers():
        for handler in app_logger.handlers[:]:
            app_logger.removeHandler(handler)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(stream_handler)
    return app_logger
