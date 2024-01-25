###
# Project: oghma
# Author: M-Davies
# https://github.com/M-Davies/oghma
###

from utils import getFileDelimiter
import os
import logging
import datetime
import sys


CURRENT_DIR = f"{os.path.dirname(os.path.realpath(__file__))}{getFileDelimiter()}"

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOG_FILE_HANDLER = logging.FileHandler(filename=f"{CURRENT_DIR}{getFileDelimiter()}logs{getFileDelimiter()}oghma-{datetime.now().strftime('%d-%m-%Y')}.log", encoding="utf-8", mode="a")
LOG_FILE_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_FILE_HANDLER)
LOG_OUTPUT_HANDLER = logging.StreamHandler(sys.stdout)
LOG_OUTPUT_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_OUTPUT_HANDLER)


def cleanup():
    """
    FUNC NAME: cleanup
    FUNC DESC: Cleans up all txt files created from commands. Fires on a schedule set by Heroku
    FUNC TYPE: Function
    """
    FOLDER = os.getcwd() + getFileDelimiter()
    for filename in os.listdir(FOLDER):
        FILE = f"{FOLDER}{getFileDelimiter()}{filename}"
        if ".md" in filename:
            LOGGER.info(f"Trying to clean { FILE }")

            os.remove(FILE)
            if os.path.exists(FILE):
                LOGGER.warn(f"Failed to delete { FILE }")
            else:
                LOGGER.info(f"{ FILE } successfully deleted!\n------")

    LOGGER.info("SUCCESS: All data files deleted!")


cleanup()
