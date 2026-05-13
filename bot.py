"""
Telegram Bot for Stock Report
Allows users to add/remove stock symbols and receive reports via Telegram
"""
import os
import asyncio
import logging
import threading
from datetime import time as dt_time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from flask import Flask
from config import Config
from app.models import db, StockSymbol, TelegramUser
from app.tasks import generate_report_text
import pytz

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app for database access
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


@app.route('/')
def health():
    return 'OK', 200


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    # Save user to database
    with app.app_context():
        user = TelegramUser.query.filter_by(chat_id=chat_id).first()
        if not user:
            user = TelegramUser(
                chat_id=chat_id,
                username=username,
                first_name=first_name
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user registered: {chat_id} - {username}")
    
    welcome_message = """
🤖 Chào mừng đến với Stock Report Bot!

📊 CÁC LỆNH CÓ SẴN:

🔹 /start - Bắt đầu sử dụng bot
🔹 /help - Xem hướng dẫn chi tiết
🔹 /list - Xem danh sách mã chứng khoán
🔹 /add <MÃ> - Thêm mã chứng khoán
🔹 /remove <MÃ> - Xóa mã chứng khoán
🔹 /report - Nhận báo cáo ngay lập tức

💡 VÍ DỤ:
• /add VNM - Thêm mã Vinamilk
• /add HPG - Thêm mã Hòa Phát
• /report - Xem báo cáo thị trường

⏰ Bot sẽ tự động gửi báo cáo hàng ngày!
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📖 HƯỚNG DẪN SỬ DỤNG CHI TIẾT

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 THÊM MÃ CHỨNG KHOÁN:
Cú pháp: /add <MÃ>
Ví dụ:
• /add VNM (Vinamilk)
• /add HPG (Hòa Phát)
• /add FPT (FPT Corporation)

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 XÓA MÃ CHỨNG KHOÁN:
Cú pháp: /remove <MÃ>
Ví dụ:
• /remove VNM

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 XEM DANH SÁCH MÃ:
Lệnh: /list
Hiển thị tất cả mã đang theo dõi

━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 NHẬN BÁO CÁO:
Lệnh: /report
Nhận báo cáo thị trường ngay lập tức

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 BÁO CÁO BAO GỒM:
• Chỉ số VN-Index, HNX-Index
• Giá đóng cửa từng mã
• Biến động giá (tăng/giảm)
• Khối lượng giao dịch
• Tổng giá trị giao dịch

━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BÁO CÁO TỰ ĐỘNG:
Bot tự động gửi báo cáo vào:
• 9:00 sáng - Trước giờ mở cửa
• 15:30 chiều - Sau giờ đóng cửa

━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ HỖ TRỢ:
Nếu gặp vấn đề, vui lòng liên hệ admin.
"""
    await update.message.reply_text(help_text)


async def list_symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all tracked stock symbols"""
    with app.app_context():
        symbols = StockSymbol.query.order_by(StockSymbol.created_at).all()
        
        if not symbols:
            await update.message.reply_text(
                "📋 Chưa có mã chứng khoán nào được theo dõi.\n\n"
                "💡 Sử dụng /add <MÃ> để thêm mã.\n"
                "Ví dụ: /add VNM"
            )
            return
        
        message = "📋 DANH SÁCH MÃ CHỨNG KHOÁN:\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, sym in enumerate(symbols, 1):
            created = sym.created_at.strftime("%d/%m/%Y %H:%M")
            message += f"{i}. 📌 {sym.code}\n   ⏰ Thêm lúc: {created}\n\n"
        
        message += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 Tổng cộng: {len(symbols)} mã"
        
        await update.message.reply_text(message)


async def add_symbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new stock symbol"""
    if not context.args:
        await update.message.reply_text(
            "❌ Vui lòng nhập mã chứng khoán.\n\n"
            "💡 Cú pháp: /add <MÃ>\n"
            "📝 Ví dụ: /add VNM"
        )
        return
    
    code = context.args[0].strip().upper()
    
    with app.app_context():
        # Check if symbol already exists
        existing = StockSymbol.query.filter_by(code=code).first()
        if existing:
            await update.message.reply_text(
                f"⚠️ Mã {code} đã tồn tại trong danh sách.\n\n"
                "💡 Sử dụng /list để xem tất cả mã."
            )
            return
        
        # Add new symbol
        new_symbol = StockSymbol(code=code)
        db.session.add(new_symbol)
        db.session.commit()
        
        await update.message.reply_text(
            f"✅ Đã thêm mã {code} vào danh sách theo dõi.\n\n"
            "💡 Sử dụng /report để xem báo cáo."
        )
        logger.info(f"Added symbol: {code}")


async def remove_symbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a stock symbol"""
    if not context.args:
        await update.message.reply_text(
            "❌ Vui lòng nhập mã chứng khoán cần xóa.\n\n"
            "💡 Cú pháp: /remove <MÃ>\n"
            "📝 Ví dụ: /remove VNM"
        )
        return
    
    code = context.args[0].strip().upper()
    
    with app.app_context():
        symbol = StockSymbol.query.filter_by(code=code).first()
        if not symbol:
            await update.message.reply_text(
                f"❌ Không tìm thấy mã {code} trong danh sách.\n\n"
                "💡 Sử dụng /list để xem tất cả mã."
            )
            return
        
        db.session.delete(symbol)
        db.session.commit()
        
        await update.message.reply_text(
            f"✅ Đã xóa mã {code} khỏi danh sách theo dõi."
        )
        logger.info(f"Removed symbol: {code}")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send report immediately"""
    await update.message.reply_text("⏳ Đang tạo báo cáo, vui lòng đợi...")
    
    with app.app_context():
        try:
            report_text = generate_report_text()
            
            # Split message if too long (Telegram limit: 4096 chars)
            if len(report_text) <= 4096:
                await update.message.reply_text(report_text)
            else:
                # Split into chunks
                chunks = []
                current_chunk = ""
                for line in report_text.split('\n'):
                    if len(current_chunk) + len(line) + 1 <= 4000:
                        current_chunk += line + '\n'
                    else:
                        chunks.append(current_chunk)
                        current_chunk = line + '\n'
                if current_chunk:
                    chunks.append(current_chunk)
                
                for i, chunk in enumerate(chunks, 1):
                    if i > 1:
                        await asyncio.sleep(0.5)  # Avoid rate limiting
                    await update.message.reply_text(chunk)
            
            logger.info(f"Report sent to chat_id: {update.effective_chat.id}")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            await update.message.reply_text(
                f"❌ Lỗi khi tạo báo cáo: {str(e)}\n\n"
                "💡 Vui lòng thử lại sau hoặc liên hệ admin."
            )


async def send_scheduled_report(context: ContextTypes.DEFAULT_TYPE):
    """Send report to all registered users (called by scheduler)"""
    logger.info("🕐 Starting scheduled report...")
    
    with app.app_context():
        try:
            # Generate report
            report_text = generate_report_text()
            
            # Get all active users
            users = TelegramUser.query.filter_by(is_active=True).all()
            
            if not users:
                logger.warning("No active users to send report to")
                return
            
            logger.info(f"Sending report to {len(users)} users")
            
            # Send to all users
            for user in users:
                try:
                    # Split message if too long
                    if len(report_text) <= 4096:
                        await context.bot.send_message(
                            chat_id=user.chat_id,
                            text=report_text
                        )
                    else:
                        # Split into chunks
                        chunks = []
                        current_chunk = ""
                        for line in report_text.split('\n'):
                            if len(current_chunk) + len(line) + 1 <= 4000:
                                current_chunk += line + '\n'
                            else:
                                chunks.append(current_chunk)
                                current_chunk = line + '\n'
                        if current_chunk:
                            chunks.append(current_chunk)
                        
                        for chunk in chunks:
                            await context.bot.send_message(
                                chat_id=user.chat_id,
                                text=chunk
                            )
                            await asyncio.sleep(0.5)
                    
                    logger.info(f"✅ Sent report to chat_id: {user.chat_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Error sending to chat_id {user.chat_id}: {e}")
            
            logger.info("✅ Scheduled report completed")
            
        except Exception as e:
            logger.error(f"❌ Error in scheduled report: {e}")


def main():
    """Start the bot"""
    # Get bot token from config
    token = Config.TELEGRAM_BOT_TOKEN
    
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
        print("\n⚠️ LỖI: Chưa cấu hình TELEGRAM_BOT_TOKEN")
        print("📝 Hãy tạo file .env và thêm token của bot:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here\n")
        return
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        logger.info("✅ Database initialized")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_symbols_command))
    application.add_handler(CommandHandler("add", add_symbol_command))
    application.add_handler(CommandHandler("remove", remove_symbol_command))
    application.add_handler(CommandHandler("report", report_command))
    
    # Schedule automatic reports
    # Morning report at 9:00 AM Vietnam time
    vietnam_tz = pytz.timezone(Config.TIMEZONE)
    job_queue = application.job_queue
    
    # Morning report - 9:00 AM
    job_queue.run_daily(
        send_scheduled_report,
        time=dt_time(hour=9, minute=0, tzinfo=vietnam_tz),
        name="morning_report"
    )
    logger.info("📅 Scheduled morning report at 9:00 AM")
    
    # Afternoon report - 3:30 PM
    job_queue.run_daily(
        send_scheduled_report,
        time=dt_time(hour=15, minute=30, tzinfo=vietnam_tz),
        name="afternoon_report"
    )
    logger.info("📅 Scheduled afternoon report at 3:30 PM")
    
    # Start the bot
    logger.info("🤖 Bot is starting...")
    print("\n" + "="*50)
    print("🤖 STOCK REPORT BOT IS RUNNING!")
    print("="*50)
    print(f"⏰ Scheduled reports: 9:00 AM & 3:30 PM")
    print("="*50)
    print("✅ Bot đang chạy! Nhấn Ctrl+C để dừng.\n")
    
    # Start Flask in background thread so Render detects an open port
    port = int(os.environ.get('PORT', 5000))
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port),
        daemon=True
    )
    flask_thread.start()
    logger.info(f"Flask health server started on port {port}")

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
