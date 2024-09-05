import discord
from discord.ext import commands
from tpblite import TPB
from dotenv import load_dotenv
import os
import flask
import logging
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello, Render!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    

# Load environment variables from .env file
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ALLOWED_SERVERS = os.getenv('ALLOWED_SERVERS').split(',')

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Set up logging
logging.basicConfig(level=logging.INFO)

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
    else:
        await ctx.send("No torrents found.")

@bot.event
async def on_reaction_add(reaction, user):
    logging.info(f"Reaction added: {reaction.emoji} by {user.name}")
    if reaction.emoji == '📋' and not user.bot:
        magnet_link = reaction.message.content.split('**Magnet**: ')[1]
        await reaction.message.channel.send(f"{user.mention} copied: {magnet_link}")

bot.run(DISCORD_BOT_TOKEN)
