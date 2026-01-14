import logging
import sys

LOG_NAME = "career_unplugged"
_CONFIGURED = False


class Log:
    @staticmethod
    def setup(application_name: str | None = None) -> logging.Logger:
        global _CONFIGURED
        if _CONFIGURED:
            return logging.getLogger(LOG_NAME)

        fmt = (
            "%(name)s %(module)s %(funcName)s %(lineno)d - "
            f"{application_name or LOG_NAME} - %(levelname)s - %(message)s"
        )
        formatter = logging.Formatter(
            fmt=fmt,
            datefmt="%Y-%m-%d %H:%M:%S(%Z)",
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        logger = logging.getLogger(LOG_NAME)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        _CONFIGURED = True
        return logger

    @staticmethod
    def debug(message: str) -> None:
        logging.getLogger(LOG_NAME).debug(message)

    @staticmethod
    def info(message: str) -> None:
        logging.getLogger(LOG_NAME).info(message)

    @staticmethod
    def warning(message: str) -> None:
        logging.getLogger(LOG_NAME).warning(message)

    @staticmethod
    def error(message: str) -> None:
        logging.getLogger(LOG_NAME).error(message)

    @staticmethod
    def exception(message: str) -> None:
        logging.getLogger(LOG_NAME).exception(message)
