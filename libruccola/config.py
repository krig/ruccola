import os
import configparser
CONFIG = os.path.expanduser("~/.config/ruccola/config.ini")

class Config(object):
    def __init__(self):
        self.server = None
        self.user_id = None
        self.token = None

def parse():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG)
    ret = Config()
    ret.server = cfg["auth"]["server"]
    ret.user_id = cfg["auth"]["user_id"]
    ret.token = cfg["auth"]["token"]
    return ret
