import logging
import sys


class Logs:
    def __init__(self, cls_name: str, output: int=0) -> None:
        """
        @param: cls_name: set logger name
        @param: output: File Handler Toggle ON/OFF
        """
        # self.f_handler = f_handler
        self.root = logging.getLogger(cls_name)
        self.log_level = logging.INFO # set logging level
        self.output = output
        if self.output:
            self.logger_file = f'{__name__}.log'
    
    def logger(self) -> logging:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.root.setLevel(self.log_level)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(self.log_level)
        stream_handler.setFormatter(formatter)

        if not self.output:
            self.root.addHandler(stream_handler)
        
        else:
            file_handler = logging.FileHandler(self.logger_file)
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            self.root.addHandler(file_handler)
            self.root.addHandler(stream_handler)

        return self.root
