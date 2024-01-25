"""
# Project: oghma
# Author: M-Davies
# https://github.com/M-Davies/oghma
"""

# pyright: reportOptionalMemberAccess=false, reportGeneralTypeIssues=false

import config
from utils import generateFileName, getRequestType, constructResponse
from errors import codeError, argLengthError, invalidArgSupplied, invalidSizeSupplied, unrecognisedNumericOperator
from api import requestScryfall, requestOpen5e, getOpen5eRoot

import sys
import os
import requests
import random
from datetime import datetime
import logging
import re
import discord
from discord import app_commands
from typing import Optional

# Import dotenv (it's troublesome to install on mac for some reason)
from dotenv import load_dotenv
load_dotenv()

# Set up logging
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOG_FILE_HANDLER = logging.FileHandler(filename=f"{os.getcwd()}{config.FILE_DELIMITER}logs{config.FILE_DELIMITER}oghma-{datetime.now().strftime('%d-%m-%Y')}.log", encoding="utf-8", mode="a")
LOG_FILE_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_FILE_HANDLER)
LOG_OUTPUT_HANDLER = logging.StreamHandler(sys.stdout)
LOG_OUTPUT_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_OUTPUT_HANDLER)


class OghmaClient(discord.Client):
    """
    Sets up the root client that communicates with Discord
    """
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        LOGGER.info("Setting up...")
        await self.tree.fetch_commands()
        if os.environ['ENVIRONMENT'] is not None and os.environ['ENVIRONMENT'] != "PRODUCTION":
            LOGGER.info(f"Non-production environment ({os.environ['ENVIRONMENT']}) detected. Syncing with testing guild...")
            supportGuild = discord.Object(id=723473275803533323)
            self.tree.clear_commands(guild=supportGuild)
            self.tree.copy_global_to(guild=supportGuild)
        await self.tree.sync()
        LOGGER.info("Setup Finished.")


CLIENT = OghmaClient(intents=discord.Intents.default())


@CLIENT.event
async def on_ready():
    """
    FUNC NAME: on_ready
    FUNC DESC: Tells you when bot is ready to accept commands. Also cleans up temp files
    FUNC TYPE: Event
    """
    LOGGER.info(f"Logged in as {CLIENT.user.name} ({CLIENT.user.id})")


@CLIENT.tree.command(description="Displays a help message that shows usage information")
async def help(interaction: discord.Interaction):
    """
    FUNC NAME: /help
    FUNC DESC: Displays a help message that shows the bot is live
    FUNC TYPE: Command
    """
    await interaction.response.defer(thinking=True)
    helpEmbed = discord.Embed(
        title="Oghma",
        url="https://top.gg/bot/658336624647733258",
        description=f"__Current Latency__\n\n{round(CLIENT.latency, 1)} seconds\n\n__Available commands__\n\n**/help** - Displays this message (duh)\n\n**/roll [ROLLS]d[SIDES]** - Dice roller with calculator logic\n\n**/search [ENTITY]** - Searches the whole Open5e D&D database for your chosen entity.\n\n**/searchdir [DIRECTORY] [ENTITY]** - Searches a specific category of the Open5e D&D database for your chosen entity a lot faster than */search*.\n\n**/lst [DIRECTORY] [ENTITY]** - Queries the API to get all the fully and partially matching entities based on the search term.",
        color=discord.Colour.purple()
    )

    helpEmbed.set_author(
        name="Intoxication#0001",
        url="https://github.com/M-Davies",
        icon_url="https://github.com/M-Davies.png"
    )
    helpEmbed.set_thumbnail(url="https://i.imgur.com/HxuMICy.jpg")

    helpEmbed.add_field(name="LINKS", value="------------------", inline=False)
    helpEmbed.add_field(name="GitHub", value="https://github.com/M-Davies/oghma", inline=True)
    helpEmbed.add_field(name="Discord", value="https://discord.gg/8YZ2NZ5", inline=True)
    helpEmbed.set_footer(text="Feedback? Hate? Make it known to us! (see links above)")
    return await interaction.followup.send(embed=helpEmbed)


@CLIENT.tree.command(description="Runs a quick & easy dice roller")
@app_commands.describe(calculation="The calculation to conduct")
async def roll(interaction: discord.Interaction, calculation: str):
    """
    FUNC NAME: /roll
    FUNC DESC: Runs a dice roller
    FUNC TYPE: Command
    """

    LOGGER.info(f"Executing: /roll {calculation}")

    # Verify arg length isn't over limits
    if len(calculation) >= 201:
        LOGGER.info(f"Failed to execute /roll, args lengths too long = {calculation}")
        return await interaction.response.send_message(embed=argLengthError())

    # Parse input
    calculationList = calculation.split(" ")
    
    # Init response embed
    diceRollEmbed = discord.Embed(
        color=discord.Colour.purple()
    )
    diceRollEmbed.add_field(name="QUERY", value=calculationList, inline=False)
    diceRollEmbed.insert_field_at(index=2, name="RESULTS", value="----------", inline=False)
    diceRollEmbed.set_author(name=f"Rolled by {interaction.user.name}", icon_url=f"{interaction.user.display_avatar}")

    # Initialise nested result dictionary. Example for query `/roll 3d8 + 8`:
    # {
    #   "3d8" : {
    #               "results" : ['4', '8', '1'],
    #               "sectionTotal" : 13.0,
    #               "cumulativeTotal" : 13.0
    #   },
    #   "+" : {
    #               "results" : [],
    #               "sectionTotal" : 0.0,
    #               "cumulativeTotal" : 13.0
    #   },
    #   "8" : {
    #               "results" : [],
    #               "sectionTotal" : 8.0,
    #               "cumulativeTotal" : 21.0
    #   }
    # }
    diceRollResults = {}
    currentOperator = ""
    runningTotal = 0
    stepCount = 1

    # Iterate over arguments array
    await interaction.response.defer(thinking=True)
    for argument in calculationList:

        # Import cumulativeTotal from previous argument for the current argument
        diceRollResults[argument] = {
            "results": [],
            "sectionTotal": 0.0,
            "cumulativeTotal": runningTotal
        }

        # If arg is a operator, isn't the first character and is a single char
        if argument in config.NUMERIC_OPERATORS:
            if calculationList.index(argument) != 0:
                if len(argument) == 1:
                    currentOperator = argument
                else:
                    return await interaction.followup.send(embed=unrecognisedNumericOperator(argument))
            else:
                operatorAtFront = discord.Embed(
                    color=discord.Colour.red(),
                    title=f"THE `{argument}` OPERATOR CANNOT BE THE FIRST CHARACTER"
                )
                operatorAtFront.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

                return await interaction.followup.send(embed=operatorAtFront)

        # If the arg is a dice or a number
        else:

            # If it's a number...
            numCheck = ""
            try:
                numCheck = float(argument)
            except ValueError:
                pass

            if isinstance(numCheck, float):
                # Ensure number isn't too big
                if numCheck <= config.ROLL_MAX_PARAM_VALUE:
                    # Add to dict in same manner as a dice roll total
                    diceRollResults[argument]["sectionTotal"] = numCheck
                else:
                    return await interaction.followup.send(embed=invalidSizeSupplied(numCheck))

            # If it's a dice...
            else:

                # Verify arguments contains a valid request
                sanitisedCurrentDice = argument.lower()
                numberOfRolls = 1
                numberOfSides = 0
                regexReturn = re.search("(?P<rolls>[0-9]*)d(?P<sides>[0-9]+)", sanitisedCurrentDice)

                if regexReturn is not None:

                    # Default to 1 roll if none are supplied, otherwise use the rolls group
                    if regexReturn.group("rolls") != "":

                        # Checks the amount of rolls supplied is a number and isn't too high
                        try:
                            numberOfRolls = int(regexReturn.group("rolls"))

                            if numberOfRolls >= config.ROLL_MAX_PARAM_VALUE:
                                return await interaction.followup.send(embed=invalidSizeSupplied(numberOfRolls))

                        except ValueError:
                            return await interaction.followup.send(embed=invalidArgSupplied(regexReturn.group("rolls")))

                    # Checks the amount of sides supplied is a number and is valid
                    try:
                        numberOfSides = int(regexReturn.group("sides"))

                        if numberOfSides < 2 or numberOfSides >= config.ROLL_MAX_PARAM_VALUE:
                            return await interaction.followup.send(embed=invalidSizeSupplied(numberOfSides))

                    except ValueError:
                        return await interaction.followup.send(embed=invalidArgSupplied(regexReturn.group("sides")))

                else:
                    return await interaction.followup.send(embed=invalidArgSupplied("NO DICE SIDES DETECTED! TRY CHECKING YOUR SYNTAX AND /roll USAGE"))

                # Calculate dice rolls and append to the dict
                for currentRoll in range(1, numberOfRolls + 1):
                    diceRollResults[argument]["results"].append(random.randint(1, numberOfSides))

                # Calculate the section total and append to the dict
                diceSectionTotal = 0
                for currentResult in diceRollResults[argument]["results"]:
                    diceSectionTotal += currentResult

                diceRollResults[argument]["sectionTotal"] = diceSectionTotal

                # Append to embed
                diceRollEmbed.add_field(
                    name=f"__STEP {stepCount}__\n`{numberOfRolls}d{numberOfSides}` ROLLED |",
                    value=f"{diceRollResults[argument]['results']}\n*TOTAL = {diceRollResults[argument]['sectionTotal']}*",
                    inline=True
                )

            # Assign running total with what we have so far
            runningTotal = diceRollResults[argument]["sectionTotal"]

            # Apply an operator specified in the last arg (if it exists)
            if currentOperator != "":

                stepCount += 1

                # Extract previous total
                previousTotal = 0
                previousTotalKey = ""
                for currentDiceSectionKey in diceRollResults:
                    if currentDiceSectionKey == argument:
                        previousTotal = diceRollResults[previousTotalKey]["cumulativeTotal"]
                        break
                    else:
                        previousTotalKey = currentDiceSectionKey

                # Apply to current total
                if currentOperator == "+":
                    runningTotal = previousTotal + runningTotal
                elif currentOperator == "-":
                    runningTotal = previousTotal - runningTotal
                elif currentOperator == "*":
                    runningTotal = previousTotal * runningTotal
                elif currentOperator == "/":
                    runningTotal = previousTotal / runningTotal
                else:
                    return await interaction.followup.send(embed=unrecognisedNumericOperator(currentOperator))

                # Append to embed
                diceRollEmbed.add_field(
                    name=f"__STEP {stepCount}__\n`{currentOperator}` OPERATOR APPLIED! |",
                    value=f"{previousTotal}\n**{currentOperator}**\n{diceRollResults[argument]['sectionTotal']}\n*TOTAL = {runningTotal}*",
                    inline=True
                )

                currentOperator = ""

            # Calculate the total for the whole query so far
            diceRollResults[argument]["cumulativeTotal"] = runningTotal

            stepCount += 1

    # Append final total and send embed
    diceRollEmbed.insert_field_at(index=1, name="TOTAL", value=f"`{runningTotal}`", inline=False)
    return await interaction.followup.send(embed=diceRollEmbed)


@CLIENT.tree.command(description="Queries the Open5e API to get the requested entity")
@app_commands.rename(entityInput="entity")
@app_commands.describe(entityInput="The entity you would like to search for")
async def search(interaction: discord.Interaction, entityInput: Optional[str] = ""):
    """
    FUNC NAME: /search [ENTITY]
    FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
    FUNC TYPE: Command
    """

    LOGGER.info(f"Executing: /search {entityInput}")

    # Verify arg length isn't over limits
    if len(entityInput) >= 201:
        LOGGER.warning(f"Failed to execute /search, args lengths too long = {entityInput}")
        return await interaction.response.send_message(embed=argLengthError())

    # Send directory contents if no search term given
    await interaction.response.defer(thinking=True)
    if len(entityInput) <= 0:

        # Get objects from directory, store in file
        directoryRequest = requests.get("https://api.open5e.com/search/?format=json&limit=10000")

        if directoryRequest.status_code != 200:
            return await interaction.followup.send(embed=codeError(
                directoryRequest.status_code,
                "https://api.open5e.com/search/?format=json&limit=10000"
            ))

        # Generate a unique filename and write to it
        entityFileName = generateFileName("entsearch")

        LOGGER.info(f"Creating file: {entityFileName}")
        with open(f"{os.getcwd()}data{config.FILE_DELIMITER}{entityFileName}", "w+") as entityFile:
            for apiEntity in directoryRequest.json()["results"]:
                if "title" in apiEntity.keys():
                    entityFile.write(f"{apiEntity['title']}\n")
                else:
                    entityFile.write(f"{apiEntity['name']}\n")

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"See `{entityFileName}` for all searchable entities in this directory",
            description="Due to discord character limits regarding embeds, the results have to be sent in a file"
        )
        return await interaction.followup.send(embed=detailsEmbed, file=discord.File(f"{os.getcwd()}data/{entityFileName}"))

    # Filter input to remove whitespaces and set lowercase
    filteredEntityInput = "".join(entityInput).lower()

    # Use first word to narrow search results down for quicker response on some directories
    splitEntityInput = entityInput.split(' ')
    match = requestOpen5e(f"https://api.open5e.com/search/?format=json&limit=10000&text={splitEntityInput[0]}", filteredEntityInput, True, False)

    # An API Request failed
    if isinstance(match, dict) and "code" in match.keys():
        LOGGER.error(f"Open5e search/ API Request FAILED: {match}")
        return await interaction.followup.send(embed=codeError(match["code"], match["query"]))

    # No entity was found
    elif match == []:
        LOGGER.info(f"No match found for {filteredEntityInput} in search/ directory")
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR",
            description=f"No matches found for **{filteredEntityInput}** in the search/ directory"
        )
        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        return await interaction.followup.send(embed=noMatchEmbed)

    # Otherwise, construct & send responses
    else:
        responses = constructResponse(entityInput, match["route"], match["entity"])
        for response in responses["embeds"]:
            # Set a thumbnail for relevant embeds and on successful Scryfall request, overwriting all other thumbnail setup
            image = requestScryfall(splitEntityInput)

            if (not isinstance(image, int)):
                response.set_thumbnail(url=image)

            # Note partial match in footer of embed
            if match['partial'] is True:
                response.set_footer(text=f"NOTE: Your search term ({filteredEntityInput}) was a PARTIAL match to this entity.\nIf this isn't the entity you were expecting, try refining your search term or use /searchdir instead")
            else:
                response.set_footer(text="NOTE: If this isn't the entity you were expecting, try refining your search term or use `/searchdir` instead")

        for embedItem in responses["embeds"]:
            LOGGER.info(f"Sending embed - {embedItem.to_dict()}")
            await interaction.followup.send(embed=embedItem)
        if len(responses["files"]) > 0:
            LOGGER.info(f"Sending files - {responses['files']}")
            return await interaction.followup.send(files=responses["files"])


@CLIENT.tree.command(description="Queries the Open5e API to get an entity's information from a specified directory.")
@app_commands.rename(directoryInput="directory", entityInput="entity")
@app_commands.describe(directoryInput="The category to search for the entity in", entityInput="The entity you would like to search for")
async def searchdir(interaction: discord.Interaction, directoryInput: str, entityInput: Optional[str] = ""):
    """
    FUNC NAME: /searchdir [DIRECTORY] [ENTITY]
    FUNC DESC: Queries the Open5e DIRECTORY API.
    FUNC TYPE: Command
    """
    
    LOGGER.info(f"EXECUTING: /searchdir {directoryInput} {entityInput}")

    # Get api root directories
    await interaction.response.defer(thinking=True)
    directories = getOpen5eRoot()
    if isinstance(directories, int):
        return await interaction.followup.send(embed=codeError(directories, "https://api.open5e.com?format=json"))

    # Filter inputs
    filteredDirectoryInput = directoryInput.lower()
    filteredEntityInput = "".join(entityInput).lower()

    # Verify arg length isn't over limits
    if len(filteredEntityInput) >= 201:
        return await interaction.followup.send(embed=argLengthError())

    # search/ directory is best used with the dedicated /search command
    if "search" in filteredDirectoryInput:

        searchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"Requested Directory (`{directoryInput}`) is not a valid directory name",
            description=f"**Available Directories**\n{', '.join(directories)}"
        )

        searchEmbed.add_field(name="NOTE", value="Use `/search` for searching the `search/` directory")
        searchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await interaction.followup.send(embed=searchEmbed)
    
    # Verify directory exists
    if directories.count(filteredDirectoryInput) <= 0:

        noDirectoryEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"Requested Directory (`{filteredDirectoryInput}`) is not a valid directory name",
            description=f"**Available Directories**\n{', '.join(directories)}"
        )

        noDirectoryEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await interaction.followup.send(embed=noDirectoryEmbed)
    
    # Send directory contents if no search term given
    if len(filteredEntityInput) <= 0:

        # Get objects from directory, store in file
        directoryRequest = requests.get(f"https://api.open5e.com/{filteredDirectoryInput}/?format=json&limit=10000")

        if directoryRequest.status_code != 200:
            return await interaction.followup.send(embed=codeError(
                directoryRequest.status_code,
                f"https://api.open5e.com/{filteredDirectoryInput}/?format=json&limit=10000"
            ))

        entityNames = []
        for apiEntity in directoryRequest.json()["results"]:
            if "title" in apiEntity.keys():
                entityNames.append(apiEntity['title'])
            else:
                entityNames.append(apiEntity['name'])

        # Keep description word count low to account for names with lots of characters
        if len(entityNames) <= 200:
            detailsEmbed = discord.Embed(
                colour=discord.Colour.orange(),
                title="All searchable entities in this directory",
                description="\n".join(entityNames)
            )
            detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
            return await interaction.followup.send(embed=detailsEmbed)

        # Generate a unique filename and write to it
        entityDirFileName = generateFileName("entsearchdir")

        LOGGER.info(f"Creating file: {entityDirFileName}")
        with open(f"{os.getcwd()}data{config.FILE_DELIMITER}{entityDirFileName}", "w+") as entityFile:
            entityFile.write("\n".join(entityNames))

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"See `{entityDirFileName}` for all searchable entities in this directory",
            description="Due to discord character limits regarding embeds, the results have to be sent in a file"
        )
        detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        return await interaction.followup.send(embed=detailsEmbed, file=discord.File(f"{os.getcwd()}data/{entityDirFileName}"))

    # Use first word to narrow search results down for quicker response on some directories
    splitEntityInput = entityInput.split(" ")
    match = requestOpen5e(f"https://api.open5e.com/{filteredDirectoryInput}/?format=json&limit=10000&{getRequestType(directoryInput)}={splitEntityInput[0]}", filteredEntityInput, False, False)

    # An API Request failed
    if isinstance(match, dict) and "code" in match.keys():
        return await interaction.followup.send(embed=codeError(match['code'], match['query']))

    # No entity was found
    elif match == []:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR",
            description=f"No matches found for **{filteredEntityInput.upper()}** in the {filteredDirectoryInput} directory"
        )

        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await interaction.followup.send(embed=noMatchEmbed)

    # Otherwise, construct & send responses
    else:
        responses = constructResponse(entityInput, filteredDirectoryInput, match['entity'])
        for response in responses["embeds"]:
            # Set a thumbnail for relevant embeds and on successful Scryfall request, overwrites other thumbnail setup
            image = requestScryfall(splitEntityInput)

            if (not isinstance(image, int)):
                response.set_thumbnail(url=image)

            # Note partial match in footer of embed
            if match['partial'] is True:
                response.set_footer(text=f"NOTE: Your search term ({filteredEntityInput}) was a PARTIAL match to this entity.\nIf this isn't the entity you were expecting, try refining your search term")

        for embedItem in responses["embeds"]:
            await interaction.followup.send(embed=embedItem)
        if len(responses["files"]) > 0:
            return await interaction.followup.send(files=responses["files"])


@CLIENT.tree.command(description="Queries the Open5e API to get all the fully and partially matching entities based on the search term")
@app_commands.rename(entityInput="entity", directoryInput="directory")
@app_commands.describe(entityInput="The entity you would like to search for", directoryInput="The category to search for the entity in")
async def lst(interaction: discord.Interaction, entityInput: str, directoryInput: Optional[str] = ""):
    """
    FUNC NAME: /lst [DIRECTORY] [ENTITY]
    FUNC DESC: Queries the Open5e API to get all the fully and partially matching entities information in a list embed format.
    FUNC TYPE: Command
    """

    LOGGER.info(f"EXECUTING: /lst {entityInput} {directoryInput}")

    # Verify arg length isn't over limits
    if len(entityInput) >= 201:
        return await interaction.response.send_message(embed=argLengthError())

    # Check if we are searching in a directory or on all directories
    matches = None
    filteredEntityInput = "".join(entityInput).lower()
    splitEntityInput = entityInput.split(" ")
    filteredDirectoryInput = directoryInput.lower()

    # Get api root directories
    await interaction.response.defer(thinking=True)
    directories = getOpen5eRoot()
    if isinstance(directories, int):
        LOGGER.error(f"Open5e Root API Request FAILED: {directories}")
        return await interaction.followup.send(embed=codeError(directories, "https://api.open5e.com?format=json"))

    # Verify directory exists
    wideSearching = False
    if len(directoryInput) <= 0 or directories.count(directoryInput) <= 0:
        filteredDirectoryInput = "search"
        wideSearching = True
        await interaction.followup.send(
            embed=discord.Embed(
                color=discord.Colour.blue(),
                title="FINDING ALL ENTITIES IN SEARCH/ DIRECTORY...",
                description=f"WARNING: {directoryInput} is not a valid directory name. Your query will use the search/ directory instead. If this behaviour is unexpected, pass a valid directory name as your first parameter."
            ).set_footer(text=f"Valid directory names = {', '.join(directories)}")
        )

    # If an invalid or empty directory is given, default to wide search using search/ directory
    if wideSearching is True:
        matches = requestOpen5e(f"https://api.open5e.com/search?format=json&limit=10000&text={splitEntityInput[0]}", filteredEntityInput, wideSearching, True)
    else:
        # Use first word to narrow search results down for quicker response on some directories
        matches = requestOpen5e(f"https://api.open5e.com/{filteredDirectoryInput}/?format=json&limit=10000&{getRequestType(directoryInput)}={splitEntityInput[0]}", filteredEntityInput, wideSearching, True)

    # An API Request failed
    if isinstance(matches, dict) and "code" in matches.keys():
        return await interaction.followup.send(embed=codeError(matches['code'], matches['query']))
    # Nothing was found
    elif matches is []:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR",
            description=f"No matches found for **{filteredEntityInput}** in the database or requested directory"
        )
        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        LOGGER.info(f"No match found for {filteredEntityInput} in {filteredDirectoryInput}/ directory")
        return await interaction.followup.send(embed=noMatchEmbed)
    else:
        # Embeds have a max of 25 fields, so stick it in a file if we can't fit all of them in
        matchesEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"SEARCH RESULTS FOR {filteredEntityInput}",
            description="Results ***in italics*** are partial matches and may be less accurate. All others are full matches and line up with your search term as it is."
        )
        matchesEmbed.set_author(name=f"Requested by {interaction.user.display_name}", icon_url=f"{interaction.user.display_avatar}")
        
        if len(matches) < 25:
            for match in matches:
                # Documents do not have a name identifier key
                identifier = "name"
                if "title" in match['entity'].keys():
                    identifier = "title"

                # Display result in field title, directory in value
                entityDirectory = filteredDirectoryInput
                if wideSearching:
                    entityDirectory = match['entity']['route']

                if match['partial'] is True:
                    matchesEmbed.add_field(
                        name=f"*{match['entity'][identifier]}*",
                        value=f"*Directory = {entityDirectory[:-1]}*",
                        inline=True
                    )
                else:
                    matchesEmbed.add_field(
                        name=match['entity'][identifier],
                        value=f"Directory = {entityDirectory[:-1]}",
                        inline=True
                    )

            return await interaction.followup.send(embed=matchesEmbed)
        else:
            formattedMatches = ""
            for match in matches:
                # Documents do not have a name identifier key
                identifier = "name"
                if "title" in match['entity'].keys():
                    identifier = "title"

                # Display result in field title, directory in value
                if match['partial'] is True:
                    formattedMatches += f"*{match['entity'][identifier]} : Directory = {match['entity']['route'] if filteredDirectoryInput == '' else filteredDirectoryInput}*\n"
                else:
                    formattedMatches += f"{match['entity'][identifier]} : Directory = {match['entity']['route'] if filteredDirectoryInput == '' else filteredDirectoryInput}\n"

            # Create file and store matches in there
            matchesFileName = generateFileName("matches")
            LOGGER.info(f"Creating file: {matchesFileName}")
            with open(f"{os.getcwd()}data{config.FILE_DELIMITER}{matchesFileName}", "w+") as matchesFile:
                matchesFile.write(formattedMatches)

            matchesEmbed.add_field(name=f"See `{matchesFileName}` for the matched entities", value="Due to discord character limits regarding embeds, the results have to be sent in a file", inline=False)
            return await interaction.followup.send(embed=matchesEmbed, file=discord.File(f"{os.getcwd()}data/{matchesFileName}"))

CLIENT.run(os.environ['BOT_KEY'])
