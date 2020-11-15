###
# Project: oghma
# Author: shadowedlucario
# https://github.com/shadowedlucario
###

import os
import requests
import json
import random
import time
import discord
import logging
import re
from discord.ext import commands

# Import dotenv (it's troublesome to install on mac for some reason)
from dotenv import load_dotenv
load_dotenv()

### GLOBALS ###
partial_match = False

### CONSTANTS ###
BOTNAME = "Oghma"
BOT = commands.Bot(command_prefix='?')
BOT.remove_command('help') # Remove this as we make our own
CLIENT = discord.Client()

SEARCH_PARAM_ENDPOINTS = ["spells", "monsters", "magicitems", "weapons"]
NUMERIC_OPERATORS = ["+", "-", "*", "/"]
COMMAND_LIST = ["ping", "roll", "search", "searchdir"]

ROLL_MAX_PARAM_VALUE = 10001
COMMAND_DELAY_SLEEP_VALUE = 1

# Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(name)s: %(message)s'))
logger.addHandler(handler)

###
# FUNC NAME: searchResponse
# FUNC DESC: Searches the API response for the user input. Returns None if nothing was found
# FUNC TYPE: Function
###
def searchResponse(responseResults, filteredInput):

    # Sets entity name/title to lowercase and removes spaces
    def parse(entityHeader): return entityHeader.replace(" ", "").lower()

    global partial_match
    match = None

    # First, look for an exact match after parsing
    for entity in responseResults:

        # Documents don't have a name attribute
        if "title" in entity:

            # Has to be in it's own "if" to avoid KeyErrors
            if parse(entity["title"]) == filteredInput:
                match = entity
                break

        elif "name" in entity:

            if parse(entity["name"]) == filteredInput:
                match = entity
                break

        else: match = "UNKNOWN"

    # Now try partially matching the entity (i.e. bluedragon will match adultbluedragon here)
    if match == None or match == "UNKNOWN":

        for entity in responseResults:

            if "title" in entity:

                if filteredInput in parse(entity["title"]):
                    partial_match = True

                    match = entity
                    break

            elif "name" in entity:

                if filteredInput in parse(entity["name"]):
                    partial_match = True

                    match = entity
                    break

            else: match = "UNKNOWN"

    return match

###
# FUNC NAME: requestScryfall
# FUNC DESC: Queries the Scryfall API to obtain a thumbnail image.
# FUNC TYPE: Function
###
def requestScryfall(searchTerm, searchdir):

    scryfallRequest = requests.get(f"https://api.scryfall.com/cards/search?q={ ' '.join(searchTerm) }&include_extras=true&include_multilingual=true&include_variations=true")

    # Try again with the first arg if nothing was found
    if scryfallRequest.status_code == 404:

        searchWord = searchTerm[0]
        if searchdir: searchWord = searchTerm[1]

        scryfallWordRequest = requests.get(f"https://api.scryfall.com/cards/search?q={ searchWord }&include_extras=true&include_multilingual=true&include_variations=true")

        if scryfallWordRequest.status_code != 200: return scryfallWordRequest.status_code
        else: return scryfallWordRequest.json()["data"][0]["image_uris"]["art_crop"]

    # Return code if API request failed
    elif scryfallRequest.status_code != 200: return scryfallRequest.status_code

    # Otherwise, return the cropped image url
    else: return scryfallRequest.json()["data"][0]["image_uris"]["art_crop"]

###
# FUNC NAME: requestOpen5e
# FUNC DESC: Queries the Open5e API.
# FUNC TYPE: Function
###
def requestOpen5e(query, filteredInput, wideSearch):

    # API Request
    request = requests.get(query)

    # Return code if not successfull
    if request.status_code != 200: return {"code": request.status_code, "query": query}

    # Iterate through the results
    output = searchResponse(request.json()["results"], filteredInput)

    if output == None: return output

    elif output == "UNKNOWN": return output

    # Find resource object if coming from search endpoint
    elif wideSearch:

        # Request resource using the first word of the name to filter results
        route = output["route"]

        # Determine filter type (search can only be used for some endpoints)
        filterType = "text"
        if route in SEARCH_PARAM_ENDPOINTS: filterType = "search"

        if "title" in output:
            resourceRequest = requests.get(
                f"https://api.open5e.com/{ route }?format=json&limit=10000&{ filterType }={ output['title'].split()[0] }"
            )
        else:
            resourceRequest = requests.get(
                f"https://api.open5e.com/{ route }?format=json&limit=10000&{ filterType }={ output['name'].split()[0] }"
            )

        # Return code if not successfull
        if resourceRequest.status_code != 200:
            return {
                "code": resourceRequest.status_code,
                "query": f"https://api.open5e.com/{ route }?format=json&limit=10000&search={ output['name'].split()[0] }"
            }

        # Search response again for the actual object
        resourceOutput = searchResponse(resourceRequest.json()["results"], filteredInput)

        if resourceOutput == "UNKNOWN": return resourceOutput

        return {"route": route, "matchedObj": resourceOutput}

    # If already got the resource object, just return it
    else: return output

###
# FUNC NAME: constructResponse
# FUNC DESC: Constructs embed responses from the API object.
# FUNC TYPE: Function
###
def constructResponse(args, route, matchedObj):
    responses = []

    # Document
    if "document" in route:
        # Get document link
        docLink = matchedObj['url']
        if "http" not in docLink: docLink = f"http://{ matchedObj['url'] }"

        if len(matchedObj["desc"]) >= 2048:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['title'] } (DOCUMENT)",
                description=matchedObj["desc"][:2047],
                url=docLink
            )
            documentEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:])
        else:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['title'] } (DOCUMENT)",
                description=matchedObj["desc"],
                url=docLink
            )
        documentEmbed.add_field(name="Authors", value=matchedObj["author"], inline=False)
        documentEmbed.add_field(name="Link", value=matchedObj["url"], inline=True)
        documentEmbed.add_field(name="Version Number", value=matchedObj["version"], inline=True)
        documentEmbed.add_field(name="Copyright", value=matchedObj["copyright"], inline=False)

        documentEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")

        responses.append(documentEmbed)

    # Spell
    elif "spell" in route:

        spellLink = f"https://open5e.com/spells/{matchedObj['slug']}/"
        if len(matchedObj["desc"]) >= 2048:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (SPELL)",
                description=matchedObj["desc"][:2047],
                url=spellLink
            )
            spellEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:], inline=False)
        else:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["name"],
                description=f"{ matchedObj['desc'] } (SPELL)",
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
        if "M" in matchedObj["components"]: spellEmbed.add_field(name="Material", value=matchedObj["material"], inline=True)
        spellEmbed.add_field(name="Page Number", value=matchedObj["page"], inline=True)

        spellEmbed.set_thumbnail(url="https://i.imgur.com/W15EmNT.jpg")

        responses.append(spellEmbed)

    # Monster
    elif "monster" in route:
        ## 1ST EMBED ##
        monsterLink = f"https://open5e.com/monsters/{ matchedObj['slug'] }/"
        monsterEmbedBasics = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (MONSTER) - STATS",
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
        if matchedObj["strength_save"] != None:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value=f"{ matchedObj['strength'] } (SAVE: **{ matchedObj['strength_save'] }**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value=f"{ matchedObj['strength'] }",
                inline=True
            )

        # Dex
        if matchedObj["dexterity_save"] != None:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value=f"{matchedObj['dexterity']} (SAVE: **{ matchedObj['dexterity_save'] }**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value=f"{ matchedObj['dexterity'] }",
                inline=True
            )

        # Con
        if matchedObj["constitution_save"] != None:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value=f"{ matchedObj['constitution'] } (SAVE: **{ matchedObj['constitution_save'] }**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value=f"{ matchedObj['constitution'] }",
                inline=True
            )

        # Int
        if matchedObj["intelligence_save"] != None:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value=f"{ matchedObj['intelligence'] } (SAVE: **{ matchedObj['intelligence_save'] }**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value=f"{ matchedObj['intelligence'] }",
                inline=True
            )

        # Wis
        if matchedObj["wisdom_save"] != None:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value=f"{ matchedObj['wisdom'] } (SAVE: **{ matchedObj['wisdom_save'] }**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value=f"{ matchedObj['wisdom'] }",
                inline=True
            )

        # Cha
        if matchedObj["charisma_save"] != None:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value=f"{ matchedObj['charisma'] } (SAVE: **{ matchedObj['charisma_save'] }**)",
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value=f"{ matchedObj['charisma'] }",
                inline=True
            )

        # Hit points/dice
        monsterEmbedBasics.add_field(
            name=f"HIT POINTS (**{ str(matchedObj['hit_points']) }**)",
            value=matchedObj["hit_dice"],
            inline=True
        )

        # Speeds
        monsterSpeeds = ""
        for speedType, speed in matchedObj["speed"].items():
            monsterSpeeds += f"**{ speedType }**: { speed }\n"
        monsterEmbedBasics.add_field(name="SPEED", value=monsterSpeeds, inline=True)

        # Armour
        monsterEmbedBasics.add_field(
            name="ARMOUR CLASS",
            value=f"{ str(matchedObj['armor_class']) } ({ matchedObj['armor_desc'] })",
            inline=True
        )

        responses.append(monsterEmbedBasics)

        ## 2ND EMBED ##
        monsterEmbedSkills = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (MONSTER) - SKILLS & PROFICIENCIES",
            url=monsterLink
        )

        # Skills & Perception
        if matchedObj["skills"] != {}:
            monsterSkills = ""
            for skillName, skillValue in matchedObj["skills"].items():
                monsterSkills += f"**{ skillName }**: { skillValue }\n"
            monsterEmbedSkills.add_field(name="SKILLS", value=monsterSkills, inline=True)

        # Senses
        monsterEmbedSkills.add_field(name="SENSES", value=matchedObj["senses"], inline=True)

        # Languages
        if matchedObj["languages"] != "": monsterEmbedSkills.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Damage conditionals
        monsterEmbedSkills.add_field(
            name="STRENGTHS & WEAKNESSES",
            value="**VULNERABLE TO:** {}\n**RESISTANT TO:** {}\n**IMMUNE TO:** {}".format(
                matchedObj["damage_vulnerabilities"] if matchedObj["damage_vulnerabilities"] != "" else "Nothing",
                matchedObj["damage_resistances"] if matchedObj["damage_resistances"] != "" else "Nothing",
                matchedObj["damage_immunities"] if matchedObj["damage_immunities"] != "" else "Nothing"
                    + ", "
                        + matchedObj["condition_immunities"] if matchedObj["condition_immunities"] != None else "Nothing",
            ),
            inline=False
        )

        responses.append(monsterEmbedSkills)

        ## 3RD EMBED ##
        monsterEmbedActions = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (MONSTER) - ACTIONS & ABILITIES",
            url=monsterLink
        )

        # Actions
        for action in matchedObj["actions"]:
            monsterEmbedActions.add_field(
                name=f"{ action['name'] } (ACTION)",
                value=action["desc"],
                inline=False
            )

        # Reactions
        if matchedObj["reactions"] != "":
            for reaction in matchedObj["reactions"]:
                monsterEmbedActions.add_field(
                    name=f"{ reaction['name'] } (REACTION)",
                    value=reaction["desc"],
                    inline=False
                )

        # Specials
        for special in matchedObj["special_abilities"]:
            if len(special["desc"]) >= 1024:
                monsterEmbedActions.add_field(
                    name=f"{ special['name'] } (SPECIAL)",
                    value=special["desc"][:1023],
                    inline=False
                )
                monsterEmbedActions.add_field(
                    name=f"{ special['name'] } (SPECIAL) Continued...",
                    value=special["desc"][1024:],
                    inline=False
                )
            else:
                monsterEmbedActions.add_field(
                    name=f"{ special['name'] } (SPECIAL)",
                    value=special["desc"],
                    inline=False
                )

        # Spells
        if matchedObj["spell_list"] != []:

            # Function to split the spell link down (e.g. https://api.open5e.com/spells/light/), [:-1] removes trailing whitespace
            def splitSpell(spellName): return spellName.replace("-", " ").split("/")[:-1]

            for spell in matchedObj["spell_list"]:
                spellSplit = splitSpell(spell)

                monsterEmbedActions.add_field(
                    name=spellSplit[-1],
                    value=f"To see spell info, `?searchdir spells { spellSplit[-1] }`",
                    inline=False
                )

        responses.append(monsterEmbedActions)

        ## 4TH EMBED (only used if it has legendary actions) ##
        if matchedObj["legendary_desc"] != "":
            monsterEmbedLegend = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (MONSTER): LEGENDARY ACTIONS & ABILITIES",
                description=matchedObj["legendary_desc"],
                url=monsterLink
            )

            for action in matchedObj["legendary_actions"]:
                monsterEmbedLegend.add_field(
                    name=action["name"],
                    value=action["desc"],
                    inline=False
                )

            responses.append(monsterEmbedLegend)

        # Author & Image for all embeds
        for embed in responses:
            if matchedObj["img_main"] != None: embed.set_thumbnail(url=matchedObj["img_main"])
            else: embed.set_thumbnail(url="https://i.imgur.com/6HsoQ7H.jpg")

    # Background
    elif "background" in route:

        # 1st Embed (Basics)
        bckLink = "https://open5e.com/sections/backgrounds"
        backgroundEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (BACKGROUND) - BASICS",
            description=matchedObj["desc"],
            url=bckLink
        )

        # Profs
        if matchedObj["tool_proficiencies"] != None:
            backgroundEmbed.add_field(
                name="PROFICIENCIES",
                value=f"**SKILLS**: { matchedObj['skill_proficiencies'] }\n**TOOLS**: { matchedObj['tool_proficiencies'] }",
                inline=True
            )
        else:
            backgroundEmbed.add_field(
                name="PROFICIENCIES",
                value=f"**SKILL**: { matchedObj['skill_proficiencies'] }",
                inline=True
            )

        # Languages
        if matchedObj["languages"] != None:
            backgroundEmbed.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Equipment
        backgroundEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)

        # Feature
        backgroundEmbed.add_field(name=matchedObj["feature"], value=matchedObj["feature_desc"], inline=False)

        responses.append(backgroundEmbed)

        # 2nd Embed (feature)
        backgroundFeatureEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (BACKGROUND)\nFEATURE ({ matchedObj['feature'] })",
            description=matchedObj["feature_desc"],
            url=bckLink
        )

        responses.append(backgroundFeatureEmbed)

        # 3rd Embed & File (suggested characteristics)
        if matchedObj["suggested_characteristics"] != None:

            if len(matchedObj["suggested_characteristics"]) <= 2047:

                backgroundChars = discord.Embed(
                    colour=discord.Colour.green(),
                    title=f"{ matchedObj['name'] } (BACKGROUND): CHARACTERISTICS",
                    description=matchedObj["suggested_characteristics"],
                    url=bckLink
                )

                responses.append(backgroundChars)

            else:
                backgroundChars = discord.Embed(
                    colour=discord.Colour.green(),
                    title=f"{ matchedObj['name'] } (BACKGROUND): CHARACTERISTICS",
                    description=matchedObj["suggested_characteristics"][:2047],
                    url=bckLink
                )

                bckFileName = generateFileName("background")

                backgroundChars.add_field(
                    name="LENGTH OF CHARACTERISTICS TOO LONG FOR DISCORD",
                    value=f"See `{ bckFileName }` for full description",
                    inline=False
                )

                responses.append(backgroundChars)

                # Create characteristics.txt
                characteristicsFile = open(bckFileName, "a+")
                characteristicsFile.write(matchedObj["suggested_characteristics"])
                characteristicsFile.close()

                responses.append(bckFileName)

        for response in responses:
            if isinstance(response, discord.Embed):
                response.set_thumbnail(url="https://i.imgur.com/GhGODan.jpg")

    # Plane
    elif "plane" in route:
        planeEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (PLANE)",
            description=matchedObj["desc"],
            url="https://open5e.com/sections/planes"
        )

        planeEmbed.set_thumbnail(url="https://i.imgur.com/GJk1HFh.jpg")

        responses.append(planeEmbed)

    # Section
    elif "section" in route:

        secLink = f"https://open5e.com/sections/{ matchedObj['slug'] }/"
        if len(matchedObj["desc"]) >= 2048:

            sectionEmbedDesc = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (SECTION) - { matchedObj['parent'] }",
                description=matchedObj["desc"][:2047],
                url=secLink
            )

            sectionFilename = generateFileName("section")
            sectionEmbedDesc.add_field(
                name="LENGTH OF DESCRIPTION TOO LONG FOR DISCORD",
                value=f"See `{ sectionFilename }` for full description",
                inline=False
            )
            sectionEmbedDesc.set_thumbnail(url="https://i.imgur.com/J75S6bF.jpg")
            responses.append(sectionEmbedDesc)

            # Full description as a file
            secDescFile = open(sectionFilename, "a+")
            secDescFile.write(matchedObj["desc"])
            secDescFile.close()
            responses.append(sectionFilename)

        else:
            sectionEmbedDesc = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (SECTION) - { matchedObj['parent'] }",
                description=matchedObj["desc"],
                url=secLink
            )
            sectionEmbedDesc.set_thumbnail(url="https://i.imgur.com/J75S6bF.jpg")
            responses.append(sectionEmbedDesc)

    # Feat
    elif "feat" in route:

        # Open5e website doesn't have a website entry for Urls yet
        featEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (FEAT)",
            description=f"PREREQUISITES: **{ matchedObj['prerequisite'] }**"
        )
        featEmbed.add_field(name="DESCRIPTION", value=matchedObj["desc"], inline=False)
        featEmbed.set_thumbnail(url="https://i.imgur.com/X1l7Aif.jpg")

        responses.append(featEmbed)

    # Condition
    elif "condition" in route:

        conLink = "https://open5e.com/gameplay-mechanics/conditions"
        if len(matchedObj["desc"]) >= 2048:
            conditionEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (CONDITION)",
                description=matchedObj["desc"][:2047],
                url=conLink
            )
            conditionEmbed.add_field(name="DESCRIPTION continued...", value=matchedObj["desc"][2048:], inline=False)

        else:
            conditionEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (CONDITION)",
                description=matchedObj["desc"],
                url=conLink
            )
        conditionEmbed.set_thumbnail(url="https://i.imgur.com/tOdL5n3.jpg")

        responses.append(conditionEmbed)

    # Race
    elif "race" in route:
        raceLink = f"https://open5e.com/races/{ matchedObj['slug'] }"
        raceEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (RACE)",
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
        responses.append(raceEmbed)

        # Start new embed for any subraces
        if matchedObj["subraces"] != []:

            for subrace in matchedObj["subraces"]:

                subraceEmbed = discord.Embed(
                    colour=discord.Colour.green(),
                    title=f"{ subrace['name'] } (Subrace of **{ matchedObj['name'] })",
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
                responses.append(subraceEmbed)

    # Class
    elif "class" in route:

        # 1st Embed & File (BASIC)
        classLink = f"https://open5e.com/classes/{ matchedObj['slug'] }"
        classDescEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (CLASS): Basics",
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
            value=f"See `{ clsDesFileName }` for full description\nSee `{ clsTblFileName }` for class table",
            inline=False
        )

        responses.append(classDescEmbed)

        # Full description as a file
        descFile = open(clsDesFileName, "a+")
        descFile.write(matchedObj["desc"])
        descFile.close()
        responses.append(clsDesFileName)

        # Class table as a file
        tableFile = open(clsTblFileName, "a+")
        tableFile.write(matchedObj["table"])
        tableFile.close()
        responses.append(clsTblFileName)

        # 2nd Embed (DETAILS)
        classDetailsEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=f"{ matchedObj['name'] } (CLASS): Profs & Details",
            description=f"**ARMOUR**: { matchedObj['prof_armor'] }\n**WEAPONS**: { matchedObj['prof_weapons'] }\n**TOOLS**: { matchedObj['prof_tools'] }\n**SAVE THROWS**: { matchedObj['prof_saving_throws'] }\n**SKILLS**: { matchedObj['prof_skills'] }",
            url=classLink
        )

        classDetailsEmbed.add_field(
            name="Hit points",
            value=f"**Hit Dice**: { matchedObj['hit_dice'] }\n**HP at first level**: { matchedObj['hp_at_1st_level'] }\n**HP at other levels**: { matchedObj['hp_at_higher_levels'] }",
            inline=False
        )

        # Equipment
        if len(matchedObj["equipment"]) >= 1024:
            classDetailsEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"][:1023], inline=False)
            classDetailsEmbed.add_field(name="EQUIPMENT continued", value=matchedObj["equipment"][1024:], inline=False)
        else:
            classDetailsEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)

        responses.append(classDetailsEmbed)

        # 3rd Embed (ARCHETYPES)
        if matchedObj["archetypes"] != []:

            for archtype in matchedObj["archetypes"]:

                archTypeEmbed = None

                if len(archtype["desc"]) <= 2047:

                    archTypeEmbed = discord.Embed(
                        colour=discord.Colour.green(),
                        title=f"{ archtype['name'] } (ARCHETYPES)",
                        description=archtype["desc"],
                        url=classLink
                    )

                    responses.append(archTypeEmbed)

                else:

                    archTypeEmbed = discord.Embed(
                        colour=discord.Colour.green(),
                        title=f"{ archtype['name'] } (ARCHETYPES)\n{ matchedObj['subtypes_name'] if matchedObj['subtypes_name'] != '' else 'None' } (SUBTYPE)",
                        description=archtype["desc"][:2047],
                        url=classLink
                    )

                    clsArchFileName = generateFileName("clsarchetype")

                    archTypeEmbed.add_field(
                        name="LENGTH OF DESCRIPTION TOO LONG FOR DISCORD",
                        value=f"See `{ clsArchFileName }` for full description",
                        inline=False
                    )

                    responses.append(archTypeEmbed)

                    archDesFile = open(clsArchFileName, "a+")
                    archDesFile.write(archtype["desc"])
                    archDesFile.close()

                    responses.append(clsArchFileName)

        # Finish up
        for response in responses:
            if isinstance(response, discord.Embed):
                response.set_thumbnail(url="https://i.imgur.com/Mjh6AAi.jpg")

    # Magic Item
    elif "magicitem" in route:
        itemLink = f"https://open5e.com/magicitems/{ matchedObj['slug'] }"
        if len(matchedObj["desc"]) >= 2048:
            magicItemEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (MAGIC ITEM)",
                description=matchedObj["desc"][:2047],
                url=itemLink
            )

            mIfileName = generateFileName("magicitem")

            magicItemEmbed.add_field(
                name="LENGTH OF DESCRIPTION TOO LONG FOR DISCORD",
                value=f"See `{ mIfileName }` for full description",
                inline=False
            )

            responses.append(magicItemEmbed)

            itemFile = open(mIfileName, "a+")
            itemFile.write(matchedObj["desc"])
            itemFile.close()

            responses.append(mIfileName)

        else:
            magicItemEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=f"{ matchedObj['name'] } (MAGIC ITEM)",
                description=matchedObj["desc"],
                url=itemLink
            )
            responses.append(magicItemEmbed)

        for response in responses:
            if isinstance(response, discord.Embed):
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
            title=f"{ matchedObj['name'] } (WEAPON)",
            description=f"**PROPERTIES**: { ' | '.join(matchedObj['properties']) if matchedObj['properties'] != [] else 'None' }",
            url="https://open5e.com/sections/weapons"
        )
        weaponEmbed.add_field(
            name="DAMAGE",
            value=f"{ matchedObj['damage_dice'] } ({ matchedObj['damage_type'] })",
            inline=True
        )

        weaponEmbed.add_field(name="WEIGHT", value=matchedObj["weight"], inline=True)
        weaponEmbed.add_field(name="COST", value=matchedObj["cost"], inline=True)
        weaponEmbed.add_field(name="CATEGORY", value=matchedObj["category"], inline=False)

        weaponEmbed.set_thumbnail(url="https://i.imgur.com/pXEe4L9.png")

        responses.append(weaponEmbed)

    else:
        global partial_match
        partial_match = False

        badObjectFilename = generateFileName("badobject")

        itemFile = open(badObjectFilename, "a+")
        itemFile.write(matchedObj)
        itemFile.close()

        noRouteEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="The matched item's type (i.e. spell, monster, etc) was not recognized",
            description=f"Please create an issue describing this failure and with the following values at https://github.com/shadowedlucario/oghma/issues\n**Input**: { args }\n**Route**: { route }\n**Troublesome Object**: SEE `{ badObjectFilename }`"
        )
        noRouteEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        responses.append(noRouteEmbed)
        responses.append(badObjectFilename)

    return responses

###
# FUNC NAME: generateFileName
# FUNC DESC: Generates a filename using type of file and random number
# FUNC TYPE: Function
###
def generateFileName(fileType): return f"{ fileType }-{ str(random.randrange(1,1000000)) }.txt"

###
# FUNC NAME: codeError
# FUNC DESC: Sends an embed informing the user that there has been an API request failure
# FUNC TYPE: Error
###
def codeError(statusCode, query):
    codeEmbed = discord.Embed(
        colour=discord.Colour.red(),
        title=f"ERROR - API Request FAILED. Status Code: **{ str(statusCode) }**",
        description=f"Query: { query }"
    )

    codeEmbed.add_field(
        name="For more idea on what went wrong:",
        value="See status codes at https://www.django-rest-framework.org/api-guide/status-codes/",
        inline=False
    )

    codeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

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
# FUNC NAME: on_command_error
# FUNC DESC: Sends useful output on an error occurance to the user
# FUNC TYPE: Event
###
@BOT.event
async def on_command_error(ctx, error):

    # Throw if discord failed to execute a command
    if isinstance(error, commands.CommandInvokeError) or isinstance(error, commands.BotMissingPermissions):
        invokeEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="COMMAND FAILED TO EXECUTE",
            description=f"Do I have the right permissions (Send messages, Embeds and Files as well as Read Message History)?\n\n__STACKTRACE__\n{error}"
        )

        invokeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        print("SENDING CommandInvokeError / BotMissingPermissions EMBED...")
        return await ctx.send(embed=invokeEmbed)

    # Throw if the user tries to execute a command that doesn't exist
    elif isinstance(error, commands.CommandNotFound):
        notFoundEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="COMMAND DOES NOT EXIST",
            description=f"Available commands are {COMMAND_LIST}"
        )
        notFoundEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        print("SENDING CommandNotFound EMBED...")
        return await ctx.send(embed=notFoundEmbed)

    # Another unexpected error occurred
    else:
        unexpectedEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="UNEXPECTED EXCEPTION OCCURRED",
            description=error
        )
        unexpectedEmbed.add_field(name="NOTE", value="Please report this to https://github.com/shadowedlucario/oghma/issues stating how you encountered this bug and with the following infomation...", inline=False)

        unexpectedEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        print("SENDING unexpectedEmbed EMBED...")
        return await ctx.send(embed=unexpectedEmbed)

###
# FUNC NAME: on_ready
# FUNC DESC: Tells you when bot is ready to accept commands. Also cleans up temp files.
# FUNC TYPE: Event
###
@BOT.event
async def on_ready():
    print(f"Logged in as\n{ BOT.user.name }\n{ BOT.user.id }\n------")

    # All done!
    print("READY!")

###
# FUNC NAME: ?help
# FUNC DESC: Displays a help message that shows the bot is live
# FUNC TYPE: Command
###
@BOT.command(
    name='help',
    help='Displays a help message that shows the bot is live.\nUsage: !ping',
    usage='?help',
    aliases=["h", "H", "ping", "p"]
)
async def help(ctx, *args):

    helpEmbed=discord.Embed(
        title="Oghma",
        url="https://top.gg/bot/658336624647733258",
        description="__Available commands__\n\n**?help** - Displays this message (duh)\n\n**?roll [ROLLS]d[SIDES]** - Dice roller with calculator logic\n\n**?search [ENTITY]** - Searches the whole Open5e D&D database for your chosen entity.\n\n**?searchdir [RESOURCE] [ENTITY]** - Searches a specific category of the Open5e D&D database for your chosen entity a lot faster than *?search*.",
        color=discord.Colour.purple()
    )

    helpEmbed.set_author(
        name="Intoxication#6666",
        url="https://github.com/shadowedlucario",
        icon_url="https://github.com/shadowedlucario.png"
    )

    helpEmbed.set_thumbnail(url="https://i.imgur.com/HxuMICy.jpg")

    # Add 1 to latency as we sleep for 1 sec before every command
    helpEmbed.add_field(name="CURRENT LATENCY", value=f"{ 1 + round(BOT.latency, 1) } seconds", inline=False)

    helpEmbed.add_field(name="LINKS", value="------------------", inline=False)
    helpEmbed.add_field(name="GitHub", value="https://github.com/shadowedlucario/oghma", inline=True)
    helpEmbed.add_field(name="Discord", value="https://discord.gg/8YZ2NZ5", inline=True)
    helpEmbed.set_footer(text="Feedback? Hate? Make it known to us! (see links above)")

    return await ctx.send(embed=helpEmbed)

###
# FUNC NAME: ?roll
# FUNC DESC: Runs a dice roller
# FUNC TYPE: Command
###
@BOT.command(
    name='roll',
    help='Runs a dice roller',
    usage='?roll [ROLLS]d[SIDES]',
    aliases=["throw", "dice", "r", "R"]
)
async def roll(ctx, *args):

    # Sleep to wait for other stuff to complete first
    time.sleep(COMMAND_DELAY_SLEEP_VALUE)

    print(f"Executing: ?roll { args }")

    # Return invalid args embed (to be called later)
    def invalidArgSupplied(culprit):
        invalidArgsEmbed = discord.Embed(
            color=discord.Colour.red(),
            title=f"Invalid argument (`{ culprit }`) supplied to ?roll",
            description="This is likely due to the value being too low or high.\n\n**USAGE**\n`?roll [ROLLS]d[SIDES]`\n*Example:* `?roll 3d20 + 3`"
        )
        invalidArgsEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        return invalidArgsEmbed

    # Return invalid size of args supplied embed (to be called later)
    def invalidSizeSupplied(culprit):
        invalidSizeEmbed = discord.Embed(
            color=discord.Colour.red(),
            title=f"Invalid size of argument (`{ culprit }`) supplied to ?roll",
            description=f"ROLLS and SIDES and STATIC NUMBERS supplied to `?roll` must be numbers of a reasonable value (CURRENT LIMIT = { ROLL_MAX_PARAM_VALUE }).\n\n**USAGE**\n`?roll [ROLLS]d[SIDES]`\n*Example:* `?roll 3d20 + 3`"
        )
        invalidSizeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        return invalidSizeEmbed

    # Return invalid numberic operator embed (to be called later)
    def unrecognisedNumericOperator(numericOperator):
        invalidOperatorEmbed = discord.Embed(
            color=discord.Colour.red(),
            title=f"`{ numericOperator }` IS NOT SUPPORTED",
            description=f"**SUPPORTED OPERATORS:**\n{ NUMERIC_OPERATORS }"
        )
        invalidOperatorEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        return invalidOperatorEmbed

    # START: Verify arg length isn't over limits
    if len(args) >= 201:
        return await ctx.send(embed=argLengthError())

    # Send command usage if no args are supplied
    if len(args) <= 0:
        rollUsageEmbed = discord.Embed(
            color=discord.Colour.orange(),
            title="`?roll` requires at least one argument",
            description="**USAGE**\n`?roll [ROLLS]d[SIDES]`\n*Example:* `?roll 3d20 + 3`"
        )
        rollUsageEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await ctx.send(embed=rollUsageEmbed)

    # Init response embed
    diceRollEmbed = discord.Embed(
        color=discord.Colour.purple()
    )
    diceRollEmbed.add_field(name="QUERY", value=args, inline=False)
    diceRollEmbed.insert_field_at(index=2, name="RESULTS", value="----------", inline=False)
    diceRollEmbed.set_author(name=f"Rolled by { ctx.author.display_name }", icon_url=f"{ ctx.author.avatar_url }")

    # Initialise nested result dictionary. Example for query `?r 3d8 + 8`:
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
    for argument in args:

        # Import cumulativeTotal from previous argument for the current argument
        diceRollResults[argument] = {
            "results" : [],
            "sectionTotal" : 0.0,
            "cumulativeTotal" : runningTotal
        }

        # If arg is a operator, isn't the first character and is a single char
        if argument in NUMERIC_OPERATORS:
            if args.index(argument) != 0:
                if len(argument) == 1:
                    currentOperator = argument
                else:
                    return await ctx.send(embed=unrecognisedNumericOperator(argument))
            else:
                operatorAtFront = discord.Embed(
                    color=discord.Colour.red(),
                    title=f"THE `{ argument }` OPERATOR CANNOT BE THE FIRST CHARACTER"
                )
                operatorAtFront.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

                return await ctx.send(embed=operatorAtFront)

        # If the arg is a dice or a number
        else:

            # If it's a number...
            numCheck = ""
            try:
                numCheck = float(argument)
            except ValueError: pass

            if isinstance(numCheck, float):
                # Ensure number isn't too big
                if numCheck <= ROLL_MAX_PARAM_VALUE:
                    # Add to dict in same manner as a dice roll total
                    diceRollResults[argument]["sectionTotal"] = numCheck
                else:
                    return await ctx.send(embed=invalidSizeSupplied(numCheck))

            # If it's a dice...
            else:

                # Verify arguments contains a valid request
                sanitisedCurrentDice = argument.lower()
                numberOfRolls = 1
                numberOfSides = 0
                regexReturn = re.search("(?P<rolls>[0-9]*)d(?P<sides>[0-9]+)", sanitisedCurrentDice)

                if regexReturn != None:

                    # Default to 1 roll if none are supplied, otherwise use the rolls group
                    if regexReturn.group("rolls") != "":

                        # Checks the amount of rolls supplied is a number and isn't too high
                        try:
                            numberOfRolls = int(regexReturn.group("rolls"))

                            if numberOfRolls >= ROLL_MAX_PARAM_VALUE:
                                return await ctx.send(embed=invalidSizeSupplied(numberOfRolls))

                        except ValueError:
                            return await ctx.send(embed=invalidArgSupplied(regexReturn.group("rolls")))

                    # Checks the amount of sides supplied is a number and is valid
                    try:
                        numberOfSides = int(regexReturn.group("sides"))

                        if numberOfSides < 2 or numberOfSides >= ROLL_MAX_PARAM_VALUE:
                            return await ctx.send(embed=invalidSizeSupplied(numberOfSides))

                    except ValueError:
                        return await ctx.send(embed=invalidArgSupplied(regexReturn.group("sides")))

                else:
                    return await ctx.send(embed=invalidArgSupplied("NO DICE SIDES DETECTED! TRY CHECKING YOUR SYNTAX AND ?roll USAGE"))

                # Calculate dice rolls and append to the dict
                for currentRoll in range(1, numberOfRolls + 1):
                    diceRollResults[argument]["results"].append(random.randint(1.0, numberOfSides))

                # Calculate the section total and append to the dict
                diceSectionTotal = 0
                for currentResult in diceRollResults[argument]["results"]:
                    diceSectionTotal += currentResult

                diceRollResults[argument]["sectionTotal"] = diceSectionTotal

                # Append to embed
                diceRollEmbed.add_field(
                    name=f"__STEP { stepCount }__\n`{ numberOfRolls }d{ numberOfSides }` ROLLED |",
                    value=f"{ diceRollResults[argument]['results'] }\n*TOTAL = { diceRollResults[argument]['sectionTotal'] }*",
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
                    return await ctx.send(embed=unrecognisedNumericOperator(currentOperator))

                # Append to embed
                diceRollEmbed.add_field(
                    name=f"__STEP { stepCount }__\n`{ currentOperator }` OPERATOR APPLIED! |",
                    value=f"{ previousTotal }\n**{ currentOperator }**\n{ diceRollResults[argument]['sectionTotal'] }\n*TOTAL = { runningTotal }*",
                    inline=True
                )

                currentOperator = ""

            # Calculate the total for the whole query so far
            diceRollResults[argument]["cumulativeTotal"] = runningTotal

            stepCount += 1

    # Append final total and send embed
    diceRollEmbed.insert_field_at(index=1, name="TOTAL", value=f"`{ runningTotal }`", inline=False)
    print(f"SENDING EMBED: { diceRollEmbed.title }...")
    await ctx.send(embed=diceRollEmbed)
    print("DONE!")


###
# FUNC NAME: ?search [ENTITY]
# FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@BOT.command(
    name='search',
    help='Queries the Open5e API to get the entities infomation.',
    usage='?search [ENTITY]',
    aliases=["sea", "s", "S"]
)
async def search(ctx, *args):

    # Sleep to wait for other stuff to complete first
    time.sleep(COMMAND_DELAY_SLEEP_VALUE)

    print(f"Executing: ?search { args }")

    # Import & reset globals
    global partial_match
    partial_match = False

    # Verify arg length isn't over limits
    if len(args) >= 201:
        return await ctx.send(embed=argLengthError())

    # Send directory contents if no search term given
    if len(args) <= 0:

        await ctx.send(embed=discord.Embed(
            color=discord.Colour.blue(),
            title="GETTING ALL SEARCHABLE ENTITIES IN SEARCH/ ENDPOINT...",
            description="WARNING: This may take a while!"
        ))

        # Get objects from directory, store in txt file
        directoryRequest = requests.get("https://api.open5e.com/search/?format=json&limit=10000")

        if directoryRequest.status_code != 200:
            return await ctx.send(embed=codeError(
                directoryRequest.status_code,
                "https://api.open5e.com/search/?format=json&limit=10000"
                )
            )

        # Generate a unique filename and write to it
        entityFileName = generateFileName("entsearch")

        entityFile = open(entityFileName, "a+")
        for entity in directoryRequest.json()["results"]:
            if "title" in entity.keys():
                entityFile.write(f"{ entity['title'] }\n")
            else:
                entityFile.write(f"{ entity['name'] }\n")

        entityFile.close()

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"See `{ entityFileName }` for all searchable entities in this endpoint", 
            description="Due to discord character limits regarding embeds, the results have to be sent in a file. Yes I know this is far from ideal but it's the best I can do!"
        )
        await ctx.send(embed=detailsEmbed)

        # Send entities file
        return await ctx.send(file=discord.File(entityFileName))

    # Filter input to remove whitespaces and set lowercase
    filteredInput = "".join(args).lower()

    # Search API
    await ctx.send(embed=discord.Embed(
        color=discord.Colour.blue(),
        title=f"SEARCHING ALL ENDPOINTS FOR { filteredInput }...",
        description="WARNING: This may take a while!"
    ))

    # Use first word to narrow search results down for quicker response on some directories
    match = requestOpen5e(f"https://api.open5e.com/search/?format=json&limit=10000&text={ str(args[0]) }", filteredInput, True)

    # An API Request failed
    if isinstance(match, dict) and "code" in match.keys():
        return await ctx.send(embed=codeError(match["code"], match["query"]))

    # Searching algorithm hit an invalid object
    elif match == "UNKNOWN":
        unknownMatchEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="ERROR",
            description="I found an entity in the API database that doesn't contain a `name` or `document` attribute. Please report this to https://github.com/shadowedlucario/oghma/issues"
        )

        unknownMatchEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        return await ctx.send(embed=unknownMatchEmbed)

    # No entity was found
    elif match == None:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.yellow(),
            title="ERROR",
            description=f"No matches found for **{ filteredInput }** in the search endpoint"
        )

        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await ctx.send(embed=noMatchEmbed)

    # Otherwise, construct & send responses
    else:
        responses = constructResponse(args, match["route"], match["matchedObj"])
        for response in responses:

            if isinstance(response, discord.Embed):

                # Set a thumbnail for relevant embeds and on successful Scryfall request, overwriting all other thumbnail setup
                image = requestScryfall(args, False)

                if (not isinstance(image, int)): response.set_thumbnail(url=image)

                # Note partial match in footer of embed
                if partial_match:
                    response.set_footer(text=f"NOTE: Your search term ({ filteredInput }) was a PARTIAL match to this entity.\nIf this isn't the entity you were expecting, try refining your search term or use ?searchdir instead")
                else:
                    response.set_footer(text="NOTE: If this isn't the entity you were expecting, try refining your search term or use `?searchdir` instead")

                print(f"SENDING EMBED: { response.title }...")
                await ctx.send(embed=response)

            elif ".txt" in response:
                print(f"SENDING FILE: { response }...")
                await ctx.send(file=discord.File(response))

    print("DONE!")

###
# FUNC NAME: ?searchdir [RESOURCE] [ENTITY]
# FUNC DESC: Queries the Open5e RESOURCE API.
# RESOURCE:  Resource name (i.e. spells, monsters, etc.).
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@BOT.command(
    name='searchdir',
    help='Queries the Open5e API to get entities infomation from specified resource.',
    usage='?search [RESOURCE] [ENTITY]',
    aliases=["dir", "d", "D"]
)
async def searchdir(ctx, *args):

    # Sleep to wait for other stuff to complete first
    time.sleep(COMMAND_DELAY_SLEEP_VALUE)

    print(f"EXECUTING: ?searchdir { args }")

    # Import & reset globals
    global partial_match
    partial_match = False

    # Get API Root
    rootRequest = requests.get("https://api.open5e.com?format=json")

    # Throw if Root request wasn't successfull
    if rootRequest.status_code != 200:
        return await ctx.send(embed=codeError(rootRequest.status_code, "https://api.open5e.com?format=json"))

    # Remove search endpoint from list (not used in this command)
    directories = list(rootRequest.json().keys())
    directories.remove("search")

    # Verify we have arguments
    if len(args) <= 0:
        usageEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="No directory was requested.\nUSAGE: `?searchdir [DIRECTORY] [D&D OBJECT]`",
            description=f"**Available Directories**\n{ ', '.join(directories) }"
        )

        usageEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await ctx.send(embed=usageEmbed)

    # Filter the dictionary input
    filteredDictionary = f"{ args[0].lower() }/"

    # Filter input to remove whitespaces and set lowercase
    filteredInput = "".join(args[1:]).lower()

    # Verify arg length isn't over limits
    if len(args) >= 201:
        return await ctx.send(embed=argLengthError())

    # Verify resource exists
    if directories.count(args[0]) <= 0:

        noResourceEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"Requested Directory (`{ str(args[0]) }`) is not a valid directory name",
            description=f"**Available Directories**\n{ ', '.join(directories) }"
        )

        noResourceEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await ctx.send(embed=noResourceEmbed)

    # Send directory contents if no search term given
    if len(args) == 1:

        await ctx.send(embed=discord.Embed(
            color=discord.Colour.blue(),
            title=f"GETTING ALL SEARCHABLE ENTITIES IN { filteredDictionary.upper() } ENDPOINT...",
            description="WARNING: This may take a while!"
        ))

        # Get objects from directory, store in txt file
        directoryRequest = requests.get(f"https://api.open5e.com/{ filteredDictionary }?format=json&limit=10000")

        if directoryRequest.status_code != 200:
            return await ctx.send(embed=codeError(
                directoryRequest.status_code,
                f"https://api.open5e.com/{ filteredDictionary }?format=json&limit=10000"
                )
            )

        entityNames = []
        for entity in directoryRequest.json()["results"]:
            if "title" in entity.keys(): entityNames.append(entity['title'])
            else: entityNames.append(entity['name'])

        # Keep description word count low to account for names with lots of characters
        if len(entityNames) <= 200:

            detailsEmbed = discord.Embed(
                colour=discord.Colour.orange(),
                title="All searchable entities in this endpoint",
                description="\n".join(entityNames)
            )

            detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
            if "search" in filteredDictionary:
                detailsEmbed.set_footer(text="NOTE: The `search` endpoint is not searchable with `?searchdir`. Use `?search` instead for this.")

            return await ctx.send(embed=detailsEmbed)

        # Generate a unique filename and write to it
        entityDirFileName = generateFileName("entsearchdir")

        entityFile = open(entityDirFileName, "a+")
        entityFile.write("\n".join(entityNames))
        entityFile.close()

        # Send embed notifying start of the spam stream
        detailsEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"See `{ entityDirFileName }` for all searchable entities in this endpoint",
            description="Due to discord character limits regarding embeds, the results have to be sent in a file. Yes I know this is far from ideal but it's the best I can do!"
        )

        detailsEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        if "search" in filteredDictionary:
            detailsEmbed.set_footer(text="NOTE: The `search` endpoint is not searchable with `?searchdir`. Use `?search` instead for this.")

        await ctx.send(embed=detailsEmbed)

        # Send entities file
        return await ctx.send(file=discord.File(entityDirFileName))

    # search/ endpoint is best used with the dedicated ?search command
    if "search" in filteredDictionary:

        # Remove search endpoint from list
        directories = list(rootRequest.json().keys())
        directories.remove("search")

        searchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title=f"Requested Directory (`{ str(args[0]) }`) is not a valid directory name", 
            description=f"**Available Directories**\n{ ', '.join(directories) }"
        )

        searchEmbed.add_field(name="NOTE", value="Use `?search` for searching the `search/` directory. This has been done to cut down on parsing errors.")
        searchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await ctx.send(embed=searchEmbed)

    # Search API
    await ctx.send(embed=discord.Embed(
        color=discord.Colour.blue(),
        title=f"SEARCHING { filteredDictionary.upper() } ENDPOINT FOR { filteredInput }...",
        description="WARNING: This may take a while!"
    ))

    # Determine filter type (search can only be used for some endpoints)
    filterType = "text"
    if args[0] in SEARCH_PARAM_ENDPOINTS: filterType = "search"

    # Use first word to narrow search results down for quicker response on some directories
    match = requestOpen5e(
        f"https://api.open5e.com/{ filteredDictionary }?format=json&limit=10000&{ filterType }={ str(args[1]) }",
        filteredInput,
        False
    )

    # An API Request failed
    if isinstance(match, dict) and "code" in match.keys():
        return await ctx.send(embed=codeError(match.code, match.query))

    # Searching algorithm hit an invalid object
    elif match == "UNKNOWN":
        unknownMatchEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="ERROR",
            description="I found an entity in the API database that doesn't contain a `name` or `document` attribute. Please report this to https://github.com/shadowedlucario/oghma/issues"
        )

        unknownMatchEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        return await ctx.send(embed=unknownMatchEmbed)

    # No entity was found
    elif match == None:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR",
            description=f"No matches found for **{ filteredInput.upper() }** in the { filteredDictionary } endpoint"
        )

        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")

        return await ctx.send(embed=noMatchEmbed)

    # Otherwise, construct & send responses
    else:
        responses = constructResponse(args, filteredDictionary, match)
        for response in responses:

            if isinstance(response, discord.Embed):

                # Set a thumbnail for relevant embeds and on successful Scryfall request, overwrites other thumbnail setup
                image = requestScryfall(args, True)

                if (not isinstance(image, int)): response.set_thumbnail(url=image)

                # Note partial match in footer of embed
                if partial_match:
                    response.set_footer(text=f"NOTE: Your search term ({ filteredInput }) was a PARTIAL match to this entity.\nIf this isn't the entity you were expecting, try refining your search term")

                print(f"SENDING EMBED: { response.title }...")
                await ctx.send(embed=response)

            elif ".txt" in response:
                print(f"SENDING FILE: { response }...")
                await ctx.send(file=discord.File(response))

    print("DONE!")

BOT.run(os.environ['BOT_KEY'])
