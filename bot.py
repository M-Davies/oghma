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

    # If input is too long
    if isinstance(error, commands.TooManyArguments):

        await ctx.send(embed=discord.Embed(
            color=discord.Colour.red(),
            title="Too many or Too Few arguments",
            description="`?search` requires at least one argument and cannot support more than 100"
        ))

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
    
    match = None
    for i in responseResults:

        # Strip whitespaces and lower case before checking if it's match
        if hasattr(i, "title"):

            # Has to be in it's own if to avoid KeyErrors
            if i["title"].replace(" ", "").lower() == filteredInput:
                match = i
                break
        
        elif i["name"].replace(" ", "").lower() == filteredInput:
            match = i
            break

        else: pass #TODO: ADD UNSUPPORTED OBJECT HERE

    return match

###
# FUNC NAME: requestAPI
# FUNC DESC: Queries the API. 
# FUNC TYPE: Function
###
def requestAPI(query, filteredInput, wideSearch):
            
    print("Current query: {}".format(query))

    # API Request
    request = requests.get(query)
    statusCode = request.status_code

    # Return code if not successfull
    if statusCode != 200: return statusCode

    # Iterate through the results
    output = searchResponse(request.json()["results"], filteredInput)

    if output == None: return output

    # Find resource object if coming from search endpoint
    elif wideSearch == True:

        # Request resource using the first word of the name to filter results
        # NOTE: Documents are not supported for this as they are not in /search at the time of writing this
        route = output["route"]
        resourceRequest = requests.get(
            "https://api.open5e.com/{}/?format=json&limit=10000&search={}"
            .format(
                route, 
                output["name"].split()[0]
            )
        )
        resourceRequestCode = resourceRequest.status_code

        # Return code if not successfull
        if resourceRequestCode != 200: return resourceRequestCode

        # Search response again for the actual object
        resourceOutput = searchResponse(resourceRequest.json()["results"], filteredInput)

        return {"route": route, "matchedObj": resourceOutput}

    # If already got the resource object, just return it
    else: return output

###
# FUNC NAME: constructResponse
# FUNC DESC: Constructs an embed response from the API object.
# FUNC TYPE: Function
###
def constructResponse(filteredInput, route, matchedObj):

    if hasattr(matchedObj, "title"):

        # Document
        documentEmbed = discord.Embed(
            colour=discord.Colour.green(),
            title=matchedObj["title"], 
            description=matchedObj["desc"]
        )
        documentEmbed.add_field(name="Authors", value=matchedObj["author"])
        documentEmbed.add_field(name="Link", value=matchedObj["url"], inline=True)
        documentEmbed.add_field(name="Version Number", value=matchedObj["version"], inline=True)

        documentEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")
        documentEmbed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        return documentEmbed

    # Found something else
    elif hasattr(matchedObj, "name"):

        # Spell
        if route == "spells/":

            spellEmbed = discord.Embed(
                colour=discord.Colour.green(),
                title=matchedObj["name"], 
                description=matchedObj["desc"]
            )
            if matchedObj["higher_level"] != "": spellEmbed.add_field(name="Higher Level", value=matchedObj["higher_level"])
            
            spellEmbed.add_field(name="School", value=matchedObj["school"])
            spellEmbed.add_field(name="Level", value=matchedObj["level"], inline=True)
            spellEmbed.add_field(name="Duration", value=matchedObj["duration"], inline=True)
            spellEmbed.add_field(name="Casting Time", value=matchedObj["casting_time"], inline=True)
            spellEmbed.add_field(name="Range", value=matchedObj["range"], inline=True)
            spellEmbed.add_field(name="Concentration?", value=matchedObj["concentration"], inline=True)
            spellEmbed.add_field(name="Ritual?", value=matchedObj["ritual"], inline=True)

            spellEmbed.add_field(name="Spell Components", value=matchedObj["components"])
            if "M" in matchedObj["components"]: spellEmbed.add_field(name="Material", value=matchedObj["material"])

            spellEmbed.set_footer(text="Page: {}".format(matchedObj["page"]))

            spellEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")
            spellEmbed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

            return spellEmbed

        # Monster

        # Background

        # Plane

        # Section

        # Feat

        # Condition

        # Race

        # Class

        # Magic Item

        # Weapon
    
    else: raise Exception("UNEXPECTED FAIL!")


###
# FUNC NAME: ?search [ENTITY]
# FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(pass_context=True, name='search', help='Queries the Open5e API to get the entities infomation.\nUsage: ?search [ENTITY]')
async def search(ctx, *args):

    # Verify arg length
    if len(args) > 100 or len(args) <= 0: raise commands.TooManyArguments

    # Filter input to remove whitespaces and set lowercase
    filteredInput = "".join(args).lower()
    print("Filtered input is {}".format(filteredInput))

    # Search API
    await ctx.send(embed=discord.Embed(
        color=discord.Colour.blue(),
        title="SEARCHING ALL ENDPOINTS FOR {} (filtered input)...".format(filteredInput),
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

        codeEmbed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/apple/237/cross-mark_274c.png")
        codeEmbed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        return await ctx.send(embed=codeEmbed)

    # No entity was found
    elif match == None:
        noMatchEmbed = discord.Embed(
            colour=discord.Colour.orange(),
            title="ERROR", 
            description="No matches found for **{}** in the search endpoint".format(filteredInput.upper())
        )

        noMatchEmbed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/apple/237/black-question-mark-ornament_2753.png")
        noMatchEmbed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        return await ctx.send(embed=noMatchEmbed)

    # Otherwise, construct response embed message
    else: 
        responseEmbed = constructResponse(filteredInput, match["route"], match["matchedObj"])

        # Send response
        return await ctx.send(embed=responseEmbed)

###
# FUNC NAME: ?searchdir [RESOURCE] [ENTITY]
# FUNC DESC: Queries the Open5e RESOURCE API.
# ENDPOINT:  Resource/endpoint name (i.e. spells, monsters, etc.).
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(name='searchdir', help='Queries the Open5e API to get the entities infomation from the specified resource.\nUsage: ?searchdir [RESOURCE] [ENTITY]')
async def searchdir(ctx, *args):

    rawDirectory = ""
    if len(args) == 1:
        rawDirectory = "search"
    elif len(args) == 2:
        rawDirectory == args[0]
    else:
        raise Exception("Command requires at least one parameter")


    print(args)

    rawDirectory = "Spels" # TODO: Find way to get from discord
    if rawDirectory == "": rawDirectory = "search" #TODO: Simulate empty 1st parameter

    rawInput = "Wish" # TODO: Find way to get from discord

    if rawInput == "": raise Exception("Command requires at least one parameter")

    # Filter input to remove whitespaces and set lowercase
    filteredInput = rawInput.replace(" ", "").lower()
    filteredDirectory = rawDirectory.lower()

    # Get Open5e root
    rootQuery = "https://api.open5e.com/?format=json"
    rootRequest = requests.get(rootQuery)

    # Iterate through directories, ensure endpoint exists
    rootResponse = rootRequest.json()
    if filteredDirectory not in rootResponse.keys():

        # Construct error embed
        embed = discord.Embed(
            colour=255,
            title="ERROR", 
            description="Endpoint ({}) does not exist or isn't accessible".format(filteredDirectory)
        )
        embed.add_field(name="Available endpoints:", value="")
        for entity, link in rootResponse.items(): embed.add_field(name=entity, value=link)
        embed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        await ctx.send(embed=embed) 
        raise Exception("Endpoint ({}) does not exist or isn't accessible".format(filteredDirectory))

    # Search API
    matches = requestAPI("https://api.open5e.com/{}/?format=json".format(filteredDirectory), filteredInput)

    if (matches == []):
        embed = discord.Embed(
            colour="#FF0000",
            title="ERROR", 
            description="No matches found for {} in the {} endpoint".format(filteredInput, filteredDirectory),
        )
        embed.set_author(name=botName, icon_url="https://i.imgur.com/rzuIRdT.jpg")

        await ctx.send(embed) # TODO: Figure out way to send embeds
    else:
        print(matches)

    await ctx.send(matches) # TODO: Figure out way to send embeds
    # await bot.say(embed=embed)

bot.run(TOKEN)
