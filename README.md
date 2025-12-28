# 🤖 Tool Tự Động Kiểm Tra Đăng Ký xxx

Tool tự động kiểm tra trang đăng ký  và gửi email thông báo khi có thể đăng ký được.

## 📋 Tính Năng

- ✅ Tự động đăng nhập vào hệ thống 
- ✅ Tự động kiểm tra trang web mỗi 30 giây (có thể tùy chỉnh)
- ✅ Phát hiện khi form đăng ký xuất hiện
- ✅ Gửi email thông báo ngay lập tức đến 2 địa chỉ
- ✅ Duy trì session tự động (re-login khi cần)
- ✅ Hiển thị log chi tiết để theo dõi
- ✅ Dễ dàng cấu hình qua file JSON

## 🚀 Cài Đặt

### 1. Cài đặt Python
Đảm bảo bạn đã cài Python 3.7 trở lên:
```bash
python --version
```

### 2. Cài đặt thư viện cần thiết
```bash
pip install -r requirements.txt
```

## ⚙️ Cấu Hình

### 1. Chỉnh sửa file `config.json`


```

### 2. Cấu hình Gmail để gửi email

**Quan trọng:** Để gửi email qua Gmail, bạn cần:

#### Bước 1: Bật xác thực 2 bước
1. Truy cập https://myaccount.google.com/security
2. Bật "2-Step Verification" (Xác thực 2 bước)

#### Bước 2: Tạo App Password
1. Truy cập https://myaccount.google.com/apppasswords
2. Chọn "Mail" và "Windows Computer" (hoặc thiết bị khác)
3. Click "Generate"
4. Copy mật khẩu 16 ký tự được tạo ra
5. Điền vào `password` trong file `config.json`

**Lưu ý:** Sử dụng App Password, KHÔNG dùng mật khẩu Gmail thường!

### 3. Tùy chọn: Chạy không cần email

Nếu không muốn cấu hình email, tool vẫn chạy được và sẽ:
- Hiển thị thông báo trên màn hình console
- Có thể kết hợp với Windows notification hoặc Telegram bot sau

## 🎮 Sử Dụng

### Chạy tool:
```bash
python check_registration.py
```

### Kết quả:
```

[2025-12-28 10:30:00] Đang kiểm tra trang web...
❌ Chưa mở đăng ký (vẫn có thông báo hết slot)
------------------------------------------------------------
⏰ Đã đặt lịch kiểm tra mỗi 1 phút...
💡 Nhấn Ctrl+C để dừng
```

### Khi phát hiện trang mở:
```
[2025-12-28 10:31:00] Đang kiểm tra trang web...
✅ TRANG WEB ĐÃ MỞ ĐĂNG KÝ!
📧 Đã gửi email thành công đến hungdangit95@gmail.com

============================================================
✅ ĐÃ PHÁT HIỆN TRANG MỞ VÀ GỬI THÔNG BÁO!
============================================================
```

## 📝 Tùy Chỉnh

### Thay đổi thông tin đăng nhập
Sửa `username` và `password` trong `config.json`

### Thay đổi thời gian kiểm tra
Sửa `check_interval_minutes` trong `config.json`:
- `0.5` = 30 giây
- `1` = 1 phút
- `5` = 5 phút

### Thay đổi URL
Sửa `login_url` hoặc `target_url` trong `config.json`

## 🔧 Chạy Trong Background (Windows)

### Sử dụng Task Scheduler:
1. Mở Task Scheduler
2. Create Basic Task
3. Trigger: At startup hoặc At log on
4. Action: Start a program
5. Program: `python`
6. Arguments: `D:\BuildProject\tools\check_registration.py`
7. Start in: `D:\BuildProject\tools`

### Hoặc chạy PowerShell ẩn:
```powershell
Start-Process python -ArgumentList "check_registration.py" -WindowStyle Hidden
```

## 🐛 Xử Lý Lỗi

### Lỗi kết nối:
- Kiểm tra internet
- Kiểm tra URL trong config

### Lỗi gửi email:
- Kiểm tra email/password trong config
- Đảm bảo đã tạo App Password (không dùng mật khẩu thường)
- Kiểm tra đã bật 2-Step Verification

### Tool không chạy:
```bash
pip install --upgrade -r requirements.txt
```

## 📧 Email Nhận Được

Khi phát hiện trang mở, bạn sẽ nhận email với nội dung:

**Subject:** 🎉 TRANG ĐĂNG KÝ ĐÃ MỞ - NAFIQAD

**Body:**
```
Xin chào!

Trang web đăng ký đã MỞ và có thể đăng ký được rồi!

⏰ Thời gian phát hiện: 2025-12-28 10:31:00

Hãy truy cập ngay để đăng ký!
```

## ⚠️ Lưu Ý

- Tool sẽ chạy liên tục cho đến khi bạn nhấn Ctrl+C
- Mỗi khi phát hiện trang mở, chỉ gửi 1 email duy nhất
- Nếu trang đóng rồi mở lại, sẽ gửi email mới
- Không spam, không gây quá tải server

## 📄 License

MIT License - Sử dụng tự do cho mục đích cá nhân

## 👤 Liên Hệ

Email: hungdangit95@gmail.com

---
**Chúc bạn đăng ký thành công! 🎉**

