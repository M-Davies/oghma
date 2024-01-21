import discord
import logging

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
