###
# Project: oghma
# Author: M-Davies
# https://github.com/M-Davies/oghma
###

import os
import re

###
# FUNC NAME: cleanup
# FUNC DESC: Cleans up all txt files created from commands. Fires on a schedule set by Heroku
# FUNC TYPE: Function
###
def cleanup():
    FOLDER = os.getcwd() + "\\data"
    for filename in os.listdir(FOLDER):

        if ".md" in filename:
            FILE = f"{FOLDER}\{filename}"
            print(f"Trying to clean { FILE }")

            os.remove(FILE)
            if os.path.exists(FILE):
                print(f"WARNING: { FILE } was not deleted!")
            else:
                print(f"SUCCESS: { FILE } successfully deleted!\n------")

    print("SUCCESS: All data files deleted!")

cleanup()