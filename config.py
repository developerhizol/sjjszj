import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
SEED_STRING = os.getenv("SEED_STRING")
SENDER_ADDRESS = os.getenv("SENDER_ADDRESS")
WALLET_VERSION = os.getenv("WALLET_VERSION", "V5R1")