# Vietnam Stock Report Telegram Bot - Railway Deployment

🤖 Telegram bot tự động gửi báo cáo thị trường chứng khoán Việt Nam với Long Polling, tối ưu cho Railway deployment.

## ✨ Tính năng

- 📊 Báo cáo VN-Index, HNX-Index tự động
- 📈 Theo dõi nhiều mã chứng khoán
- ⏰ Gửi báo cáo định kỳ (9:00 sáng & 15:30 chiều)
- 🔔 Lệnh báo cáo ngay lập tức
- 💾 Lưu trữ dữ liệu với PostgreSQL
- 🌐 Web scraping với Playwright

## 🚀 Deploy trên Railway

### Bước 1: Chuẩn bị

1. Tạo Telegram bot với [@BotFather](https://t.me/botfather)
2. Lấy `TELEGRAM_BOT_TOKEN`
3. Lấy `TELEGRAM_CHAT_ID` của bạn (chat với [@userinfobot](https://t.me/userinfobot))

### Bước 2: Deploy

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new)

1. Click nút "Deploy on Railway" hoặc tạo project mới
2. Kết nối GitHub repository này
3. Railway sẽ tự động detect và build

### Bước 3: Cấu hình Aiven Database

1. Vào [Aiven Console](https://console.aiven.io/)
2. Chọn PostgreSQL service của bạn
3. Copy **Service URI** từ tab "Overview" → "Connection Information"
4. Format: `postgresql://avnadmin:password@host:port/defaultdb?sslmode=require`

### Bước 4: Cấu hình Environment Variables

Trong Railway dashboard, thêm các biến sau:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=postgresql://avnadmin:password@your-project.aivencloud.com:12345/defaultdb?sslmode=require
TIMEZONE=Asia/Ho_Chi_Minh
SECRET_KEY=your-random-secret-key
```

> ⚠️ **Lưu ý:** Sử dụng Aiven PostgreSQL thay vì Railway database

### Bước 5: Install Playwright Chromium

Railway sẽ tự động chạy lệnh trong `railway.json`:

```bash
playwright install chromium
```

## 📋 Các lệnh bot

- `/start` - Bắt đầu sử dụng bot
- `/help` - Xem hướng dẫn
- `/list` - Xem danh sách mã chứng khoán
- `/add <MÃ>` - Thêm mã (vd: /add VNM)
- `/remove <MÃ>` - Xóa mã
- `/report` - Nhận báo cáo ngay

## 🏗️ Cấu trúc project

```
telegram_stock_bot_rail/
├── bot.py              # Main bot file with long polling
├── config.py           # Configuration
├── requirements.txt    # Python dependencies
├── Procfile           # Railway start command
├── railway.json       # Railway build config
├── .env.example       # Environment variables template
└── app/
    ├── __init__.py
    ├── models.py      # Database models
    └── tasks.py       # Report generation tasks
```

## ⚙️ Railway Configuration

### Procfile

```
worker: python bot.py
```

### railway.json

Railway sẽ:

- Cài đặt dependencies từ `requirements.txt`
- Cài đặt Playwright Chromium
- Chạy bot với restart policy

## 🔧 Troubleshooting

### Bot không phản hồi

- Kiểm tra `TELEGRAM_BOT_TOKEN` đã đúng chưa
- Xem logs trong Railway dashboard
- Đảm bảo bot đang chạy (worker process)

### Lỗi Playwright

Railway đã được config để tự động cài Chromium:

```json
"buildCommand": "pip install -r requirements.txt && playwright install chromium"
```

### Database errors - Aiven PostgreSQL

- Kiểm tra `DATABASE_URL` có đúng format của Aiven không
- Đảm bảo connection string có `?sslmode=require` ở cuối
- Kiểm tra Aiven service đang chạy (không bị paused)
- Verify IP whitelist trong Aiven nếu có cấu hình

## 📝 Local Development

```bash
# Clone repository
git clone <your-repo>
cd telegram_stock_bot_rail

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Copy và cấu hình .env
cp .env.example .env
# Sửa .env với token của bạn

# Run bot
python bot.py
```

## 🌟 Tech Stack

- **python-telegram-bot** - Telegram Bot API wrapper với async support
- **Flask-SQLAlchemy** - Database ORM
- **vnstock** - Vietnam stock market data
- **Playwright** - Web scraping
- **PostgreSQL (Aiven)** - Managed database service
- **APScheduler** - Job scheduling

## 📄 License

MIT License - Free to use and modify

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a PR.

## 📞 Support

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub.
