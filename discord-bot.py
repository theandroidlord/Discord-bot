import discord
import asyncio
from discord.ext import commands
from discord.ui import Button, View
from tpblite import TPB
from dotenv import load_dotenv
import requests
import subprocess
import os
import logging
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
import speedtest as speedtest_module  
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import time
import asyncio

# Renaming the import to avoid conflicts

# Load e nvironment variables from .env file
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
async def remind(ctx, minutes: int, *, reminder_text):
    try:
        if minutes <= 0:
            await ctx.send("Please enter a positive number of minutes.")
            return

        await ctx.send(f"Reminder set for {minutes} minutes.")

        async def send_delayed_reminder():
            await ctx.send('Hi Your Reminder 🎗️for ' + reminder_text)

        await asyncio.sleep(minutes * 60)
        await send_delayed_reminder()
    except ValueError:
        await ctx.send("Invalid reminder format. Please use !remind <minutes> <text>")


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

        trailer_button = Button(label="Watch Trailer", url=f"https://www.youtube.com/results?search_query={movie_name}+trailer")
        view = View()
        view.add_item(trailer_button)

        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send("Movie not found.")
        
        
async def download_file(url, local_filename, ctx):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kilobyte
    t = tqdm(total=total_size, unit='iB', unit_scale=True)
    start_time = time.time()

    with open(local_filename, 'wb') as file:
        for data in response.iter_content(block_size):
            t.update(len(data))
            file.write(data)
            elapsed_time = time.time() - start_time
            speed = t.n / elapsed_time if elapsed_time > 0 else 0
            t.set_postfix(speed=f'{speed:.2f} iB/s')
            if t.n % (block_size * 100) == 0:  # Update every 100 KB
                await ctx.send(f'Downloading... {t.n / total_size:.2%} complete at {speed:.2f} iB/s')
    t.close()

    if total_size != 0 and t.n != total_size:
        raise Exception("Error in downloading file")

    return local_filename

async def upload_file(file_path, ctx):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get('https://filetransfer.io/')

    # Locate the file input element and upload the file
    file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
    file_input.send_keys(file_path)

    # Wait for the upload to complete and get the download link
    start_time = time.time()
    while True:
        try:
            download_link = driver.find_element(By.XPATH, '//a[@class="download-link"]').get_attribute('href')
            break
        except:
            elapsed_time = time.time() - start_time
            uploaded_size = os.path.getsize(file_path)
            speed = uploaded_size / elapsed_time if elapsed_time > 0 else 0
            await ctx.send(f'Uploading... {uploaded_size / os.path.getsize(file_path):.2%} complete at {speed:.2f} iB/s')
            time.sleep(1)

    driver.quit()
    return download_link

@bot.command()
async def mirror(ctx, url):
    local_filename = 'downloaded_file'
    try:
        # Download the file
        await ctx.send('Downloading file...')
        await download_file(url, local_filename, ctx)
        await ctx.send('File downloaded successfully.')

        # Upload the file to FileTransfer.io
        await ctx.send('Uploading file...')
        link = await upload_file(local_filename, ctx)
        await ctx.send(f'File uploaded: {link}')
    except Exception as e:
        await ctx.send(f'An error occurred: {e}')
    finally:
        if os.path.exists(local_filename):
            os.remove(local_filename)

       
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
