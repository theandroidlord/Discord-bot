import discord
from discord.ext import commands
from tpblite import TPB
from seedrcc import Login, Seedr
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SEEDR_EMAIL = os.getenv('SEEDR_EMAIL')
SEEDR_PASSWORD = os.getenv('SEEDR_PASSWORD')
ALLOWED_SERVERS = os.getenv('ALLOWED_SERVERS').split(',')

bot = commands.Bot(command_prefix='!')

def seedr_login():
    seedr = Login(SEEDR_EMAIL, SEEDR_PASSWORD)
    seedr.authorize()
    return Seedr(token=seedr.token)

def add_torrent_to_seedr(magnet_link, seedr):
    response = seedr.addTorrent(magnet_link)
    return response

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def search(ctx, *, query):
    if str(ctx.guild.id) not in ALLOWED_SERVERS:
        await ctx.send("This bot is not allowed to operate in this server.")
        return

    tpb = TPB()
    torrents = tpb.search(query)
    if torrents:
        for torrent in torrents[:5]:  # Limit to top 5 results
            message = await ctx.send(f"**Title**: {torrent.title}\n**Seeds**: {torrent.seeds}\n**Magnet**: {torrent.magnetlink}")
            await message.add_reaction('📋')  # Add a clipboard emoji reaction
            await message.add_reaction('🌐')  # Add a globe emoji reaction for mirroring
    else:
        await ctx.send("No torrents found.")

@bot.event
async def on_reaction_add(reaction, user):
    if reaction.emoji == '📋' and not user.bot:
        magnet_link = reaction.message.content.split('**Magnet**: ')[1]
        await reaction.message.channel.send(f"{user.mention} copied: {magnet_link}")
    elif reaction.emoji == '🌐' and not user.bot:
        magnet_link = reaction.message.content.split('**Magnet**: ')[1]
        seedr = seedr_login()
        response = add_torrent_to_seedr(magnet_link, seedr)
        if 'error' not in response:
            await reaction.message.channel.send(f"{user.mention} mirrored to Seedr: {response['title']}")
        else:
            await reaction.message.channel.send(f"{user.mention} failed to mirror to Seedr: {response['error']}")

bot.run(DISCORD_BOT_TOKEN)
