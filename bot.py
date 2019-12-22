import os
import random
import discord

from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()
#token = os.getenv('DISCORD_TOKEN')
token = 'NjU4MzM2NjI0NjQ3NzMzMjU4.Xf-1dw.h7dYLr6XmjHgtvgG7aEZO5rWrUg'

bot = commands.Bot(command_prefix='!')

client = discord.Client()

###
# FUNC NAME: on_error()
# FUNC DESC: Error Handler that records error messages in a file
# FUNC TYPE: Event
###
@client.event
async def on_error(event, *args, **kwargs):
    print(f'Exception Thrown!')
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

###
# FUNC NAME: on_command_error()
# FUNC DESC: Error Handler that responds to an access denied user
# FUNC TYPE: Event
###
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')

###
# FUNC NAME: !rolldice
# FUNC DESC: Dice roller (sides and dice number specified by the user)
# FUNC TYPE: Command
###
@bot.command(name='rolldice', help='Simulates rolling dice.\nUsage: !rolldice [number-of-dice] [number-of-sides]')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))

###
# FUNC NAME: !addchannel
# FUNC DESC: Create a channel (requires: admin)
# FUNC TYPE: Command
###
@bot.command(name='addchannel', help='Creates a new channel\nUsage (requires: Admin): !addchannel [channel-name]')
@commands.has_role('Admin')
async def create_channel(ctx, *args):
    guild = ctx.guild
    existing_channel = discord.utils.get(guild.channels, name=args[0])
    if not existing_channel:
        print(f'Creating a new channel: {args[0]}')
        await guild.create_text_channel(args[0])


bot.run(token)