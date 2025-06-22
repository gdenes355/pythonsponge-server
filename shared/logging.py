import logging
import sys

logger = logging.getLogger("pythonsponge")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)s | %(asctime)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

