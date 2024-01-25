import discord
import logging
import config

LOGGER = logging.getLogger(__name__)


def codeError(statusCode: int, query: str):
    """
    FUNC NAME: codeError
    FUNC DESC: Sends an embed informing the user that there has been an API request failure
    FUNC TYPE: Error
    """
    codeEmbed = discord.Embed(
        colour=discord.Colour.red(),
        title=f"ERROR - API Request FAILED. Status Code: **{str(statusCode)}**",
        description=f"Query: {query}"
    )

    codeEmbed.add_field(
        name="For more idea on what went wrong:",
        value="See status codes at https://www.django-rest-framework.org/api-guide/status-codes/",
        inline=False
    )

    codeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    LOGGER.error(f"Sending Open5e Root API Request FAILED embed = {codeEmbed.to_dict()}")
    return codeEmbed


def argLengthError():
    """
    FUNC NAME: argLengthError
    FUNC DESC: Sends an embed informing the user that their request is too long
    FUNC TYPE: Error
    """
    argLengthErrorEmbed = discord.Embed(
        color=discord.Colour.red(),
        title="Invalid argument length",
        description="This command does not support more than 200 words in a single message. Try splitting up your query."
    )
    argLengthErrorEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    return argLengthErrorEmbed


def invalidArgSupplied(culprit):
    """
    Returns an invalid args embed
    """
    invalidArgsEmbed = discord.Embed(
        color=discord.Colour.red(),
        title=f"Invalid argument (`{culprit}`) supplied to /roll",
        description="This is likely due to the value being too low or high.\n\n**USAGE**\n`/roll [ROLLS]d[SIDES]`\n*Example:* `/roll 3d20 + 3`"
    )
    invalidArgsEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    LOGGER.info(f"Invalid argument supplied to /roll = {culprit}")
    return invalidArgsEmbed


def invalidSizeSupplied(culprit):
    """
    Returns an invalid size of args supplied embed
    """
    invalidSizeEmbed = discord.Embed(
        color=discord.Colour.red(),
        title=f"Invalid size of argument (`{culprit}`) supplied to /roll",
        description=f"ROLLS and SIDES and STATIC NUMBERS supplied to `/roll` must be numbers of a reasonable value (CURRENT LIMIT = {config.ROLL_MAX_PARAM_VALUE}).\n\n**USAGE**\n`?roll [ROLLS]d[SIDES]`\n*Example:* `?roll 3d20 + 3`"
    )
    invalidSizeEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    LOGGER.info(f"Invalid size of argument supplied to /roll = {culprit}")
    return invalidSizeEmbed


def unrecognisedNumericOperator(numericOperator):
    """
    Return invalid numeric operator embed
    """
    invalidOperatorEmbed = discord.Embed(
        color=discord.Colour.red(),
        title=f"`{numericOperator}` IS NOT SUPPORTED",
        description=f"**SUPPORTED OPERATORS:**\n{config.NUMERIC_OPERATORS}"
    )
    invalidOperatorEmbed.set_thumbnail(url="https://i.imgur.com/j3OoT8F.png")
    LOGGER.info(f"Unrecognised numeric operator supplied to /roll = {numericOperator}")
    return invalidOperatorEmbed
