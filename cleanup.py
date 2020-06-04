###
# Project: oghma
# Author: shadowedlucario
# https://github.com/shadowedlucario
###

import os
import re

###
# FUNC NAME: cleanup
# FUNC DESC: Cleans up all txt files created from commands. Fires on a schedule set by Heroku
# FUNC TYPE: Function
###
def cleanup():
    for filename in os.listdir():

        if re.search(".*-.*\.txt", filename) != None:
            print(f"Trying to clean { filename }")

            if os.path.exists(filename):
                os.remove(filename)

                if os.path.exists(filename): print(f"WARNING: { filename } was not deleted!")
                else: print(f"SUCCESS: { filename } successfully deleted!\n------")

    print("SUCCESS: All text files deleted!")

cleanup()