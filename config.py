import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Bot configuration"""
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///stock_bot.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Timezone
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh")
    
    # Secret Key
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # VNStock Data Sources (comma-separated priority list)
    VNSTOCK_DATA_SOURCES = os.getenv("VNSTOCK_DATA_SOURCES", "TCBS,VCI,MSN").split(',')
