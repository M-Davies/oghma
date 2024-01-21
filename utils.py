import random
import discord
import logging
import platform
import os

SEARCH_PARAM_DIRECTORIES = ["spells", "monsters", "magicitems", "weapons"]
LOGGER = logging.getLogger(__name__)


def getFileDelimiter():
    if platform.system() == "Windows":
        return "\\"
    else:
        return "/"


def generateFileName(fileType: str):
    """
    FUNC NAME: generateFileName
    FUNC DESC: Generates a filename using type of file and random number
    FUNC TYPE: Function
    """
    return f"{fileType}-{str(random.randrange(1,1000000))}.md"


def getRequestType(route: str):
    """
    FUNC NAME: getRequestType
    FUNC DESC: Calculates the request type based on what is supported by open5e and the requested route to search
    FUNC TYPE: Function
    """
    # Determine filter type (search can only be used for some directories)
    if route in SEARCH_PARAM_DIRECTORIES:
        return "search"
    else:
        return "text"


def constructResponse(entityInput: str, route: str, matchedObj: dict):
    """
    FUNC NAME: constructResponse
    FUNC DESC: Constructs embed responses from the API object.
    FUNC TYPE: Function
    """
    responses = {"files": list(), "embeds": list()}
    fileDelimiter = getFileDelimiter()

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
        # 1ST EMBED
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

        # 2ND EMBED
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

        # 3RD EMBED
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

        # 4TH EMBED (only used if it has legendary actions)
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
                with open(f"{os.getcwd()}data{fileDelimiter}{bckFileName}", "w+") as characteristicsFile:
                    characteristicsFile.write(matchedObj["suggested_characteristics"])

                responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + bckFileName}"))

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
            with open(f"{os.getcwd()}data{fileDelimiter}{sectionFilename}", "w+") as secDescFile:
                secDescFile.write(matchedObj["desc"])
            responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + sectionFilename}"))

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
        with open(f"{os.getcwd()}data{fileDelimiter}{clsDesFileName}", "w+") as descFile:
            descFile.write(matchedObj["desc"])
        responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + clsDesFileName}"))

        # Class table as a file
        LOGGER.info(f"Creating file: {clsTblFileName}")
        with open(f"{os.getcwd()}data{fileDelimiter}{clsTblFileName}", "w+") as tableFile:
            tableFile.write(matchedObj["table"])
        responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + clsTblFileName}"))

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
                    with open(f"{os.getcwd()}data{fileDelimiter}{clsArchFileName}", "w+") as archDesFile:
                        archDesFile.write(archtype["desc"])
                    responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + clsArchFileName}"))

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
            with open(f"{os.getcwd()}data{fileDelimiter}{mIfileName}", "w+") as itemFile:
                itemFile.write(matchedObj["desc"])
            responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + mIfileName}"))

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
        with open(f"{os.getcwd()}data{fileDelimiter}{badObjectFilename}", "w+") as itemFile:
            itemFile.write(matchedObj) # type: ignore

        noRouteEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="The matched item's type (i.e. spell, monster, etc) was not recognized",
            description=f"Please create an issue describing this failure and with the following values at https://github.com/M-Davies/oghma/issues\n**Input**: {entityInput}\n**Route**: {route}\n**Troublesome Object**: SEE `{badObjectFilename}`"
        )
        noRouteEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")

        responses["embeds"].append(noRouteEmbed)
        responses["files"].append(discord.File(f"{os.getcwd()}data{fileDelimiter + badObjectFilename}"))

    return responses
