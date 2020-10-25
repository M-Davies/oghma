# Oghma - Rules and references bot for discord dnd groups

[![Discord Bots](https://top.gg/api/widget/658336624647733258.svg)](https://top.gg/bot/658336624647733258)

## Overview

This is (yet another) discord bot for dnd groups on discord. The bot is pretty simple, it pulls in and parses data from [Open5e](https://open5e.com/) to be displayed in discord.
The whole open5e database is utilised, meaning you can query the bot for dnd conditions, spells, monsters, whatever you need to lookup in the heat of the moment!

## How it works

The bot accepts a search phrase (known as an entity) which it feeds into the [Open5e API](https://api.open5e.com/), using various boring parsing and filtration techniques to ensure the request is legit. The bot first searches the API for an exact match, then for a partial one (i.e. `dragon` will match `adult black dragon`).

When it finds a match, it then uses the [Scryfall search/ API](https://api.scryfall.com/cards/search) to find a suitable picture for the response [embed](https://discordjs.guide/popular-topics/embeds.html) (if it doesn't have one in the first place) and sends the information back to the sender.
Sometimes more than one embed or even files need to be sent due to discord API character restrictions

## Commands

NOTE: Most commands enforce a word limit of 200 words per query

### ?roll [ROLLS]d[SIDES]

**ALIASES `[throw, dice, r, R]`**

- Rolls a dice `ROLLS` times of `SIDES` many sides. Each roll result is recorded and displayed to the end user as well as all the steps taken by the command. `ROLLS` can be omitted (the bot will default to 1 roll) but `SIDES` must be equal to at least 2.
- You can also use various operators to make complex sums and equations on your dice roll queries. Obviously, this means that standalone numbers (e.g. `4` `7.2`) are supported too. As of writing this, the currently supported operators are below.

```python
"+" # Addition
"-" # Subtraction
"*" # Multiplication
"/" # Division
```

- `ROLLS` and `SIDES` values are treated as single decimal point values but any standalone numbers are treated as decimal pointed, meaning `?roll 1d20.5` would eval to `?roll 1d20` but `?roll 1d20.5 + 7.5` would eval to `?roll 1d20 + 7.5`.
- Spaces must be placed between operators and arguments, otherwise it's likely your dice roll will not be calculated correctly. `?roll 3d4 + 3` is fine but `?roll 3d4+3` would only evaluate to `?roll 3d4`.

![Image of Rolls Example](/images/rollsExample.png)

- The steps are listed to show a user what order the program has calculated the final total in, as well as showing the running/cumulative total at that time of calculation.

### ?search [ENTITY]

**ALIASES = `[sea, s, S]`**

- Utilises the Open5e [search/](https://api.open5e.com/search/) endpoint to search the entire database for the ENTITY given. `search/` is like a directory (see below) that lists items in the database, but it also provides links and pointers to the original object in it's respective directory. This is how the bot will find your requested entity.
- This takes longer than `?searchdir` but provides a lot wider searchbase if you don't know what category your entity is in.

### ?searchdir [DIRECTORY] [ENTITY]

**ALIASES = `[dir, d, D]`**

- Searches a specific DIRECTORY in the Open5e database for the ENTITY. As of writing this, the total list of available directories is:

```python
"spells" # Contains spell names, effects and other stats (Fireball, Light, etc)
"monsters" # Contains monster names, powers and other stats (Adult Black dragon, Kraken, etc)
"documents" # Contains documents that open5e uses to populate their api & database (e.g. Tome Of Beasts, Creature Codex, etc)
"backgrounds" # Contains background details and effects for PC's (e.g. Scoundrel)
"planes" # Contains plane descriptions of what they are like (e.g. The Material Plane)
"sections" # Basically a misc directory, this contains dnd entities of various categories (Armour, Alignment, etc)
"feats" # Contains feat descriptions and prerequisites (e.g. Grappler)
"conditions" # Contains condition effects (blinded, charmed, etc)
"races" # Contains race effects and descriptions, including subraces (Dwarves, Elves, etc)
"classes" # Contains class abilities and progression table, including subclasses (Wizard, Warrior, etc)
"magicitems" # Contains magic artifact powers and restrictions (Deck of Many Things, Animated Shield, etc)
"weapons" # Contains weapon stats and ranges (Longsword, Short bow, etc)
```

- This is quicker than `?search`, with a smaller searchbase limited to the directory

### How to add to your server

We have a top.gg page! Assuming the link in the image above doesn't work, [click this text for a working link](https://top.gg/bot/658336624647733258)

### Contributing

All contributions are welcome! Please join our [discord](https://discord.gg/8YZ2NZ5) and post a greeting in `#contributing` to get started. Also check out our [Testing.md](./TESTING.md) guide to setting up your own test bot to push new features and fixes (requires joining the discord)!
It's just me working on the bot at the moment so any and all help would be appreciated :)
