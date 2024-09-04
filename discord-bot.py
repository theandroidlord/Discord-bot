import discord
from discord.ext import commands
from tpblite import TPB
from seedrcc import Login, Seedr
from dotenv import load_dotenv
import os
import logging
import unittest

# Load environment variables from .env file
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SEEDR_EMAIL = os.getenv('SEEDR_EMAIL')
SEEDR_PASSWORD = os.getenv('SEEDR_PASSWORD')
ALLOWED_SERVERS = os.getenv('ALLOWED_SERVERS').split(',')

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Set up logging
logging.basicConfig(level=logging.INFO)

def seedr_login():
    try:
        seedr = Login(SEEDR_EMAIL, SEEDR_PASSWORD)
        seedr.authorize()
        return Seedr(token=seedr.token)
    except Exception as e:
        logging.error(f"Seedr login failed: {e}")
        return None

def add_torrent_to_seedr(magnet_link, seedr):
    try:
        response = seedr.addTorrent(magnet_link)
        return response
    except Exception as e:
        logging.error(f"Failed to add torrent to Seedr: {e}")
        return {'error': str(e)}

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')

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
        if seedr:
            response = add_torrent_to_seedr(magnet_link, seedr)
            if 'error' not in response:
                await reaction.message.channel.send(f"{user.mention} mirrored to Seedr: {response['title']}")
            else:
                await reaction.message.channel.send(f"{user.mention} failed to mirror to Seedr: {response['error']}")
        else:
            await reaction.message.channel.send(f"{user.mention} failed to login to Seedr.")

bot.run(DISCORD_BOT_TOKEN)

# Unit tests
class TestSeedrFunctions(unittest.TestCase):
    def test_seedr_login(self):
        seedr = seedr_login()
        self.assertIsNotNone(seedr, "Seedr login should not return None")

    def test_add_torrent_to_seedr(self):
        seedr = seedr_login()
        if seedr:
            response = add_torrent_to_seedr("magnet_link_example", seedr)
            self.assertNotIn('error', response, "Adding torrent should not return an error")

if __name__ == '__main__':
    unittest.main()
