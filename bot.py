import os
import requests
import json
import discord
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

### GLOBALS ###
TOKEN = os.getenv('BOT_TOKEN')
bot = commands.Bot(command_prefix='!')
client = discord.Client()

###
# FUNC NAME: !ping
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
        if (pageNum != 1):
            newQuery = query + "&page={}".format(str(pageNum))
            
        print("Current query: {}".format(newQuery)) # TODO: Remove this debug

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
# FUNC NAME: !get [ENDPOINT] [ENTITY]
# FUNC DESC: Queries the Open5e API.
# ENDPOINT:  A directory can be specified by replacing `ENDPOINT` with the endpoint name (i.e. spells, monsters, etc.). Default is `search`.
# ENTITY: The DND entity you wish to get infomation on.
# FUNC TYPE: Command
###
@bot.command(name='get', help='Queries the Open5e API to get the entities infomation.\nUsage: !get [entity]')
async def get(ctx):

    rawEndpoint = "Spells" # TODO: Find way to get from discord
    if rawEndpoint == "": rawEndpoint = "search" #TODO: Simulate empty 1st parameter

    rawInput = "Wish" # TODO: Find way to get from discord

    if rawInput == "": raise Exception("Command requires at least one parameter")

    # Filter input to remove whitespaces and set lowercase
    filteredInput = rawInput.replace(" ", "").lower()
    filteredEndpoint = rawEndpoint.lower()

    # Get Open5e root
    rootQuery = "https://api.open5e.com/?format=json"
    rootRequest = requests.get(rootQuery)

    # Throw error if not successfull
    if rootRequest.status_code != 200: throwCodeError(rootQuery, rootRequest.status_code)

    # Iterate through directories, ensure endpoint exists
    rootResponse = rootRequest.json()
    if filteredEndpoint not in rootResponse.keys(): raise Exception("Endpoint ({}) does not exist or isn't accessible".format(filteredEndpoint))

    # Search API
    matches = requestAndSearchAPI("https://api.open5e.com/{}/?format=json".format(filteredEndpoint), filteredInput)

    # TODO: Construct embed here
    if (matches == []):
        print("No matches found for {} in the {} endpoint".format(filteredInput, filteredEndpoint))
    else:
        print(matches)

    await ctx.send(matches) # TODO: Figure out way to send embeds

bot.run(TOKEN)
