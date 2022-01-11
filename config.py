import json
import logging

CONFIG = None
with open('config.json', 'w') as f:
    CONFIG = json.load(f)


LOGGING_LEVEL = {
    'CRITICAL': logging.CRITICAL,
    'FATAL': logging.FATAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOGGING_LEVEL[CONFIG['logging_level']])
    handler = logging.FileHandler(CONFIG['logging_file'])
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    return logger
