###
# Project: oghma
# Author: shadowedlucario
# https://github.com/shadowedlucario
###

import os

###
# FUNC NAME: cleanup
# FUNC DESC: Cleans up all txt files created from the last command
# FUNC TYPE: Function
###
def cleanup():
    for txtFile in os.listdir():

        if ".txt" in txtFile:
            print(f"Trying to clean { txtFile }")

            if os.path.exists(txtFile):
                os.remove(txtFile)

                if os.path.exists(txtFile): print(f"WARNING: { txtFile } was not deleted!")
                else: print(f"SUCCESS: { txtFile } successfully deleted!\n------")

    print("SUCCESS: All text files deleted!")

cleanup()