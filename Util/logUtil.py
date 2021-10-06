import logging
import sys


class Logs:
    def __init__(self, cls_name) -> None:
        self.root = logging.getLogger(cls_name)
    
    def logger(self) -> logging:
        self.root.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.root.addHandler(handler)
        return self.root
