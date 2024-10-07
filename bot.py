from discord import Intents, Embed  # Imports for Discord functionality (Intents for selective event handling, Embed for rich messages)
from discord.ext import commands, tasks  # Imports for Discord bot commands and background tasks
import discord  # General Discord library import

from bs4 import BeautifulSoup  # Library for parsing HTML content
import requests  # Library for making HTTP requests

import io
from PIL import Image  # Libraries for image processing and manipulation

import cv2  # OpenCV library for computer vision tasks
import numpy as np  # Library for numerical operations

import urllib.request  # Library for URL retrieval (consider using `requests` for consistency)
import pytesseract  # Library for optical character recognition (OCR)

from dotenv import load_dotenv  # Library for managing environment variables
import os  # Library for interacting with the operating system

from selenium import webdriver  # Library for web browser automation
from selenium.webdriver.common.by import By  # Used to identify web elements by various methods
from selenium.webdriver.support.ui import WebDriverWait  # Used for waiting for web elements to appear
from selenium.webdriver.support import expected_conditions as EC  # Various conditions for waiting (presence, visibility, etc.)

# Load environment variables from a `.env` file for security and maintainability
load_dotenv()

# Grab the API token from the environment variable for secure bot authentication
BOT_TOKEN = str(os.getenv("DISCORD_TOKEN"))

# Configure the URL of the store website you want to monitor from the environment variable
WEBSITE_URL = str(os.getenv("WEBSITE_URL"))

# Channel ID for sending Diamond Factory updates (retrieve from Discord developer portal)
DIAMONDS_FACTORY_CHANNEL_ID = int(os.getenv("DIAMONDS_FACTORY_CHANNEL_ID"))

# Channel ID for sending bot activity messages (optional, for logging purposes)
BOT_ACTIVITY_CHANNEL_ID = int(os.getenv("BOT_ACTIVITY_CHANNEL_ID"))

# Path to Tesseract OCR engine (ensure it's installed and accessible)
TESSERACT_LOCATION = str(os.getenv("TESSERACT_LOCATION"))

# URL of the first item you want to check for price changes (from the environment variable)
ITEM_1_PRICE_URL = str(os.getenv("ITEM_CHECK_1_URL"))

# Define the intents
intents = Intents.default()
intents.message_content = True

# GETS THE CLIENT OBJECT FROM DISCORD.PY. CLIENT IS SYNONYMOUS WITH BOT.
bot = commands.Bot(command_prefix="!", intents=intents)

# Set the path to the Tesseract-OCR executable (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = f"{TESSERACT_LOCATION}"

def extract_text_from_image(image_url):
    """Extracts text from an image at the specified URL using Tesseract OCR.

    Args:
        image_url (str): The URL of the image containing the text to be extracted.

    Returns:
        str: The extracted text from the image, or None if an error occurs.
    """

    try:
        # Download the image
        image_response = requests.get(image_url)
        image_response.raise_for_status()  # Raise an exception for non-200 status codes

        # Create a Discord File object from the image data
        image_file = discord.File(io.BytesIO(image_response.content), filename="diamond_factory_sale_image.jpg")

        # Load the image directly using PIL (if format is known)
        image = Image.open(io.BytesIO(image_file.fp.read()))

        # Extract text from the image using Tesseract
        text = pytesseract.image_to_string(image)

        return text

    except Exception as e:
        print(f"Error processing image: {e}")
        return None  # Indicate failure by returning None

async def check_item_price(item_url):
    """Checks the price of an item on a website and sends a formatted message to Discord.

    Args:
        item_url (str): The URL of the item page.

    Raises:
        Exception: Any error encountered during the process.
    """
    try:
        # Use Selenium to load the page and wait for elements to appear
        driver = webdriver.Chrome()
        driver.get(item_url)

        # Wait for the `pricemetalD` element to appear
        pricemetalD_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pricepopupCont"))
        )

        # Get the entire HTML content
        html_content = driver.page_source

        # Close the driver (optional, can be done in the finally block)
        driver.quit()

        # Create a BeautifulSoup object
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all span elements with the specified class name within pricemetalD
        pricemetalD_element = soup.find(class_="pricemetalD")
        metal_price_element = pricemetalD_element.find(id="metalPrice")
        metalband_foot_element = pricemetalD_element.find(class_="metalband_foot")

        # Find all span elements with the specified class name within pricediamonD
        pricediamonD_element = soup.find(class_="pricediamonD")
        stone_price_element = pricediamonD_element.find(id="stonePrice")
        stone_size_element = pricediamonD_element.find(class_="pd_car_foot")
        stone_shape_element = pricediamonD_element.find(class_="centerstoneshape")

        # Find all span elements with the specified class name within pricediamonD
        priceMainDiv_element = soup.find(class_="priceMainDiv")
        total_price_element = priceMainDiv_element.find(class_="pprice")

        # Extract the text from the elements
        metal_price = metal_price_element.text.strip()
        metal_type = metalband_foot_element.text.strip()

        stone_price = stone_price_element.text.strip()
        stone_size = stone_size_element.text.strip()
        stone_shape = stone_shape_element.text.strip()

        total_price = total_price_element.text.strip()

        # Create a formatted Discord message
        message =   f"{metal_type}: \t\t\t\t **  {metal_price}**\n" \
                    f"{stone_size}ct {stone_shape} Diamond: \t **{stone_price}**\n" \
                    f"{'-' * 36}\n" \
                    f"Total: \t\t\t\t\t\t\t **CAD {total_price}**"

        # Send the message to Discord
        channel = bot.get_channel(DIAMONDS_FACTORY_CHANNEL_ID)
        await channel.send(message)

    except Exception as e:
        print(f"Error processing item price: {e}")
        import traceback
        traceback.print_exc()  # Print the full traceback

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
    global DIAMONDS_FACTORY_CHANNEL_ID, BOT_ACTIVITY_CHANNEL_ID, ITEM_1_PRICE_URL

    # Send update to the Bot Activity Channel
    channel = bot.get_channel(BOT_ACTIVITY_CHANNEL_ID)
    bot_activity_message = "{0.user}".format(bot) + " is now online!"
    await channel.send(bot_activity_message)

    # Schedule the function to run every hour (adjust as needed)
    # check_diamonds_factory_sales.start() # Use when there is a time loop
    await check_diamonds_factory_sales()

    # Check the ring price and sale price
    await check_item_price(ITEM_1_PRICE_URL)

bot.run(BOT_TOKEN)