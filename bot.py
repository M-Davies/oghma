import os
import requests
import json
import discord
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

### GLOBALS ###
botName = "Discord Dungeon"
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
        colour="#FF0000",
        title="ERROR", 
        description="API Request on {} FAILED".format(location)
    )
    embed.add_field(name="Status Code", value=code)
    embed.add_field(name="For more information:", value="See https://www.django-rest-framework.org/api-guide/status-codes/")
    embed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

    # Respond and exit
    bot.say(embed=embed)
    raise Exception("API Request on {} FAILED.\nStatus code: {}\nSee https://www.django-rest-framework.org/api-guide/status-codes/ for more information".format(location, code))

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
        if statusCode != 200: throwCodeError(newQuery, statusCode)

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

    # TODO: Add notification of query execution
    matches = requestAndSearchAPI("https://api.open5e.com/search/?format=json", filteredInput)

    # Construct Embed
    if (matches == []):
        embed = discord.Embed(
            colour=0xff0000,
            title="ERROR", 
            description="No matches found for {} in the search endpoint".format(filteredInput.upper())
        )
        embed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        # await ctx.send(embed) # TODO: Figure out way to send embeds
        await ctx.send(embed=embed)
    else:
        # TODO: Construct embed for correct response
        print(matches)

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
        embed.set_author(name=botName, icon_url="https://i.imgur.com/HxuMICy.jpg")

        await ctx.send(embed) # TODO: Figure out way to send embeds
    else:
        print(matches)

    await ctx.send(matches) # TODO: Figure out way to send embeds
    # await bot.say(embed=embed)

bot.run(TOKEN)
