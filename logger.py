# -*-coding=utf-8-*-


import logging


class Logger(object):
    """日志模块"""

    def __init__(self, name=None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        format_str = logging.Formatter(
            '%(asctime)s - [%(pathname)s line:%(lineno)d] => %(levelname)s: %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(format_str)
        self.logger.addHandler(stream_handler)

        file_handler = logging.FileHandler(filename='info.log', mode='a', encoding='utf-8')
        file_handler.setFormatter(format_str)
        self.logger.addHandler(file_handler)

        self.logger.setLevel(level)
