###
# Project: oghma
# Author: M-Davies
# https://github.com/M-Davies/oghma
###

import os
import platform
import logging
import datetime
import sys

FILE_DELIMITER = "\\" if platform.system() == "Windows" else "/"
CURRENT_DIR = f"{os.path.dirname(os.path.realpath(__file__))}{FILE_DELIMITER}"

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOG_FILE_HANDLER = logging.FileHandler(filename=f"{CURRENT_DIR}{FILE_DELIMITER}logs{FILE_DELIMITER}oghma-{datetime.now().strftime('%d-%m-%Y')}.log", encoding="utf-8", mode="a")
LOG_FILE_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_FILE_HANDLER)
LOG_OUTPUT_HANDLER = logging.StreamHandler(sys.stdout)
LOG_OUTPUT_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_OUTPUT_HANDLER)

###
# FUNC NAME: cleanup
# FUNC DESC: Cleans up all txt files created from commands. Fires on a schedule set by Heroku
# FUNC TYPE: Function
###
def cleanup():
    FOLDER = os.getcwd() + FILE_DELIMITER
    for filename in os.listdir(FOLDER):
        FILE = f"{FOLDER}{FILE_DELIMITER}{filename}"
        if ".md" in filename:
            LOGGER.info(f"Trying to clean { FILE }")

            os.remove(FILE)
            if os.path.exists(FILE):
                LOGGER.warn(f"Failed to delete { FILE }")
            else:
                LOGGER.info(f"{ FILE } successfully deleted!\n------")

    LOGGER.info("SUCCESS: All data files deleted!")

cleanup()
