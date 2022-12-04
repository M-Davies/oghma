###
# Project: oghma
# Author: M-Davies
# https://github.com/M-Davies/oghma
###

import os
import platform

FILE_DELIMITER = "\\" if platform.system() == "Windows" else "/"

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
            print(f"INFO: Trying to clean { FILE }")

            os.remove(FILE)
            if os.path.exists(FILE):
                print(f"WARNING: { FILE } was not deleted!")
            else:
                print(f"SUCCESS: { FILE } successfully deleted!\n------")
        else:
            print(f"INFO: Skipping non markdown file { FILE }")

    print("SUCCESS: All data files deleted!")

cleanup()