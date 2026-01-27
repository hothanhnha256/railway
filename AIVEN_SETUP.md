# 🎯 Hướng dẫn lấy DATABASE_URL từ Aiven

## Bước 1: Truy cập Aiven Console

1. Đăng nhập vào [Aiven Console](https://console.aiven.io/)
2. Chọn PostgreSQL service của bạn

## Bước 2: Lấy Connection String

### Cách 1: Từ Overview Tab

1. Click vào PostgreSQL service
2. Tab **"Overview"**
3. Tìm section **"Connection Information"**
4. Copy **"Service URI"**

### Cách 2: Từ Connection Info Button

1. Click nút **"Quick Connect"** hoặc **"Connection Information"**
2. Chọn language: **Python** hoặc **General**
3. Copy URI có format:

```
postgresql://avnadmin:password@pg-xxxxx-yyyy-zzzz.aivencloud.com:12345/defaultdb?sslmode=require
```

## Bước 3: Format Connection String

Aiven cung cấp URI đầy đủ, bạn chỉ cần copy y nguyên:

```bash
postgresql://[username]:[password]@[host]:[port]/[database]?sslmode=require
```

**Ví dụ thực tế:**

```
postgresql://avnadmin:AVNS_abc123xyz@pg-stock-bot-project.aivencloud.com:12345/defaultdb?sslmode=require
```

### ⚠️ Quan trọng:

- ✅ Phải có `?sslmode=require` ở cuối
- ✅ Port thường là `12345` hoặc `10628` (tùy theo khu vực)
- ✅ Username mặc định: `avnadmin`
- ✅ Database mặc định: `defaultdb`

## Bước 4: Thêm vào Railway

1. Vào Railway project dashboard
2. Click tab **"Variables"**
3. Click **"New Variable"**
4. Tên: `DATABASE_URL`
5. Giá trị: Paste connection string từ Aiven
6. Click **"Add"**

## 🔒 Bảo mật

- ❌ **KHÔNG** commit connection string vào Git
- ✅ Chỉ lưu trong environment variables
- ✅ Sử dụng `.env` cho local development
- ✅ Rotate password định kỳ trong Aiven console

## 📊 Kiểm tra kết nối

Sau khi deploy, check Railway logs:

```bash
✅ Database initialized
🤖 Bot is starting...
```

Nếu thấy lỗi database, kiểm tra:

1. Connection string có đúng format không
2. Aiven service có đang chạy không (không bị paused)
3. IP whitelist (nếu có cấu hình)
