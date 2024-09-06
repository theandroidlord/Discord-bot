import discord
from discord.ext import commands
from tpblite import TPB
from dotenv import load_dotenv
import requests
import os
import logging
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import speedtest as speedtest_module  # Renaming the import to avoid conflicts
 
# Load environment variables from .env file
load_dotenv()
 
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
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
 
@bot.command()
async def speedtest(ctx):
    await ctx.send("Running speed test... This may take a few seconds.")
 
    try:
        st = speedtest_module.Speedtest()  # Use the renamed import
        st.get_best_server()
        download_speed = st.download() / 10**6  # Convert from bits to megabits
        upload_speed = st.upload() / 10**6      # Convert from bits to megabits
        ping = st.results.ping
 
        result = (
            f"**Speed Test Results:**\n"
            f"**Download Speed:** {download_speed:.2f} Mbps\n"
            f"**Upload Speed:** {upload_speed:.2f} Mbps\n"
            f"**Ping:** {ping} ms"
        )
        await ctx.send(result)
 
    except Exception as e:
        await ctx.send(f"An error occurred during the speed test: {str(e)}")
 
@bot.event
async def on_reaction_add(reaction, user):
    logging.info(f"Reaction added: {reaction.emoji} by {user.name}")
    if reaction.emoji == '📋' and not user.bot:
        magnet_link = reaction.message.content.split('**Magnet**: ')[1]
        await reaction.message.channel.send(f"{user.mention} copied: {magnet_link}")
 
@bot.command()
async def stream(ctx, url: str):
    if ctx.author.voice is None:
        await ctx.send("You are not connected to a voice channel.")
        return
 
    channel = ctx.author.voice.channel
    voice_client = await channel.connect()
 
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
 
    voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
    await ctx.send(f'Streaming: {url}')
 
@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Stopped streaming.")
    else:
        await ctx.send("The bot is not connected to a voice channel.")
 
@bot.command()
async def movieinfo(ctx, *, movie_name):
    url = f"https://www.omdbapi.com/?t={movie_name}&apikey={OMDB_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if data['Response'] == 'True':
        title = data['Title']
        year = data['Year']
        rating = data['imdbRating']
        plot = data['Plot']
        director = data['Director']
        actors = data['Actors']
        poster = data['Poster']

        embed = discord.Embed(title=title, description=plot, color=0x00ff00)
        embed.set_image(url=poster)
        embed.add_field(name="Year", value=year, inline=True)
        embed.add_field(name="IMDb Rating", value=rating, inline=True)
        embed.add_field(name="Director", value=director, inline=True)
        embed.add_field(name="Actors", value=actors, inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Movie not found.")
)
 
# Simple HTTP server to satisfy Render's port binding requirement
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Hello, Render!')
 
def run_http_server():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()
 
# Run HTTP server in a separate thread
http_thread = Thread(target=run_http_server)
http_thread.start()
 
# Run the Discord bot
bot.run(DISCORD_BOT_TOKEN)