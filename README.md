# Oghma - Rules and references bot for discord dnd groups
[![Discord Bots](https://top.gg/api/widget/658336624647733258.svg)](https://top.gg/bot/658336624647733258)

# Overview 
This is (yet another) discord bot for dnd groups on discord. The bot is pretty simple, it pulls in and parses data from [Open5e](https://open5e.com/) to be displayed in discord. The whole open5e database is utilised, meaning you can query the bot for dnd conditions, spells, monsters, whatever you need to lookup in the heat of the moment!

# How it works
The bot accepts a search phrase (known as an entity) which it feeds into the [Open5e API](https://api.open5e.com/), imploying various boring parsing and filtration techniques to ensure the request is legit. The bot first searches the API for an exact match, then for a partial one (i.e. `dragon` will match `adult black dragon`). When it finds a match, it then uses the [Scryfall search/ API](https://api.scryfall.com/cards/search) to find a suitable picture for the response [embed](https://discordjs.guide/popular-topics/embeds.html) (if it doesn't have one in the first place) and sends the infomation back to the sender. Sometimes more than one embed or even files need to be sent due to discord API charecter restrictions

# Commands

# ?search [ENTITY]
- Utilises the Open5e [search/](https://api.open5e.com/search/) endpoint to search the entire database for the ENTITY given.
- This takes longer than `?searchdir` but provides a lot wider searchbase if you don't know what you're looking for.

# ?searchdir [DIRECTORY] [ENTITY]
- Searches a specific DIRECTORY in the Open5e database for the ENTITY. The total list of available directories is:
```
"spells"
"monsters"
"documents"
"backgrounds"
"planes"
"sections" (NOT CURRENTLY SUPPORTED)
"feats"
"conditions"
"races"
"classes"
"magicitems"
"weapons"
```
- This is quicker than `?search`, with a smaller searchbase limited to the directory

# How to add to your server
We have a top.gg page! See https://top.gg/bot/658336624647733258
