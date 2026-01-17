import logging
import sys


def setup_logging(log_level):

    # setup log
    log_format = logging.Formatter(
        "%(asctime)s - %(module)-10s - %(levelname)-8s - %(message)s"
    )
    # configure the client logging
    log = logging.getLogger("")
    # has to be set to debug as is the root logger
    log.setLevel(log_level)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)
