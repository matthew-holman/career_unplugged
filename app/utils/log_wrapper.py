import logging

from enum import Enum


class LogLevels(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


class LoggerFactory:
    _log = None

    @staticmethod
    def _create_logger(log_file: str | None, log_level: LogLevels, console_log: bool):
        handlers = []
        if log_file is not None:
            # handlers.append(logging.FileHandler(log_file))
            pass
        if console_log:
            handlers.append(logging.StreamHandler())

        # set the logging format
        log_format = "%(asctime)s:%(levelname)s:%(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=handlers,
        )
        LoggerFactory._log = logging.getLogger()

        # set the logging level based on the user selection
        if log_level == "INFO":
            LoggerFactory._log.setLevel(logging.INFO)
        elif log_level == "ERROR":
            LoggerFactory._log.setLevel(logging.ERROR)
        elif log_level == "DEBUG":
            LoggerFactory._log.setLevel(logging.DEBUG)
        return LoggerFactory._log

    @staticmethod
    def get_logger(
        log_file: str | None, log_level: LogLevels, console_log: bool = True
    ):
        logger = LoggerFactory._create_logger(log_file, log_level, console_log)
        return logger
