from discord import Intents, Embed
from discord.ext import commands, tasks
import discord
from bs4 import BeautifulSoup
import requests

import io
from PIL import Image

import cv2
import numpy as np
import urllib.request
import pytesseract

from dotenv import load_dotenv
import os

load_dotenv()

# Grab the API token from the .env file.
BOT_TOKEN = str(os.getenv("DISCORD_TOKEN"))

# Configure the URL of the store website you want to monitor
WEBSITE_URL = str(os.getenv("WEBSITE_URL"))

DIAMONDS_FACTORY_CHANNEL_ID = int(os.getenv("DIAMONDS_FACTORY_CHANNEL_ID"))
BOT_ACTIVITY_CHANNEL_ID = int(os.getenv("BOT_ACTIVITY_CHANNEL_ID"))

TESSERACT_LOCATION = str(os.getenv("TESSERACT_LOCATION"))

# Define the intents
intents = Intents.default()
intents.message_content = True

# GETS THE CLIENT OBJECT FROM DISCORD.PY. CLIENT IS SYNONYMOUS WITH BOT.
bot = commands.Bot(command_prefix="!", intents=intents)

# Set the path to the Tesseract-OCR executable (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = f"{TESSERACT_LOCATION}"

def extract_text_from_image(image_url):
    try:
        # Download the image
        image_response = requests.get(image_url)
        image_response.raise_for_status()

        # Create a Discord File object from the image data
        image_file = discord.File(io.BytesIO(image_response.content), filename="diamond_factory_sale_image.jpg")

        # Load the image from the Discord File object
        image = Image.open(io.BytesIO(image_file.fp.read()))

        # Extract text from the image
        text = pytesseract.image_to_string(image)

        if text:
            print(text)

        return text

    except Exception as e:
        print(f"Error processing image: {e}")

# @tasks.loop(hours=1)  # Adjust the interval as needed
async def check_diamonds_factory_sales():
    try:
        response = requests.get(WEBSITE_URL + 'sale')
        response.raise_for_status()  # Raise an exception for non-200 status codes

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all 'picture' elements
        picture_elements = soup.find_all('picture')

        for picture_element in picture_elements:
            # Find the 'img' tag within the 'picture' element
            image_element = picture_element.find('img')

            if image_element:
                # Extract the image URL from the 'src' attribute
                image_url = image_element.get('src')

                try:

                    # Check if the URL contains "menu_collection"
                    if "menu_collection" not in image_url:
                        # Construct the full image URL
                        full_image_url = WEBSITE_URL + image_url

                        # Download the image
                        image_response = requests.get(full_image_url)
                        image_response.raise_for_status()

                        # Create a Discord File object from the image data
                        image_file = discord.File(io.BytesIO(image_response.content), filename="diamond_factory_sale_image.jpg")

                        # Extract text and get the Discord File object from the image
                        saleText = extract_text_from_image(full_image_url)

                        # Send the image to the Diamonds Factory Discord channel
                        channel = bot.get_channel(DIAMONDS_FACTORY_CHANNEL_ID)
                        await channel.send(content=f"**Diamond Factory Sale:** \n{saleText}" if saleText else "", file=image_file)

                except Exception as e:
                    print(f"Error processing image: {e}")

            else:
                await bot.get_channel(DIAMONDS_FACTORY_CHANNEL_ID).send("Image element not found within the 'picture' tag.")

    except Exception as e:
        await bot.get_channel(DIAMONDS_FACTORY_CHANNEL_ID).send(f"Error checking Diamonds Factory sales: {e}")

# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
@bot.event
async def on_ready():
  global DIAMONDS_FACTORY_CHANNEL_ID, BOT_ACTIVITY_CHANNEL_ID

  # Send update to the Bot Activity Channel
  channel = bot.get_channel(BOT_ACTIVITY_CHANNEL_ID)
  bot_activity_message = "{0.user}".format(bot) + " is now online!"
  await channel.send(bot_activity_message)

  # Schedule the function to run every hour (adjust as needed)
  # check_diamonds_factory_sales.start() # Use when there is a time loop
  await check_diamonds_factory_sales()

bot.run(BOT_TOKEN)