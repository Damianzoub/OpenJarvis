import logging

DANGER = 45  

logger = logging.Logger("OpenJarvis")

if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logging.addLevelName(DANGER, "DANGER")
