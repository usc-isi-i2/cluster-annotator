import json
import logging


LOGGING_LEVEL = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}


def get_logger(name, cfg):
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_LEVEL[cfg['logging_level']])
    handler = logging.FileHandler(cfg['logging_file'])
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger


def get_config(filename):
    with open(filename) as f:
        return json.load(f)


config = None
