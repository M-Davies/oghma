###
# Project: oghma
# Author: shadowedlucario
# https://github.com/shadowedlucario
###

import os
import requests
import json
import discord
import logging
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

### GLOBALS ###
botName = "Oghma"
TOKEN = os.getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='?')
client = discord.Client()
partialMatch = False

# Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

###
# FUNC NAME: on_ready
# FUNC DESC: Tells you when bot is ready to accept commands
# FUNC TYPE: Command
###
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

###
# FUNC NAME: on_command_error
# FUNC DESC: If an error is thrown this func is executed
# FUNC TYPE: Event
###
@bot.event
async def on_command_error(ctx, error):
    
    raise Exception(error)

###
# FUNC NAME: ?ping
# FUNC DESC: Pings the bot to check it is live
# FUNC TYPE: Command
###
@bot.command(name='ping', help='Pings the bot.\nUsage: !ping')
async def ping(ctx):
    await ctx.send('Pong!')

###
# FUNC NAME: searchResponse
# FUNC DESC: Searches the API response for the user input. Returns None if nothing was found
# FUNC TYPE: Function
###
def searchResponse(responseResults, filteredInput):
    global partialMatch
    match = None
    for entity in responseResults:

        # Strip whitespaces and lower case before checking if it's match
        if "title" in entity:

            # Has to be in it's own "if" to avoid KeyErrors
            if entity["title"].replace(" ", "").lower() == filteredInput:
                match = entity
                break

            # Now try partially matching the entity (i.e. bluedragon will match adultbluedragon here)
            if filteredInput in entity["title"].replace(" ", "").lower():
                partialMatch = True

                match = entity
                break
        
        elif "name" in entity:
            
            if entity["name"].replace(" ", "").lower() == filteredInput:
                match = entity
                break

            if filteredInput in entity["name"].replace(" ", "").lower():
                partialMatch = True

                match = entity
                break

        else: raise Exception("Object does not have a 'name' or 'title' field\n**OBJECT**: {}".format(entity))

    return match

###
# FUNC NAME: requestAPI
# FUNC DESC: Queries the API. 
# FUNC TYPE: Function
###
def requestAPI(query, filteredInput, wideSearch):

    # API Request
    request = requests.get(query)

    # Return code if not successfull
    if request.status_code != 200: return request.status_code

    # Iterate through the results
    output = searchResponse(request.json()["results"], filteredInput)

    if output == None: return output

    # Find resource object if coming from search endpoint
    elif wideSearch == True:

        # Request resource using the first word of the name to filter results
        # NOTE: Documents are not supported for this as they are not in /search at the time of writing this
        route = output["route"]
        resourceRequest = requests.get(
            "https://api.open5e.com/{}?format=json&limit=10000&search={}"
            .format(
                route, 
                output["name"].split()[0]
            )
        )

        # Return code if not successfull
        if resourceRequest.status_code != 200: return resourceRequest.status_code

        # Search response again for the actual object
        resourceOutput = searchResponse(resourceRequest.json()["results"], filteredInput)

        return {"route": route, "matchedObj": resourceOutput}

    # If already got the resource object, just return it
    else: return output

###
# FUNC NAME: constructResponse
# FUNC DESC: Constructs embed responses from the API object.
# FUNC TYPE: Function
###
def constructResponse(filteredInput, route, matchedObj):
    responseEmbeds = []

    # Document
    if route == "documents/":
        documentEmbed = None

        # Description charecter length for embeds is 2048, titles is 256
        if len(matchedObj["desc"]) >= 2048:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (DOCUMENT)".format(matchedObj["title"]), 
                description=matchedObj["desc"][:2047]
            )
            documentEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:])
        else:
            documentEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["title"], 
                description=matchedObj["desc"]
            )
        documentEmbed.add_field(name="Authors", value=matchedObj["author"], inline=False)
        documentEmbed.add_field(name="Link", value=matchedObj["url"], inline=True)
        documentEmbed.add_field(name="Version Number", value=matchedObj["version"], inline=True)
        documentEmbed.add_field(name="Copyright", value=matchedObj["copyright"], inline=False)

        documentEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")
        documentEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        responseEmbeds.append(documentEmbed)

    # Spell
    elif route == "spells/":
        spellEmbed = None

        if len(matchedObj["desc"]) >= 2048:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (SPELL)".format(matchedObj["name"]), 
                description=matchedObj["desc"][:2047]
            )
            spellEmbed.add_field(name="Description Continued...", value=matchedObj["desc"][2048:], inline=False)
        else:
            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["name"], 
                description=matchedObj["desc"]
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
        spellEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        responseEmbeds.append(spellEmbed)

    # Monster
    elif route == "monsters/":
        ## 1ST EMBED ##
        monsterEmbedBasics = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MONSTER): BASIC STATS".format(matchedObj["name"]), 
            description="**TYPE**: {}\n**SUBTYPE**: {}\n**ALIGNMENT**: {}\n**SIZE**: {}\n**CHALLENGE RATING**: {}".format(
                matchedObj["type"] if matchedObj["type"] != "" else "None", 
                matchedObj["subtype"] if matchedObj["subtype"] != "" else "None", 
                matchedObj["alignment"] if matchedObj["alignment"] != "" else "None",
                matchedObj["size"],
                matchedObj["challenge_rating"]
            )
        )

        # Str
        if matchedObj["strength_save"] != None:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["strength"],
                    matchedObj["strength_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="STRENGTH",
                value="**{}**".format(matchedObj["strength"]),
                inline=True
            )

        # Dex
        if matchedObj["dexterity_save"] != None:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["dexterity"],
                    matchedObj["dexterity_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="DEXTERITY",
                value="**{}**".format(matchedObj["dexterity"]),
                inline=True
            )

        # Con
        if matchedObj["constitution_save"] != None:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["constitution"],
                    matchedObj["constitution_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CONSTITUTION",
                value="**{}**".format(matchedObj["constitution"]),
                inline=True
            )

        # Int
        if matchedObj["intelligence_save"] != None:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["intelligence"],
                    matchedObj["intelligence_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="INTELLIGENCE",
                value="**{}**".format(matchedObj["intelligence"]),
                inline=True
            )

        # Wis
        if matchedObj["wisdom_save"] != None:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["wisdom"],
                    matchedObj["wisdom_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="WISDOM",
                value="**{}**".format(matchedObj["wisdom"]),
                inline=True
            )

        # Cha
        if matchedObj["charisma_save"] != None:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value="**{}** (SAVE: **{}**)".format(
                    matchedObj["charisma"],
                    matchedObj["charisma_save"]
                ),
                inline=True
            )
        else:
            monsterEmbedBasics.add_field(
                name="CHARISMA",
                value="**{}**".format(matchedObj["charisma"]),
                inline=True
            )

        # Hit points/dice
        monsterEmbedBasics.add_field(
            name="HIT POINTS ({})".format(str(matchedObj["hit_points"])), 
            value=matchedObj["hit_dice"], 
            inline=True
        )

        # Speeds
        monsterSpeeds = ""
        for speed in matchedObj["speed"].items(): 
            monsterSpeeds += "**{}**: {}\n".format(speed[0].upper(), str(speed[1]))
        monsterEmbedBasics.add_field(name="SPEED", value=monsterSpeeds, inline=True)

        # Armour
        monsterEmbedBasics.add_field(
            name="ARMOUR CLASS", 
            value="{} ({})".format(str(matchedObj["armor_class"]), matchedObj["armor_desc"]),
            inline=True
        )

        responseEmbeds.append(monsterEmbedBasics)

        ## 2ND EMBED ##
        monsterEmbedSkills = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MONSTER): SKILLS & PROFICIENCIES".format(matchedObj["name"])
        )

        # Skills & Perception
        if matchedObj["skills"] != {} and matchedObj["perception"] != None:
            monsterSkills = ""
            for skill in matchedObj["skills"].items(): 
                monsterSkills += "**{}**: {}\n".format(skill[0].upper(), str(skill[1]))
            monsterEmbedSkills.add_field(name="SKILLS", value=monsterSkills, inline=True)

        elif matchedObj["perception"] != None:
            monsterEmbedSkills.add_field(name="PERCEPTION", value=str(matchedObj["perception"]), inline=True)
        else: pass

        # Senses
        monsterEmbedSkills.add_field(name="SENSES", value=matchedObj["senses"], inline=True)

        # Languages
        monsterEmbedSkills.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Damage conditionals
        monsterEmbedSkills.add_field(
            name="STRENGTHS & WEAKNESSES",
            value="**VULNERABLE TO:** {}\n**RESISTANT TO:** {}\n**IMMUNE TO:** {}".format(
                matchedObj["damage_vulnerabilities"] if matchedObj["damage_vulnerabilities"] != None else "Nothing",
                matchedObj["damage_resistances"] if matchedObj["damage_resistances"] != None else "Nothing",
                matchedObj["damage_immunities"] if matchedObj["damage_immunities"] != None else "Nothing" 
                    + ", "
                        + matchedObj["condition_immunities"] if matchedObj["condition_immunities"] != None else "Nothing",
            ),
            inline=False
        )

        responseEmbeds.append(monsterEmbedSkills)

        ## 3RD EMBED ##
        monsterEmbedActions = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (MONSTER): ACTIONS AND ABILITIES".format(matchedObj["name"])
        )

        # Actions
        for action in matchedObj["actions"]:
            monsterEmbedActions.add_field(
                name=action["name"],
                value=action["desc"],
                inline=False
            )
        
        # Reactions
        if matchedObj["reactions"] != "":
            for reaction in matchedObj["reactions"]:
                monsterEmbedActions.add_field(
                    name=reaction["name"],
                    value=reaction["desc"],
                    inline=False
                )

        # Specials
        for special in matchedObj["special_abilities"]:
            monsterEmbedActions.add_field(
                name=special["name"],
                value=special["desc"],
                inline=False
            )

        # Spells
        if matchedObj["spell_list"] != []:
            for spell in matchedObj["spell_list"]:
                spellSplit = spell.replace("-", " ").split("/")

                # Remove trailing /, leaving the spell name as the last element in list
                del spellSplit[-1]

                monsterEmbedActions.add_field(
                    name=spellSplit[-1].upper(),
                    value="To see spell info, `?searchdir SPELLS {}`".format(spellSplit[-1].upper()),
                    inline=False
                )

        responseEmbeds.append(monsterEmbedActions)

        ## 4TH EMBED (only used if it has legendary actions) ##
        if matchedObj["legendary_desc"] != "":
            monsterEmbedLegend = discord.Embed(
                colour=discord.Colour.green(),
                title="{} (MONSTER): LEGENDARY ACTIONS AND ABILITIES".format(matchedObj["name"]),
                description=matchedObj["legendary_desc"]
            )

            for action in matchedObj["legendary_actions"]:
                monsterEmbedLegend.add_field(
                    name=action["name"],
                    value=action["desc"],
                    inline=False
                )

            responseEmbeds.append(monsterEmbedLegend)

        # Author & Image for all embeds
        for embed in responseEmbeds: 
            embed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

            if matchedObj["img_main"] != None: embed.set_thumbnail(url=matchedObj["img_main"])
            else: embed.set_thumbnail(url="https://i.imgur.com/6HsoQ7H.jpg")

    # Background
    elif route == "background/":
        backgroundEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title="{} (BACKGROUND)".format(matchedObj["name"])
        )

        # Description
        backgroundEmbed.add_field(name="DESCRIPTION", value=matchedObj["desc"], inline=False)

        # Profs
        if matchedObj["tool_proficiencies"] != None: 
            backgroundEmbed.add_field(name="PROFICIENCIES", value="**SKILL**: {}\n**TOOL**: {}".format(
                matchedObj["skill_proficiencies"],
                matchedObj["tool_proficiencies"]
                ),
                inline=True
            )
        else:
            backgroundEmbed.add_field(name="PROFICIENCIES", value="**SKILL**: {}".format(
                matchedObj["skill_proficiencies"]
                ),
                inline=True
            )

        # Languages
        if matchedObj["languages"] != None: backgroundEmbed.add_field(name="LANGUAGES", value=matchedObj["languages"], inline=True)

        # Equipment
        backgroundEmbed.add_field(name="EQUIPMENT", value=matchedObj["equipment"], inline=False)

        # Feature
        backgroundEmbed.add_field(name=matchedObj["feature"], value=matchedObj["feature_desc"], inline=False)

        # Charecteristics
        if matchedObj["suggested_characteristics"] != None:
            backgroundEmbed.add_field(name="CHARECTERISTICS", value=matchedObj["suggested_characteristics"], inline=False)

        backgroundEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")
        backgroundEmbed.set_thumbnail(url="https://i.imgur.com/GhGODan.jpg")

        responseEmbeds.append(backgroundEmbed)

        

    # Plane

    # Section

    # Feat

    # Condition

    # Race

    # Class

    # Magic Item

    # Weapon
    
    else:
        # Don't add a footer to an error embed
        global partialMatch
        partialMatch = False

        noRouteEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="The matched item's type (i.e. spell, monster, etc) was not recognised",
            description="Please create an issue describing this failure and with the following values at https://github.com/M-Davies/oghma/issues\n**Input**: {}\n**Route**: {}\n**Troublesome Object**: {}".format(
                filteredInput, route, matchedObj
            )
        )
        noRouteEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        noRouteEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")
        
        responseEmbeds.append(noRouteEmbed)

    return responseEmbeds


###
# FUNC NAME: ?search [ENTITY]
# FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(
    pass_context=True,
    name='search',
    help='Queries the Open5e API to get the entities infomation.\nUsage: ?search [ENTITY]',
    usage='?search [ENTITY]'
)
async def search(ctx, *args):

    # Import & reset globals
    global partialMatch
    partialMatch = False

    # Verify arg length
    if len(args) > 100 or len(args) <= 0:
        argumentsEmbed = discord.Embed(
            color=discord.Colour.red(),
            title="Invalid arguments",
            description="`?{}` requires at least one argument and cannot support more than 100\nUsage: `?search [D&D OBJECT YOU WANT TO SEARCH FOR]`"
        )
        argumentsEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        argumentsEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=argumentsEmbed)

    # Filter input to remove whitespaces and set lowercase
    filteredInput = "".join(args).lower()

    # Search API
    await ctx.send(embed=discord.Embed(
        color=discord.Colour.blue(),
        title="SEARCHING ALL ENDPOINTS FOR {} (filtered input)...".format(args),
        description="WARNING: This may take a while!"
    ))
    
    # Use first word to narrow search results down for quicker response
    match = requestAPI("https://api.open5e.com/search/?format=json&limit=10000&text={}".format(str(args[0])), filteredInput, True)

    # An API Request failed
    if isinstance(match, int):
        codeEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="ERROR", 
            description="API Request FAILED. Status Code: **{}**".format(str(match))
        )
        
        codeEmbed.add_field(name="For more idea on what went wrong:", value="See status codes at https://www.django-rest-framework.org/api-guide/status-codes/")

        codeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
        codeEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=codeEmbed)

    # No entity was found
    elif match == None:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR", 
            description="No matches found for **{}** in the search endpoint".format(filteredInput.upper())
        )

        noMatchEmbed.set_thumbnail(url="https://i.imgur.com/obEXyeX.png")
        noMatchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/Pq2fobL.jpg")

        return await ctx.send(embed=noMatchEmbed)

    # Otherwise, construct & send response embeds
    else:
        responseEmbeds = constructResponse(filteredInput, match["route"], match["matchedObj"])
        for embed in responseEmbeds:

            # Note partial match in footer of embed
            if partialMatch == True: 
                embed.set_footer(text="NOTE: Your search term ({}) was a PARTIAL match to this entity. If this isn't the entity you were expecting, try refining your search term or use ?searchdir instead".format(args))
            else:
                embed.set_footer(text="NOTE: If this isn't the entity you were expecting, try refining your search term or use ?searchdir instead")

            await ctx.send(embed=embed)

###
# FUNC NAME: ?searchdir [RESOURCE] [ENTITY]
# FUNC DESC: Queries the Open5e RESOURCE API.
# ENDPOINT:  Resource/endpoint name (i.e. spells, monsters, etc.).
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(name='searchdir', help='Queries the Open5e API to get the entities infomation from the specified resource.\nUsage: ?searchdir [RESOURCE] [ENTITY]')
async def searchdir(ctx, *args):
    print("no")

bot.run(TOKEN)
