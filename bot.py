###
# Project: oghma
# Author: M-Davies
# https://github.com/M-Davies/oghma
###

import sys
import os
import requests
import random
from datetime import datetime
import logging
import re
import platform
import discord
from discord import app_commands
from typing import Optional

# Import dotenv (it's troublesome to install on mac for some reason)
from dotenv import load_dotenv
load_dotenv()

### CONSTANTS ###
FILE_DELIMITER = "/"
if platform.system() == "Windows":
    FILE_DELIMITER = "\\"
CURRENT_DIR = f"{os.path.dirname(os.path.realpath(__file__))}/"

class OghmaClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

INTENTS = discord.Intents.default()
CLIENT = OghmaClient(intents=INTENTS)

SEARCH_PARAM_DIRECTORIES = ["spells", "monsters", "magicitems", "weapons"]
NUMERIC_OPERATORS = ["+", "-", "*", "/"]
COMMAND_LIST = ["roll", "search", "searchdir", "help", "lst"]
ROLL_MAX_PARAM_VALUE = 10001

# Set up logging
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
LOG_FILE_HANDLER = logging.FileHandler(filename=f"{CURRENT_DIR}{FILE_DELIMITER}logs{FILE_DELIMITER}oghma-{datetime.now().strftime('%d-%m-%Y')}.log", encoding="utf-8", mode="a")
LOG_FILE_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_FILE_HANDLER)
LOG_OUTPUT_HANDLER = logging.StreamHandler(sys.stderr)
LOG_OUTPUT_HANDLER.setFormatter(logging.Formatter("%(asctime)s: %(levelname)s: %(name)s: %(message)s"))
LOGGER.addHandler(LOG_OUTPUT_HANDLER)

###
# FUNC NAME: on_ready
# FUNC DESC: Tells you when bot is ready to accept commands. Also cleans up temp files
# FUNC TYPE: Event
###
@CLIENT.event
async def on_ready():
    for g in CLIENT.guilds:
        LOGGER.info(f"Syncing commands for guild = {g.name}:{g.id}...")
        try:
            currentGuild = discord.Object(id=g.id)
            CLIENT.tree.copy_global_to(guild=currentGuild)
            await CLIENT.tree.sync(guild=currentGuild)
        except Exception as e:
            LOGGER.warning(f"FAILED to sync commands for {g.name}:{g.id}. Error = {e}")
    LOGGER.info(f"Logged in as {CLIENT.user.name} ({CLIENT.user.id})")
    
###
# FUNC NAME: searchResponse
# FUNC DESC: Searches the API response for the user input. Returns empty list if nothing was found
# FUNC TYPE: Function
###
def searchResponse(responseResults, filteredEntityInput: str):

    # Sets entity name/title to lowercase and removes spaces
    def parse(entityHeader):
        return entityHeader.replace(" ", "").lower()

    matches = []

    for apiEntity in responseResults:

        # Documents don't have a name attribute
        if "title" in apiEntity:

            # Look for a partial match if no exact match can be found. Exact matches are pushed to front
            if filteredEntityInput == parse(apiEntity["title"]):
                matches.insert(0, {"entity": apiEntity, "partial": False})
            elif filteredEntityInput in parse(apiEntity["title"]):
                matches.append({"entity": apiEntity, "partial": True})

        elif "name" in apiEntity:

            if filteredEntityInput == parse(apiEntity["name"]):
                matches.insert(0, {"entity": apiEntity, "partial": False})
            elif filteredEntityInput in parse(apiEntity["name"]):
                matches.append({"entity": apiEntity, "partial": True})

    return matches

###
# FUNC NAME: requestScryfall
# FUNC DESC: Queries the Scryfall API to obtain a thumbnail image.
# FUNC TYPE: Function
###
def requestScryfall(splitSearchTerm: list):

    requestStr = f"https://api.scryfall.com/cards/search?q={' '.join(splitSearchTerm)}&include_extras=true&include_multilingual=true&include_variations=true"
    scryfallRequest = requests.get(requestStr)

    # Try again with the first arg if nothing was found
    foundItem = {}
    if scryfallRequest.status_code == 404:
        LOGGER.info(f"Scryfall 1st Attempt - No matches found for: {requestStr}")
        requestStr = f"https://api.scryfall.com/cards/search?q={splitSearchTerm[0]}&include_extras=true&include_multilingual=true&include_variations=true"
        scryfallWordRequest = requests.get(requestStr)

        if scryfallWordRequest.status_code != 200:
            LOGGER.info(f"Scryfall 2nd Attempt - No matches found for: {requestStr}")
            return scryfallWordRequest.status_code
        else:
            foundItem = scryfallWordRequest.json()["data"][0]

    # Return code if API request failed
    elif scryfallRequest.status_code != 200:
        LOGGER.warning(f"Scryfall 1st Attempt - API Request failed for: {requestStr}")
        return scryfallRequest.status_code

    # Otherwise, return the cropped image url
    else:
        foundItem = scryfallRequest.json()["data"][0]
    
    # Verify there is a valid card face and image
    if "card_faces" in foundItem.keys() and len(foundItem["card_faces"]) >= 1:
        foundCardFace = list(foundItem["card_faces"])[0]
        if "image_uris" in foundCardFace.keys() and len(foundCardFace["image_uris"].keys()) >= 1:
            imageUris = dict(foundCardFace["image_uris"])
            if "art_crop" in imageUris.keys():
                return imageUris["art_crop"]
    # Otherwise, no valid image found
    return 404

###
# FUNC NAME: getFilterType
# FUNC DESC: Calculates the filter type based on what is supported by open5e and the requested route to search
# FUNC TYPE: Function
###
def getRequestType(route: str):
    # Determine filter type (search can only be used for some directories)
    if route in SEARCH_PARAM_DIRECTORIES:
        return "search"
    else:
        return "text"

###
# FUNC NAME: requestOpen5e
# FUNC DESC: Queries the Open5e API and returns an array of results
# FUNC TYPE: Function
###
def requestOpen5e(query: str, filteredEntityInput: str, wideSearch: bool, listResults: bool):

    # API Request
    request = requests.get(query)

    # Return code if not successful
    if request.status_code != 200:
        return {"code": request.status_code, "query": query}

    # Iterate through the results
    results = searchResponse(request.json()["results"], filteredEntityInput)

    if results == []:
        # No full or partial matches were found
        return []
    elif listResults is True:
        # Return all the full and partial matches
        return results
    else:
        firstMatchedEntity = results[0]
        if wideSearch is True:
            # Request directory using the first word of the name to filter results
            route = firstMatchedEntity['entity']["route"]

            # Determine filter type (search can only be used for some directories)
            filterType = getRequestType(route)

            if "title" in results:
                directoryRequest = requests.get(
                    f"https://api.open5e.com/{route}?format=json&limit=10000&{filterType}={firstMatchedEntity['entity']['title'].split()[0]}"
                )
            else:
                directoryRequest = requests.get(
                    f"https://api.open5e.com/{route}?format=json&limit=10000&{filterType}={firstMatchedEntity['entity']['name'].split()[0]}"
                )

            # Return code if not successful
            if directoryRequest.status_code != 200:
                return {
                    "code": directoryRequest.status_code,
                    "query": f"https://api.open5e.com/{route}?format=json&limit=10000&search={firstMatchedEntity['entity']['name'].split()[0]}"
                }

            # Search response again for the actual object, return empty array if none was found
            actualMatch = searchResponse(directoryRequest.json()["results"], filteredEntityInput)
            if actualMatch != []:
                actualMatch[0]["route"] = route
                return actualMatch[0]
            else:
                return []
        else:
            # We already got a match, return it
            return firstMatchedEntity


###
# FUNC NAME: constructResponse
# FUNC DESC: Constructs embed responses from the API object.
# FUNC TYPE: Function
###
def constructResponse(entityInput: str, route: str, matchedObj: dict):
    responses = {"files": list(), "embeds": list()}

    # Document
    if "document" in route:
        # Get document link
        docLink = matchedObj['url']
        if "http" not in docLink:
            docLink = f"http://{matchedObj['url']}"

        if len(matchedObj["desc"]) >= 2048:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['title']} (DOCUMENT)",
                description=matchedObj["desc"][:2047],
                url=docLink
            )
            documentEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:])
        else:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['title']} (DOCUMENT)",
                description=matchedObj["desc"],
                url=docLink
            )
        documentEmbed.add_field(name="Authors", value=matchedObj["author"], inline=False)
        documentEmbed.add_field(name="Link", value=matchedObj["url"], inline=True)
        documentEmbed.add_field(name="Version Number", value=matchedObj["version"], inline=True)
        documentEmbed.add_field(name="Copyright", value=matchedObj["copyright"], inline=False)

        documentEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")

        responses["embeds"].append(documentEmbed)

    # Spell
    elif "spell" in route:

        spellLink = f"https://open5e.com/spells/{matchedObj['slug']}/"
        if len(matchedObj["desc"]) >= 2048:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (SPELL)",
                description=matchedObj["desc"][:2047],
                url=spellLink
            )
            spellEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:], inline=False)
        else:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["name"],
                description=f"{matchedObj['desc']} (SPELL)",
                url=spellLink
            )

        if matchedObj["higher_level"] != "":
            spellEmbed.add_field(name="Higher Level", value=matchedObj["higher_level"], inline=False)

        spellEmbed.add_field(name="School", value=matchedObj["school"], inline=False)
        spellEmbed.add_field(name="Level", value=matchedObj["level"], inline=True)
        spellEmbed.add_field(name="Duration", value=matchedObj["duration"], inline=True)
        spellEmbed.add_field(name="Casting Time", value=matchedObj["casting_time"], inline=True)
        spellEmbed.add_field(name="Range", value=matchedObj["range"], inline=True)
        spellEmbed.add_field(name="Concentration?", value=matchedObj["concentration"], inline=True)
        spellEmbed.add_field(name="Ritual?", value=matchedObj["ritual"], inline=True)

        spellEmbed.add_field(name="Spell Components", value=matchedObj["components"], inline=True)
        if "M" in matchedObj["components"]:
            spellEmbed.add_field(name="Material", value=matchedObj["material"], inline=True)
        spellEmbed.add_field(name="Page Number", value=matchedObj["page"], inline=True)

        spellEmbed.set_thumbnail(url="https://i.imgur.com/W15EmNT.jpg")

        responses["embeds"].append(spellEmbed)

    # Monster
    elif "monster" in route:
        ## 1ST EMBED ##
        monsterLink = f"https://open5e.com/monsters/{matchedObj['slug']}/"
        monsterEmbedBasics = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (MONSTER) - STATS",
            description="**TYPE**: {}\n**SUBTYPE**: {}\n**ALIGNMENT**: {}\n**SIZE**: {}\n**CHALLENGE RATING**: {}".format(
                matchedObj["type"] if matchedObj["type"] != "" else "None",
                matchedObj["subtype"] if matchedObj["subtype"] != "" else "None",
                matchedObj["alignment"] if matchedObj["alignment"] != "" else "None",
                matchedObj["size"],
                matchedObj["challenge_rating"]
            ),
            url=monsterLink
        )

        # Str
        if matchedObj["strength_save"] is not None:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value=f"{matchedObj['strength']} (SAVE: **{matchedObj['strength_save']}**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value=f"{matchedObj['strength']}",
                inline=True
            )

        # Dex
        if matchedObj["dexterity_save"] is not None:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value=f"{matchedObj['dexterity']} (SAVE: **{matchedObj['dexterity_save']}**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value=f"{matchedObj['dexterity']}",
                inline=True
            )

        # Con
        if matchedObj["constitution_save"] is not None:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value=f"{matchedObj['constitution']} (SAVE: **{matchedObj['constitution_save']}**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value=f"{matchedObj['constitution']}",
                inline=True
            )

        # Int
        if matchedObj["intelligence_save"] is not None:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value=f"{matchedObj['intelligence']} (SAVE: **{matchedObj['intelligence_save']}**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value=f"{matchedObj['intelligence']}",
                inline=True
            )

        # Wis
        if matchedObj["wisdom_save"] is not None:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value=f"{matchedObj['wisdom']} (SAVE: **{matchedObj['wisdom_save']}**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value=f"{matchedObj['wisdom']}",
                inline=True
            )

        # Cha
        if matchedObj["charisma_save"] is not None:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value=f"{matchedObj['charisma']} (SAVE: **{matchedObj['charisma_save']}**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value=f"{matchedObj['charisma']}",
                inline=True
            )

        # Hit points/dice
        monsterEmbedBasics.add_field(
            name=f"HIT POINTS (**{str(matchedObj['hit_points'])}**)",
            value=matchedObj["hit_dice"],
            inline=True
        )

        # Speeds
        monsterSpeeds = ""
        for speedType, speed in matchedObj["speed"].items():
            monsterSpeeds += f"**{speedType}**: {speed}\n"
        monsterEmbedBasics.add_field(name="SPEED", value=monsterSpeeds, inline=True)

        # Armour
        monsterEmbedBasics.add_field(
            name="ARMOUR CLASS",
            value=f"{str(matchedObj['armor_class'])} ({matchedObj['armor_desc']})",
            inline=True
        )

        responses["embeds"].append(monsterEmbedBasics)

        ## 2ND EMBED ##
        monsterEmbedSkills = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (MONSTER) - SKILLS & PROFICIENCIES",
            url=monsterLink
        )

        # Skills & Perception
        if matchedObj["skills"] != {}:
            monsterSkills = ""
            for skillName, skillValue in matchedObj["skills"].items():
                monsterSkills += f"**{skillName}**: {skillValue}\n"
            monsterEmbedSkills.add_field(name="SKILLS", value=monsterSkills, inline=True)

        # Senses
        monsterEmbedSkills.add_field(name="SENSES", value=matchedObj["senses"], inline=True)

        # Languages
        if matchedObj["languages"] != "":
            monsterEmbedSkills.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Damage conditionals
        monsterEmbedSkills.add_field(
            name="STRENGTHS & WEAKNESSES",
            value="**VULNERABLE TO:** {}\n**RESISTANT TO:** {}\n**IMMUNE TO:** {}".format(
                matchedObj["damage_vulnerabilities"] if matchedObj["damage_vulnerabilities"] != "" else "Nothing",
                matchedObj["damage_resistances"] if matchedObj["damage_resistances"] != "" else "Nothing",
                matchedObj["damage_immunities"] if matchedObj["damage_immunities"] != "" else "Nothing" + ", " + matchedObj["condition_immunities"] if matchedObj["condition_immunities"] is not None else "Nothing",
            ),
            inline=False
        )

        responses["embeds"].append(monsterEmbedSkills)

        ## 3RD EMBED ##
        monsterEmbedActions = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (MONSTER) - ACTIONS & ABILITIES",
            url=monsterLink
        )

        # Actions
        for action in matchedObj["actions"]:
            monsterEmbedActions.add_field(
                name=f"{action['name']} (ACTION)",
                value=action["desc"],
                inline=False
            )

        # Reactions
        if matchedObj["reactions"] != "":
            for reaction in matchedObj["reactions"]:
                monsterEmbedActions.add_field(
                    name=f"{reaction['name']} (REACTION)",
                    value=reaction["desc"],
                    inline=False
                )

        # Specials
        for special in matchedObj["special_abilities"]:
            if len(special["desc"]) >= 1024:
                monsterEmbedActions.add_field(
                    name=f"{special['name']} (SPECIAL)",
                    value=special["desc"][:1023],
                    inline=False
                )
                monsterEmbedActions.add_field(
                    name=f"{special['name']} (SPECIAL) Continued...",
                    value=special["desc"][1024:],
                    inline=False
                )
            else:
                monsterEmbedActions.add_field(
                    name=f"{special['name']} (SPECIAL)",
                    value=special["desc"],
                    inline=False
                )

        # Spells
        if matchedObj["spell_list"] != []:

            for spell in matchedObj["spell_list"]:
                # Split the spell link down (e.g. https://api.open5e.com/spells/light/), [:-1] removes trailing whitespace
                spellSplit = spell.replace("-", " ").split("/")[:-1]

                monsterEmbedActions.add_field(
                    name=spellSplit[-1],
                    value=f"To see spell info, `/searchdir spells {spellSplit[-1]}`",
                    inline=False
                )

        responses["embeds"].append(monsterEmbedActions)

        ## 4TH EMBED (only used if it has legendary actions) ##
        if matchedObj["legendary_desc"] != "":
            monsterEmbedLegend = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (MONSTER): LEGENDARY ACTIONS & ABILITIES",
                description=matchedObj["legendary_desc"],
                url=monsterLink
            )

            for action in matchedObj["legendary_actions"]:
                monsterEmbedLegend.add_field(
                    name=action["name"],
                    value=action["desc"],
                    inline=False
                )

            responses["embeds"].append(monsterEmbedLegend)

        # Author & Image for all embeds
        for embed in responses["embeds"]:
            if matchedObj["img_main"] is not None:
                embed.set_thumbnail(url=matchedObj["img_main"])
            else:
                embed.set_thumbnail(url="https://i.imgur.com/6HsoQ7H.jpg")

    # Background
    elif "background" in route:

        # 1st Embed (Basics)
        bckLink = "https://open5e.com/sections/backgrounds"
        backgroundEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (BACKGROUND) - BASICS",
            description=matchedObj["desc"],
            url=bckLink
        )

        # Profs
        if matchedObj["tool_proficiencies"] is not None:
            backgroundEmbed.add_field(
                name="PROFICIENCIES",
                value=f"**SKILLS**: {matchedObj['skill_proficiencies']}\n**TOOLS**: {matchedObj['tool_proficiencies']}",
                inline=True
            )
        else:
            backgroundEmbed.add_field(
                name="PROFICIENCIES",
                value=f"**SKILL**: {matchedObj['skill_proficiencies']}",
                inline=True
            )

        # Languages
        if matchedObj["languages"] is not None:
            backgroundEmbed.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Equipment
        backgroundEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)

        # Feature
        backgroundEmbed.add_field(name=matchedObj["feature"], value=matchedObj["feature_desc"], inline=False)

        responses["embeds"].append(backgroundEmbed)

        # 2nd Embed (feature)
        backgroundFeatureEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (BACKGROUND)\nFEATURE ({matchedObj['feature']})",
            description=matchedObj["feature_desc"],
            url=bckLink
        )

        responses["embeds"].append(backgroundFeatureEmbed)

        # 3rd Embed & File (suggested characteristics)
        if matchedObj["suggested_characteristics"] is not None:

            if len(matchedObj["suggested_characteristics"]) <= 2047:

                backgroundChars = discord.Embed(
                    colour=discord.Colour.green(),
                    title=f"{matchedObj['name']} (BACKGROUND): CHARACTERISTICS",
                    description=matchedObj["suggested_characteristics"],
                    url=bckLink
                )

                responses["embeds"].append(backgroundChars)

            else:
                backgroundChars = discord.Embed(
                    colour=discord.Colour.green(),
                    title=f"{matchedObj['name']} (BACKGROUND): CHARACTERISTICS",
                    description=matchedObj["suggested_characteristics"][:2047],
                    url=bckLink
                )

                bckFileName = generateFileName("background")

                backgroundChars.add_field(
                    name="LENGTH OF CHARACTERISTICS TOO LONG FOR DISCORD",
                    value=f"See `{bckFileName}` for full description",
                    inline=False
                )
                responses["embeds"].append(backgroundChars)

                # Create characteristics file
                LOGGER.info(f"Creating file: {bckFileName}")
                with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{bckFileName}", "w+") as characteristicsFile:
                    characteristicsFile.write(matchedObj["suggested_characteristics"])

                responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + bckFileName}"))

        for response in responses["embeds"]:
            response.set_thumbnail(url="https://i.imgur.com/GhGODan.jpg")

    # Plane
    elif "plane" in route:
        planeEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (PLANE)",
            description=matchedObj["desc"],
            url="https://open5e.com/sections/planes"
        )

        planeEmbed.set_thumbnail(url="https://i.imgur.com/GJk1HFh.jpg")

        responses["embeds"].append(planeEmbed)

    # Section
    elif "section" in route:

        secLink = f"https://open5e.com/sections/{matchedObj['slug']}/"
        if len(matchedObj["desc"]) >= 2048:

            sectionEmbedDesc = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (SECTION) - {matchedObj['parent']}",
                description=matchedObj["desc"][:2047],
                url=secLink
            )

            sectionFilename = generateFileName("section")
            sectionEmbedDesc.add_field(
                name="LENGTH OF DESCRIPTION TOO LONG FOR DISCORD",
                value=f"See `{sectionFilename}` for full description",
                inline=False
            )
            sectionEmbedDesc.set_thumbnail(url="https://i.imgur.com/J75S6bF.jpg")
            responses["embeds"].append(sectionEmbedDesc)

            # Full description as a file
            LOGGER.info(f"Creating file: {sectionFilename}")
            with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{sectionFilename}", "w+") as secDescFile:
                secDescFile.write(matchedObj["desc"])
            responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + sectionFilename}"))

        else:
            sectionEmbedDesc = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (SECTION) - {matchedObj['parent']}",
                description=matchedObj["desc"],
                url=secLink
            )
            sectionEmbedDesc.set_thumbnail(url="https://i.imgur.com/J75S6bF.jpg")
            responses["embeds"].append(sectionEmbedDesc)

    # Feat
    elif "feat" in route:

        # Open5e website doesn't have a website entry for Urls yet
        featEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (FEAT)",
            description=f"PREREQUISITES: **{matchedObj['prerequisite']}**"
        )
        featEmbed.add_field(name="DESCRIPTION", value=matchedObj["desc"], inline=False)
        featEmbed.set_thumbnail(url="https://i.imgur.com/X1l7Aif.jpg")

        responses["embeds"].append(featEmbed)

    # Condition
    elif "condition" in route:

        conLink = "https://open5e.com/gameplay-mechanics/conditions"
        if len(matchedObj["desc"]) >= 2048:
            conditionEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (CONDITION)",
                description=matchedObj["desc"][:2047],
                url=conLink
            )
            conditionEmbed.add_field(name="DESCRIPTION continued...", value=matchedObj["desc"][2048:], inline=False)

        else:
            conditionEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (CONDITION)",
                description=matchedObj["desc"],
                url=conLink
            )
        conditionEmbed.set_thumbnail(url="https://i.imgur.com/tOdL5n3.jpg")

        responses["embeds"].append(conditionEmbed)

    # Race
    elif "race" in route:
        raceLink = f"https://open5e.com/races/{matchedObj['slug']}"
        raceEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (RACE)",
            description=matchedObj["desc"],
            url=raceLink
        )

        # Asi Description
        raceEmbed.add_field(name="BENEFITS", value=matchedObj["asi_desc"], inline=False)

        # Age, Alignment, Size
        raceEmbed.add_field(name="AGE", value=matchedObj["age"], inline=True)
        raceEmbed.add_field(name="ALIGNMENT", value=matchedObj["alignment"], inline=True)
        raceEmbed.add_field(name="SIZE", value=matchedObj["size"], inline=True)

        # Speeds
        raceEmbed.add_field(name="SPEEDS", value=matchedObj["speed_desc"], inline=False)

        # Languages
        raceEmbed.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Vision buffs
        if matchedObj["vision"] != "":
            raceEmbed.add_field(name="VISION", value=matchedObj["vision"], inline=True)

        # Traits
        if matchedObj["traits"] != "":

            if len(matchedObj["traits"]) >= 1024:
                raceEmbed.add_field(name="TRAITS", value=matchedObj["traits"][:1023], inline=False)
                raceEmbed.add_field(name="TRAITS continued...", value=matchedObj["traits"][1024:], inline=False)
            else:
                raceEmbed.add_field(name="TRAITS", value=matchedObj["traits"], inline=False)

        raceEmbed.set_thumbnail(url="https://i.imgur.com/OUSzh8W.jpg")
        responses["embeds"].append(raceEmbed)

        # Start new embed for any subraces
        if matchedObj["subraces"] != []:

            for subrace in matchedObj["subraces"]:

                subraceEmbed = discord.Embed(
                    colour=discord.Colour.green(),
                    title=f"{subrace['name']} (Subrace of **{matchedObj['name']})",
                    description=subrace["desc"],
                    url=raceLink
                )

                # Subrace Benefits
                subraceEmbed.add_field(name="SUBRACE BENEFITS", value=subrace["asi_desc"], inline=False)

                # Subrace traits
                if subrace["traits"] != "":

                    if len(subrace["traits"]) >= 1024:
                        subraceEmbed.add_field(name="TRAITS", value=subrace["traits"][:1023], inline=False)
                        subraceEmbed.add_field(name="TRAITS continued...", value=subrace["traits"][1024:], inline=False)
                    else:
                        subraceEmbed.add_field(name="TRAITS", value=subrace["traits"], inline=False)

                subraceEmbed.set_thumbnail(url="https://i.imgur.com/OUSzh8W.jpg")
                responses["embeds"].append(subraceEmbed)

    # Class
    elif "class" in route:

        # 1st Embed & File (BASIC)
        classLink = f"https://open5e.com/classes/{matchedObj['slug']}"
        classDescEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (CLASS): Basics",
            description=matchedObj["desc"][:2047],
            url=classLink
        )

        # Spell casting
        if matchedObj["spellcasting_ability"] != "":
            classDescEmbed.add_field(name="CASTING ABILITY", value=matchedObj["spellcasting_ability"], inline=False)

        clsDesFileName = generateFileName("clsdescription")
        clsTblFileName = generateFileName("clstable")

        classDescEmbed.add_field(
            name="LENGTH OF DESCRIPTION & TABLE TOO LONG FOR DISCORD",
            value=f"See `{clsDesFileName}` for full description\nSee `{clsTblFileName}` for class table",
            inline=False
        )

        responses["embeds"].append(classDescEmbed)

        # Full description as a file
        LOGGER.info(f"Creating file: {clsDesFileName}")
        with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{clsDesFileName}", "w+") as descFile:
            descFile.write(matchedObj["desc"])
        responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + clsDesFileName}"))

        # Class table as a file
        LOGGER.info(f"Creating file: {clsTblFileName}")
        with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{clsTblFileName}", "w+") as tableFile:
            tableFile.write(matchedObj["table"])
        responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + clsTblFileName}"))

        # 2nd Embed (DETAILS)
        classDetailsEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (CLASS): Profs & Details",
            description=f"**ARMOUR**: {matchedObj['prof_armor']}\n**WEAPONS**: {matchedObj['prof_weapons']}\n**TOOLS**: {matchedObj['prof_tools']}\n**SAVE THROWS**: {matchedObj['prof_saving_throws']}\n**SKILLS**: {matchedObj['prof_skills']}",
            url=classLink
        )

        classDetailsEmbed.add_field(
            name="Hit points",
            value=f"**Hit Dice**: {matchedObj['hit_dice']}\n**HP at first level**: {matchedObj['hp_at_1st_level']}\n**HP at other levels**: {matchedObj['hp_at_higher_levels']}",
            inline=False
        )

        # Equipment
        if len(matchedObj["equipment"]) >= 1024:
            classDetailsEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"][:1023], inline=False)
            classDetailsEmbed.add_field(name="EQUIPMENT continued", value=matchedObj["equipment"][1024:], inline=False)
        else:
            classDetailsEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)

        responses["embeds"].append(classDetailsEmbed)

        # 3rd Embed (ARCHETYPES)
        if matchedObj["archetypes"] != []:

            for archtype in matchedObj["archetypes"]:

                archTypeEmbed = None

                if len(archtype["desc"]) <= 2047:

                    archTypeEmbed = discord.Embed(
                        colour=discord.Colour.green(),
                        title=f"{archtype['name']} (ARCHETYPES)",
                        description=archtype["desc"],
                        url=classLink
                    )

                    responses["embeds"].append(archTypeEmbed)

                else:

                    archTypeEmbed = discord.Embed(
                        colour=discord.Colour.green(),
                        title=f"{archtype['name']} (ARCHETYPES)\n{matchedObj['subtypes_name'] if matchedObj['subtypes_name'] != '' else 'None'} (SUBTYPE)",
                        description=archtype["desc"][:2047],
                        url=classLink
                    )

                    clsArchFileName = generateFileName("clsarchetype")

                    archTypeEmbed.add_field(
                        name="LENGTH OF DESCRIPTION TOO LONG FOR DISCORD",
                        value=f"See `{clsArchFileName}` for full description",
                        inline=False
                    )

                    responses["embeds"].append(archTypeEmbed)

                    LOGGER.info(f"Creating file: {clsArchFileName}")
                    with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{clsArchFileName}", "w+") as archDesFile:
                        archDesFile.write(archtype["desc"])
                    responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + clsArchFileName}"))

        # Finish up
        for response in responses["embeds"]:
            response.set_thumbnail(url="https://i.imgur.com/Mjh6AAi.jpg")

    # Magic Item
    elif "magicitem" in route:
        itemLink = f"https://open5e.com/magicitems/{matchedObj['slug']}"
        if len(matchedObj["desc"]) >= 2048:
            magicItemEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (MAGIC ITEM)",
                description=matchedObj["desc"][:2047],
                url=itemLink
            )

            mIfileName = generateFileName("magicitem")

            magicItemEmbed.add_field(
                name="LENGTH OF DESCRIPTION TOO LONG FOR DISCORD",
                value=f"See `{mIfileName}` for full description",
                inline=False
            )

            responses["embeds"].append(magicItemEmbed)

            LOGGER.info(f"Creating file: {mIfileName}")
            with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{mIfileName}", "w+") as itemFile:
                itemFile.write(matchedObj["desc"])
            responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + mIfileName}"))

        else:
            magicItemEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{matchedObj['name']} (MAGIC ITEM)",
                description=matchedObj["desc"],
                url=itemLink
            )
            responses["embeds"].append(magicItemEmbed)

        for response in responses["embeds"]:
            response.add_field(name="TYPE", value=matchedObj["type"], inline=True)
            response.add_field(name="RARITY", value=matchedObj["rarity"], inline=True)

            if matchedObj["requires_attunement"] == "requires_attunement":
                response.add_field(name="ATTUNEMENT REQUIRED?", value="YES", inline=True)
            else:
                response.add_field(name="ATTUNEMENT REQUIRED?", value="NO", inline=True)

            response.set_thumbnail(url="https://i.imgur.com/2wzBEjB.png")

            # Remove this break if magicitems produces more than 1 embed in the future
            break

    # Weapon
    elif "weapon" in route:
        weaponEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{matchedObj['name']} (WEAPON)",
            description=f"**PROPERTIES**: {' | '.join(matchedObj['properties']) if matchedObj['properties'] != [] else 'None'}",
            url="https://open5e.com/sections/weapons"
        )
        weaponEmbed.add_field(
            name="DAMAGE",
            value=f"{matchedObj['damage_dice']} ({matchedObj['damage_type']})",
            inline=True
        )

        weaponEmbed.add_field(name="WEIGHT", value=matchedObj["weight"], inline=True)
        weaponEmbed.add_field(name="COST", value=matchedObj["cost"], inline=True)
        weaponEmbed.add_field(name="CATEGORY", value=matchedObj["category"], inline=False)

        weaponEmbed.set_thumbnail(url="https://i.imgur.com/pXEe4L9.png")

        responses["embeds"].append(weaponEmbed)

    else:
        badObjectFilename = generateFileName("badobject")

        LOGGER.info(f"Creating file: {badObjectFilename}")
        with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{badObjectFilename}", "w+") as itemFile:
            itemFile.write(matchedObj)

        noRouteEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="The matched item's type (i.e. spell, monster, etc) was not recognized",
            description=f"Please create an issue describing this failure and with the following values at https://github.com/M-Davies/oghma/issues\n**Input**: {entityInput}\n**Route**: {route}\n**Troublesome Object**: SEE `{badObjectFilename}`"
        )
        noRouteEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        responses["embeds"].append(noRouteEmbed)
        responses["files"].append(discord.File(f"{CURRENT_DIR}data{FILE_DELIMITER + badObjectFilename}"))

    return responses

###
# FUNC NAME: generateFileName
# FUNC DESC: Generates a filename using type of file and random number
# FUNC TYPE: Function
###
def generateFileName(fileType: str):
    return f"{fileType}-{str(random.randrange(1,1000000))}.md"

###
# FUNC NAME: codeError
# FUNC DESC: Sends an embed informing the user that there has been an API request failure
# FUNC TYPE: Error
###
def codeError(statusCode: int, query: str):
    codeEmbed = discord.Embed(
        colour=discord.Colour.red(),
        title=f"ERROR - API Request FAILED. Status Code: **{str(statusCode)}**",
        description=f"Query: {query}"
    )

    codeEmbed.add_field(
        name="For more idea on what went wrong:",
        value="See status codes at https://www.django-rest-framework.org/api-guide/status-codes/",
        inline=False
    )

    codeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    LOGGER.error(f"Sending Open5e Root API Request FAILED embed = {codeEmbed.to_dict()}")
    return codeEmbed

###
# FUNC NAME: argLengthError
# FUNC DESC: Sends an embed informing the user that their request is too long
# FUNC TYPE: Error
###
def argLengthError():
    argLengthErrorEmbed = discord.Embed(
        color=discord.Colour.red(),
        title="Invalid argument length",
        description="This command does not support more than 200 words in a single message. Try splitting up your query."
    )
    argLengthErrorEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    return argLengthErrorEmbed

###
# FUNC NAME: getOpen5eRoot
# FUNC DESC: Retrieves the open5e root dir, which contains the directory urls and names
# FUNC TYPE: Function
###
def getOpen5eRoot():
    # Get API Root
    rootRequest = requests.get("https://api.open5e.com?format=json")

    if rootRequest.status_code == 200:
        # Remove search directory from list (not used)
        allDirectories = list(rootRequest.json().keys())
        allDirectories.remove("search")
        return allDirectories
    else:
        # Throw if Root request wasn't successful
        LOGGER.error(f"API Request to Open5e root directory FAILED. Code: {rootRequest.status_code}")
        return rootRequest.status_code

###
# FUNC NAME: /help
# FUNC DESC: Displays a help message that shows the bot is live
# FUNC TYPE: Command
###
@CLIENT.tree.command(description="Displays a help message that shows usage information")
async def help(interaction: discord.Interaction):
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
    return await interaction.response.send_message(embed=helpEmbed)

###
# FUNC NAME: /roll
# FUNC DESC: Runs a dice roller
# FUNC TYPE: Command
###
@CLIENT.tree.command(description="Runs a quick & easy dice roller")
@app_commands.describe(calculation = "The calculation to conduct")
async def roll(interaction: discord.Interaction, calculation: str):

    LOGGER.info(f"Executing: /roll {calculation}")

    # Return invalid args embed (to be called later)
    def invalidArgSupplied(culprit):
        invalidArgsEmbed = discord.Embed(
            color=discord.Colour.red(),
            title=f"Invalid argument (`{culprit}`) supplied to /roll",
            description="This is likely due to the value being too low or high.\n\n**USAGE**\n`/roll [ROLLS]d[SIDES]`\n*Example:* `/roll 3d20 + 3`"
        )
        invalidArgsEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        LOGGER.info(f"Invalid argument supplied to /roll = {culprit}")
        return invalidArgsEmbed

    # Return invalid size of args supplied embed (to be called later)
    def invalidSizeSupplied(culprit):
        invalidSizeEmbed = discord.Embed(
            color=discord.Colour.red(),
            title=f"Invalid size of argument (`{culprit}`) supplied to /roll",
            description=f"ROLLS and SIDES and STATIC NUMBERS supplied to `/roll` must be numbers of a reasonable value (CURRENT LIMIT = {ROLL_MAX_PARAM_VALUE}).\n\n**USAGE**\n`?roll [ROLLS]d[SIDES]`\n*Example:* `?roll 3d20 + 3`"
        )
        invalidSizeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        LOGGER.info(f"Invalid size of argument supplied to /roll = {culprit}")
        return invalidSizeEmbed

    # Return invalid numeric operator embed (to be called later)
    def unrecognisedNumericOperator(numericOperator):
        invalidOperatorEmbed = discord.Embed(
            color=discord.Colour.red(),
            title=f"`{numericOperator}` IS NOT SUPPORTED",
            description=f"**SUPPORTED OPERATORS:**\n{NUMERIC_OPERATORS}"
        )
        invalidOperatorEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        LOGGER.info(f"Unrecognised numeric operator supplied to /roll = {numericOperator}")
        return invalidOperatorEmbed

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
        if argument in NUMERIC_OPERATORS:
            if calculationList.index(argument) != 0:
                if len(argument) == 1:
                    currentOperator = argument
                else:
                    return await interaction.response.send_message(embed=unrecognisedNumericOperator(argument))
            else:
                operatorAtFront = discord.Embed(
                    color=discord.Colour.red(),
                    title=f"THE `{argument}` OPERATOR CANNOT BE THE FIRST CHARACTER"
                )
                operatorAtFront.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

                return await interaction.response.send_message(embed=operatorAtFront)

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
                if numCheck <= ROLL_MAX_PARAM_VALUE:
                    # Add to dict in same manner as a dice roll total
                    diceRollResults[argument]["sectionTotal"] = numCheck
                else:
                    return await interaction.response.send_message(embed=invalidSizeSupplied(numCheck))

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

                            if numberOfRolls >= ROLL_MAX_PARAM_VALUE:
                                return await interaction.response.send_message(embed=invalidSizeSupplied(numberOfRolls))

                        except ValueError:
                            return await interaction.response.send_message(embed=invalidArgSupplied(regexReturn.group("rolls")))

                    # Checks the amount of sides supplied is a number and is valid
                    try:
                        numberOfSides = int(regexReturn.group("sides"))

                        if numberOfSides < 2 or numberOfSides >= ROLL_MAX_PARAM_VALUE:
                            return await interaction.response.send_message(embed=invalidSizeSupplied(numberOfSides))

                    except ValueError:
                        return await interaction.response.send_message(embed=invalidArgSupplied(regexReturn.group("sides")))

                else:
                    return await interaction.response.send_message(embed=invalidArgSupplied("NO DICE SIDES DETECTED! TRY CHECKING YOUR SYNTAX AND /roll USAGE"))

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
                    return await interaction.response.send_message(embed=unrecognisedNumericOperator(currentOperator))

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
    return await interaction.response.send_message(embed=diceRollEmbed)

###
# FUNC NAME: /search [ENTITY]
# FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
# FUNC TYPE: Command
###
@CLIENT.tree.command(description="Queries the Open5e API to get the requested entity")
@app_commands.rename(entityInput = "entity")
@app_commands.describe(entityInput = "The entity you would like to search for")
async def search(interaction: discord.Interaction, entityInput: Optional[str] = ""):

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
        with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{entityFileName}", "w+") as entityFile:
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
        return await interaction.followup.send(embed=detailsEmbed, file=discord.File(f"{CURRENT_DIR}data/{entityFileName}"))

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

###
# FUNC NAME: /searchdir [DIRECTORY] [ENTITY]
# FUNC DESC: Queries the Open5e DIRECTORY API.
# FUNC TYPE: Command
###
@CLIENT.tree.command(description="Queries the Open5e API to get an entity's information from a specified directory.")
@app_commands.rename(directoryInput = "directory", entityInput = "entity")
@app_commands.describe(directoryInput = "The category to search for the entity in", entityInput = "The entity you would like to search for")
async def searchdir(interaction: discord.Interaction, directoryInput: str, entityInput: Optional[str] = ""):
    
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
        with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{entityDirFileName}", "w+") as entityFile:
            entityFile.write("\n".join(entityNames))

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"See `{entityDirFileName}` for all searchable entities in this directory",
            description="Due to discord character limits regarding embeds, the results have to be sent in a file"
        )
        detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        return await interaction.followup.send(embed=detailsEmbed, file=discord.File(f"{CURRENT_DIR}data/{entityDirFileName}"))

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

###
# FUNC NAME: /lst [DIRECTORY] [ENTITY]
# FUNC DESC: Queries the Open5e API to get all the fully and partially matching entities information in a list embed format.
# FUNC TYPE: Command
###
@CLIENT.tree.command(description="Queries the Open5e API to get all the fully and partially matching entities based on the search term")
@app_commands.rename(entityInput = "entity", directoryInput = "directory")
@app_commands.describe(entityInput = "The entity you would like to search for", directoryInput = "The category to search for the entity in")
async def lst(interaction: discord.Interaction, entityInput: str, directoryInput: Optional[str] = ""):

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
            with open(f"{CURRENT_DIR}data{FILE_DELIMITER}{matchesFileName}", "w+") as matchesFile:
                matchesFile.write(formattedMatches)

            matchesEmbed.add_field(name=f"See `{matchesFileName}` for the matched entities", value="Due to discord character limits regarding embeds, the results have to be sent in a file", inline=False)
            return await interaction.followup.send(embed=matchesEmbed, file=discord.File(f"{CURRENT_DIR}data/{matchesFileName}"))

CLIENT.run(os.environ['BOT_KEY'])
