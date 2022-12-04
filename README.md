# Oghma - Rules and references bot for discord dnd groups

[![Discord Bots](https://top.gg/api/widget/658336624647733258.svg)](https://top.gg/bot/658336624647733258)

## Overview

This is (yet another) discord bot for dnd groups on discord. The bot is pretty simple, it pulls in and parses data from [Open5e](https://open5e.com/) to be displayed in discord.
The whole Open5e database is utilised, meaning you can query the bot for dnd conditions, spells, monsters, whatever you need to lookup in the heat of the moment!

## How it works

The bot accepts a search phrase (known as an entity) which it feeds into the [Open5e API](https://api.open5e.com/), using various boring parsing and filtration techniques to ensure the request is legit. The bot first searches the API for an exact match, then for a partial one (i.e. `dragon` will match `adult black dragon`).

When it finds a match, it then uses the [Scryfall search/ API](https://api.scryfall.com/cards/search) to find a suitable picture for the [response](https://discordjs.guide/popular-topics/embeds.html) (if it doesn't have one in the first place) and sends the information back to the sender.

Sometimes more than one embed or even files need to be sent due to discord API character restrictions

## Commands

- Most commands enforce a word limit of 200 words per query.
- The first word in an entity is used to optimise a query to Open5e:
  - For example, in the command `/search monsters frost giant`, frost giant will be treated as the entity, with `frost` being the word that optimises the search.
  - This means that you need to be careful where you put spaces and what word you place first in your query, as each will produce radically different results. So if you're getting weird results, try changing what word you lead with.
  - For example, `/search monsters frostgiant` produces no results as there are no monsters that include the full search term `frostgiant`.

### /help

Display bot latency, author information (me!) and useful data. Pretty simple tbh.

### /roll [CALCULATION]

- Conducts a mathematical CALCULATION similar to rolling a dice and adding modifiers. The CALCULATION can include dice rolls (in the format `[ROLLS]d[SIDES]`, such as `3d8`) and logical operators.
- Each roll result is recorded and displayed to the end user as well as all the steps taken by the command. `ROLLS` can be omitted (the bot will default to 1 roll) but `SIDES` must be equal to at least 2.
- You can also use various operators to make complex sums and equations on your dice roll queries. Obviously, this means that standalone numbers (e.g. `4` `7.2`) are supported too. As of writing this, the currently supported operators are below.

```python
"+" # Addition
"-" # Subtraction
"*" # Multiplication
"/" # Division
```

- `ROLLS` and `SIDES` values are treated as single decimal point values but any standalone numbers are treated as decimal pointed. Meaning, `/roll 1d20.5` would evaluate to `/roll 1d20` but `/roll 1d20.5 + 7.5` would evaluate to `/roll 1d20 + 7.5`.
- Spaces must be placed between operators and arguments, otherwise it's likely your dice roll will not be calculated correctly. `/roll 3d4 + 3` is fine but `/roll 3d4+3` would only evaluate to `/roll 3d4`.

![Image of Rolls Example](https://raw.githubusercontent.com/M-Davies/oghma/master/images/rollsExample.png)

- The steps are listed to show a user what order the program has calculated the final total in, as well as showing the running/cumulative total at that time of calculation.

### /search [ENTITY]

- Utilises the Open5e [search/](https://api.open5e.com/search/) directory to search the entire database for the ENTITY given.
- `search/` is like a directory (see below) that lists items in the database, but it also provides links and pointers to the original object in it's respective directory. This is how the bot will find your requested ENTITY.
- This takes longer than `/searchdir` but provides a bigger area to search. Especially useful if you don't know what category your ENTITY is in.

### /searchdir [DIRECTORY] [?ENTITY]

- Searches a specific DIRECTORY in the Open5e database for the ENTITY. Check out the [Open5e API Root Page](https://api.open5e.com/) for the supported directories.
- If no ENTITY is provided, the bot will instead return all the searchable entities in the requested DIRECTORY, providing a handy reference for you in the future.
- This is quicker than `/search`, with a smaller searchbase limited to the DIRECTORY. Handy if you need your result to be accurate.

### /lst [ENTITY] [?DIRECTORY]

- Returns a list of all the full and partial matches in Open5e to a requested ENTITY as well as their parent directories.
- You could use this to narrow down repetitive search results or to find where a specific spell or item appears.
- You can optionally add a DIRECTORY name to search for matches specifically within that directory or omit it to search the entire database for the requested entity.

## How to add to your server

We have a top.gg page! Assuming the link in the image above doesn't work, [click this text for a working link](https://top.gg/bot/658336624647733258)

## Contributing

All contributions are welcome! Please join our [discord](https://discord.gg/8YZ2NZ5) and post a greeting in `#contributing` to get started. Also check out our [Testing.md](https://github.com/M-Davies/oghma/blob/master/TESTING.md) guide to setting up your own test bot to push new features and fixes (requires joining the discord)!
It's just me working on the bot at the moment so any and all help would be appreciated :)

## Privacy

No user data is stored on who executed what command, just logs of what command was initiated anonymously are stored for debugging purposes. 
