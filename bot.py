import os
import requests
import json
import discord
import time
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

### GLOBALS ###
botName = "Oghma"
TOKEN = os.getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='?')
client = discord.Client()

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
# FUNC NAME: ?ping
# FUNC DESC: Pings the bot to check it is live
# FUNC TYPE: Command
###
@bot.command(name='ping', help='Pings the bot.\nUsage: !ping')
async def ping(ctx):
    await ctx.send('Pong!')

###
# FUNC NAME: throwCodeError
# FUNC DESC: Throws an error if the api status code is not a successful one 
# FUNC TYPE: Function
###
def throwCodeError(location, code):

    # Construct error embed
    embed = discord.Embed(
        colour=discord.Colour.red(),
        title="ERROR", 
        description="API Request on {} FAILED".format(location)
    )
    embed.add_field(name="Status Code", value=code)
    embed.add_field(name="For more information:", value="See https://www.django-rest-framework.org/api-guide/status-codes/")
    
    embed.timestamp(time.ctime())
    embed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/apple/237/cross-mark_274c.png")
    embed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

    # Respond and exit
    return embed

###
# FUNC NAME: requestAndSearchAPI
# FUNC DESC: Queries and parses the API. 
# FUNC TYPE: Function
###
def requestAndSearchAPI(query, filteredInput):
    output = []

    nextPage = True
    pageNum = 1

    while nextPage:
        newQuery = query
        request = None
        response = None

        # Alter query if changing page
        if (pageNum != 1): newQuery = query + "&page={}".format(str(pageNum))
            
        print("Current query: {}".format(newQuery))

        # API Request
        request = requests.get(newQuery)
        statusCode = request.status_code

        # Throw error if not successfull
        if statusCode != 200: 
            output = throwCodeError(newQuery, statusCode)
            break

        # Iterate through the objects
        response = request.json()

        for i in response["results"]:
            match = False

            try:
                # Strip whitespaces and lower case before checking if it's match
                match = i["name"].replace(" ", "").lower() == filteredInput or i["title"].replace(" ", "").lower() == filteredInput

            # Filter out KeyErrors for objects that don't have the title field
            except KeyError: pass

            if match: output.append(i)
    
        # Check if there is another page
        if response["next"] == None: 
            nextPage = False
        else:
            pageNum = pageNum + 1

    return output

###
# FUNC NAME: constructResponse
# FUNC DESC: Constructs an embed response from the API object.
# FUNC TYPE: Function
###
def constructResponse(responseArray, filteredInput):
    embeds = []

    if (responseArray == []):
        
        # Not found
        failEmbed = discord.Embed(
            colour=discord.Colour.red(),
            title="ERROR", 
            description="No matches found for **{}** in the search endpoint".format(filteredInput.upper())
        )

        failEmbed.timestamp(time.ctime())
        failEmbed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/apple/237/black-question-mark-ornament_2753.png")
        failEmbed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        # Append to embeds
        embeds.append(failEmbed)

    else:

        # Iterate through matches
        for i in responseArray:

            # Found document
            if i["title"]:

                documentEmbed = discord.Embed(
                    colour=discord.Colour.blue(),
                    title=i["title"], 
                    description=i["desc"]
                )
                documentEmbed.add_field(name="Authors", value=i["author"])
                documentEmbed.add_field(name="Link", value=i["url"], inline=True)
                documentEmbed.add_field(name="Version Number", value=i["version"], inline=True)

                documentEmbed.timestamp(time.ctime())
                documentEmbed.set_thumbnail(url="https://i.imgur.com/lnkhxCe.jpg")
                documentEmbed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

                embeds.append(documentEmbed)

            # Found something else
            elif i["name"]:

                embeds = discord.Embed(
                    colour=discord.Colour.green(),
                    title="ERROR", 
                    description="No matches found for {} in the search endpoint".format(filteredInput.upper())
                )
                embeds.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

    # Return responses
    return embeds

###
# FUNC NAME: ?search [ENTITY]
# FUNC DESC: Queries the Open5e search API, basically searches the whole thing for the ENTITY.
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(pass_context=True, name='search', help='Queries the Open5e API to get the entities infomation.\nUsage: ?search [ENTITY]')
async def search(ctx, *args):

    print(args)
    print(len(args))

    # Verify arg length
    if len(args) != 1: raise Exception("Command requires only one parameter")

    # Filter input to remove whitespaces and set lowercase
    filteredInput = args[0].replace(" ", "").lower()

    # Search API
    ctx.send("SEARCHING API...")
    matches = requestAndSearchAPI("https://api.open5e.com/search/?format=json", filteredInput)

    # Construct embeds
    responseEmbed = constructResponse(matches, filteredInput)

    # Send responses
    for embed in responseEmbed: await ctx.send(embed=embed)

###
# FUNC NAME: ?searchDirectory [DIRECTORY] [ENTITY]
# FUNC DESC: Queries the Open5e DIRECTORY API.
# ENDPOINT:  Directory/endpoint name (i.e. spells, monsters, etc.).
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(name='searchDirectory', help='Queries the Open5e API to get the entities infomation from the specified directory.\nUsage: ?searchDirectory [DIRECTORY] [ENTITY]')
async def searchDirectory(ctx, *args):

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

    # Throw error if not successfull
    if rootRequest.status_code != 200: throwCodeError(rootQuery, rootRequest.status_code)

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
    matches = requestAndSearchAPI("https://api.open5e.com/{}/?format=json".format(filteredDirectory), filteredInput)

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
