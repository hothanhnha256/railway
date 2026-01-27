"""Database models for stock tracking"""
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

db = SQLAlchemy()

def generate_uuid():
    """Generate UUID for primary key"""
    return str(uuid.uuid4())

class StockSymbol(db.Model):
    """Stock symbol tracking model"""
    __tablename__ = "stock_symbols"
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<StockSymbol {self.code}>"

class TelegramUser(db.Model):
    """Telegram user tracking for sending reports"""
    __tablename__ = "telegram_users"
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    chat_id = db.Column(db.BigInteger, nullable=False, unique=True, index=True)
    username = db.Column(db.String(100), nullable=True)
    first_name = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TelegramUser {self.chat_id}>"
