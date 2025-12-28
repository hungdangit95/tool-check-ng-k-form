#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool tự động kiểm tra trang đăng ký NAFIQAD
Gửi email thông báo khi có thể đăng ký
"""

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import schedule
from datetime import datetime
from bs4 import BeautifulSoup
import json
import os
import sys
from urllib.parse import urljoin

# Fix encoding và unbuffered output trên Windows
if sys.platform == 'win32':
    import codecs
    # Unbuffered output để print realtime
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Monkey-patch print để tự động flush (realtime output)
import builtins
_original_print = builtins.print
def print(*args, **kwargs):
    """Print với flush tự động để hiển thị realtime"""
    kwargs.setdefault('flush', True)  # Tự động flush
    _original_print(*args, **kwargs)

# Thay thế builtin print
builtins.print = print


class RegistrationChecker:
    def __init__(self, config_file='config.json'):
        """Khởi tạo checker với config"""
        self.config = self.load_config(config_file)
        self.last_status = None
        self.email_sent = False
        self.session = requests.Session()  # Session để duy trì cookie
        self.is_logged_in = False
        
    def load_config(self, config_file):
        """Đọc config từ file JSON"""
        try:
            if os.path.exists(config_file):
                print(f"[INIT] Doc config tu: {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[INIT] Doc config thanh cong!")
                    return config
            else:
                print(f"[INIT] Khong tim thay {config_file}, dung config mac dinh")
        except Exception as e:
            print(f"[INIT] Loi khi doc config: {e}")
            print(f"[INIT] Dung config mac dinh")
            # Config mặc định
            return {
                "login_url": "https://nafiqpm1.vn/thanhvien/dangnhaptaikhoan",
                "login_api_url": "https://nafiqpm1.vn/thanhvien/checkdangnhap",
                "target_url": "https://nafiqpm1.vn/thanhvien/dangkylaymau",
                "username": "ctyvuongminh",
                "password": "hanoi1234@",
                "form_indicators": [
                    "Đăng ký lấy mẫu trái cây tươi",
                    "Tên mẫu",
                    "Ngày lấy mẫu",
                    "File đính kèm"
                ],
                "check_interval_minutes": 0.5,
                "email": {
                    "to": "npahuph@gmail.com, hungdangit95@gmail.com",
                    "from": "your_email@gmail.com",  # Cần điền email gửi
                    "password": "",  # Cần điền app password của Gmail
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587
                }
            }
    
    def login(self):
        """Đăng nhập vào hệ thống"""
        try:
            print(f"[LOGIN] Dang dang nhap voi user: {self.config['username']}...")
            
            # Lấy API URL từ config hoặc dùng mặc định
            login_api_url = self.config.get('login_api_url', 'https://nafiqpm1.vn/thanhvien/checkdangnhap')
            print(f"[LOGIN] Dang ket noi den: {login_api_url}...")
            
            # Dữ liệu đăng nhập theo format JSON
            login_data = {
                'user': self.config['username'],
                'pass': self.config['password']
            }
            
            # Headers cho POST request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json',
                'Referer': self.config.get('login_url', 'https://nafiqpm1.vn/thanhvien/dangnhaptaikhoan')
            }
            
            print(f"[LOGIN] POST den: {login_api_url}")
            print(f"[LOGIN] Data: {login_data}")
            print(f"[LOGIN] Dang gui POST request...")
            
            # POST request để đăng nhập với JSON data
            response = self.session.post(
                login_api_url,
                json=login_data,
                headers=headers,
                timeout=5,
                allow_redirects=True
            )
            
            print(f"[LOGIN] Response status: {response.status_code}")
            print(f"[LOGIN] Response URL: {response.url}")
            print(f"[LOGIN] Cookies: {len(self.session.cookies)} cookies")
            
            # Kiểm tra đăng nhập thành công
            if response.status_code == 200:
                # Kiểm tra response có thành công không
                # Thường API sẽ trả về JSON với status hoặc redirect
                try:
                    response_json = response.json()
                    print(f"[LOGIN] Response JSON: {response_json}")
                    # Nếu có status success hoặc có cookies thì coi như thành công
                    if len(self.session.cookies) > 0:
                        print("[LOGIN] Dang nhap thanh cong! (co cookies)")
                        self.is_logged_in = True
                        return True
                except:
                    # Nếu không phải JSON, kiểm tra cookies
                    if len(self.session.cookies) > 0:
                        print("[LOGIN] Dang nhap thanh cong! (co cookies)")
                        self.is_logged_in = True
                        return True
                    else:
                        print("[LOGIN] Khong co cookies - co the sai username/password")
                        print(f"[LOGIN] Response text: {response.text[:200]}")
                        return False
            else:
                print(f"[LOGIN] Loi dang nhap: Status code {response.status_code}")
                print(f"[LOGIN] Response text: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"[LOGIN] Loi khi dang nhap: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_website(self):
        """Kiểm tra trang web có form đăng ký không"""
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Dang kiem tra trang web...")
            
            # Đăng nhập nếu chưa đăng nhập
            if not self.is_logged_in:
                print("[CHECK] Chua dang nhap, dang nhap lai...")
                if not self.login():
                    print("[CHECK] Khong the dang nhap, thu lai lan sau...")
                    return None
            else:
                print("[CHECK] Da dang nhap, tiep tuc kiem tra...")
            
            # Gửi request đến trang đăng ký với session đã login
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.config['login_url']
            }
            
            print(f"[CHECK] GET: {self.config['target_url']}")
            print(f"[CHECK] Dang ket noi...")
            response = self.session.get(
                self.config['target_url'], 
                headers=headers,
                timeout=5
            )
            
            print(f"[CHECK] Response status: {response.status_code}")
            print(f"[CHECK] Response URL: {response.url}")
            
            if response.status_code != 200:
                print(f"[CHECK] Loi ket noi: Status code {response.status_code}")
                # Reset login nếu gặp lỗi 401/403
                if response.status_code in [401, 403]:
                    print("[CHECK] Session het han, reset login...")
                    self.is_logged_in = False
                return None
            
            # Parse HTML từ trang dangkylaymau
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Kiểm tra có bị redirect về trang login không
            if 'dangnhaptaikhoan' in response.url or 'Ten dang nhap' in page_text or 'Dang nhap' in page_text:
                print("[CHECK] Bi redirect ve trang login, dang nhap lai...")
                self.is_logged_in = False
                return None
            
            # Parse form đăng ký từ trang dangkylaymau
            print(f"[CHECK] Parse form tu trang: {response.url}")
            forms = soup.find_all('form')
            print(f"[CHECK] Tim thay {len(forms)} form(s) trong trang")
            
            # Tìm form đăng ký (form có các field đặc trưng)
            form_indicators = self.config.get('form_indicators', [
                "Đăng ký lấy mẫu trái cây tươi",
                "Tên mẫu",
                "Ngày lấy mẫu",
                "File đính kèm"
            ])
            
            # Kiểm tra trong text và trong form HTML
            found_indicators = []
            form_found = False
            
            # Kiểm tra text trong trang
            for indicator in form_indicators:
                if indicator in page_text:
                    found_indicators.append(indicator)
                    print(f"[CHECK] Tim thay text: {indicator}")
            
            # Kiểm tra form HTML có các input field đặc trưng không
            for form in forms:
                form_html = str(form).lower()
                # Tìm các field đặc trưng trong form
                if 'ten mau' in form_html or 'ngay lay mau' in form_html or 'file dinh kem' in form_html:
                    form_found = True
                    print(f"[CHECK] Tim thay form dang ky voi cac field can thiet!")
                    # Lấy action URL của form nếu có
                    if form.get('action'):
                        print(f"[CHECK] Form action: {form.get('action')}")
                    break
            
            found_count = len(found_indicators)
            
            # Nếu tìm thấy form HOẶC ít nhất 2/4 indicators thì coi như form đã xuất hiện
            if form_found or found_count >= 2:
                if form_found:
                    print(f"[CHECK] *** FORM DANG KY DA XUAT HIEN! (Tim thay form HTML) ***")
                else:
                    print(f"[CHECK] *** FORM DANG KY DA XUAT HIEN! (Tim thay {found_count}/{len(form_indicators)} yeu to) ***")
                return True
            else:
                print(f"[CHECK] Chua co form dang ky (Chi tim thay {found_count}/{len(form_indicators)} yeu to, khong co form HTML)")
                if found_count > 0:
                    print(f"[CHECK] Cac yeu to tim thay: {', '.join(found_indicators)}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[CHECK] Loi ket noi: {e}")
            return None
        except Exception as e:
            print(f"[CHECK] Loi: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def send_email(self):
        """Gửi email thông báo"""
        try:
            email_config = self.config['email']
            
            # Kiểm tra config email
            if not email_config.get('from') or not email_config.get('password'):
                print("⚠️ Chưa cấu hình email trong config.json")
                print("📧 THÔNG BÁO: Form đăng ký đã xuất hiện!")
                print(f"🔗 Truy cập ngay: {self.config['target_url']}")
                return False
            
            # Kiểm tra format App Password (thường là 16 ký tự, không có khoảng trắng)
            password = email_config.get('password', '').strip()
            if len(password) != 16 or ' ' in password:
                print("⚠️ CẢNH BÁO: Mật khẩu có vẻ không phải App Password!")
                print("📌 App Password của Gmail thường có 16 ký tự, không có khoảng trắng")
                print("📌 Hướng dẫn tạo App Password:")
                print("   1. Truy cập: https://myaccount.google.com/apppasswords")
                print("   2. Chọn 'Mail' và 'Other (Custom name)'")
                print("   3. Nhập tên: 'NAFIQAD Tool'")
                print("   4. Copy mật khẩu 16 ký tự (không có khoảng trắng)")
                print("   5. Dán vào config.json")
            
            # Tạo email
            msg = MIMEMultipart()
            msg['From'] = email_config['from']
            msg['To'] = email_config['to']
            msg['Subject'] = '🎉 FORM ĐĂNG KÝ ĐÃ XUẤT HIỆN - NAFIQAD'
            
            body = f"""
Xin chào!

Form đăng ký lấy mẫu trái cây tươi đã XUẤT HIỆN trên trang web!

🔗 Link: {self.config['target_url']}
⏰ Thời gian phát hiện: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 Hãy truy cập ngay để điền form và đăng ký!

Các thông tin cần chuẩn bị:
- Tên mẫu
- Ngày lấy mẫu
- File đính kèm (pdf, docx, xlsx)

---
Tool tự động check đăng ký NAFIQAD
Kiểm tra mỗi 30 giây
"""
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Gửi email qua Gmail
            print(f"[EMAIL] Dang ket noi den SMTP server...")
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            print(f"[EMAIL] Dang dang nhap voi email: {email_config['from']}...")
            server.login(email_config['from'], password)
            print(f"[EMAIL] Dang gui email den: {email_config['to']}...")
            server.send_message(msg)
            server.quit()
            
            print(f"📧 Đã gửi email thành công đến {email_config['to']}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ LỖI XÁC THỰC EMAIL: {e}")
            print("\n" + "="*60)
            print("🔧 HƯỚNG DẪN SỬA LỖI:")
            print("="*60)
            print("1. Đảm bảo đã BẬT 2-Step Verification:")
            print("   → https://myaccount.google.com/security")
            print("\n2. Tạo App Password (KHÔNG dùng mật khẩu Gmail thường):")
            print("   → https://myaccount.google.com/apppasswords")
            print("   → Chọn 'Mail' và 'Other (Custom name)'")
            print("   → Nhập tên: 'NAFIQAD Tool'")
            print("   → Copy mật khẩu 16 ký tự (dạng: xxxx xxxx xxxx xxxx)")
            print("   → Xóa tất cả khoảng trắng khi dán vào config.json")
            print("\n3. Kiểm tra lại trong config.json:")
            print(f"   - from: {email_config.get('from')}")
            print(f"   - password: {'*' * len(password)} (độ dài: {len(password)})")
            print("="*60)
            print("\n📧 THÔNG BÁO: Form đăng ký đã xuất hiện!")
            print(f"🔗 Truy cập ngay: {self.config['target_url']}")
            return False
        except Exception as e:
            print(f"⚠️ Lỗi khi gửi email: {e}")
            print("📧 THÔNG BÁO: Form đăng ký đã xuất hiện!")
            print(f"🔗 Truy cập ngay: {self.config['target_url']}")
            return False
    
    def check_and_notify(self):
        """Kiểm tra và gửi thông báo nếu cần"""
        is_open = self.check_website()
        
        if is_open is True and not self.email_sent:
            # Trang web đã mở và chưa gửi email
            self.send_email()
            self.email_sent = True
            print("\n" + "="*60)
            print("*** DA PHAT HIEN TRANG MO VA GUI THONG BAO! ***")
            print("="*60 + "\n")
        elif is_open is False:
            # Reset flag nếu trang đóng lại
            if self.email_sent:
                self.email_sent = False
        
        self.last_status = is_open
        print("-" * 60)
    
    def run(self):
        """Chạy tool kiểm tra định kỳ"""
        print("\n" + "="*60)
        print("TOOL KIEM TRA FORM DANG KY NAFIQAD")
        print("="*60)
        print(f"Login URL: {self.config['login_url']}")
        print(f"Target URL: {self.config['target_url']}")
        print(f"Username: {self.config['username']}")
        print(f"Email nhan thong bao: {self.config['email']['to']}")
        interval = self.config['check_interval_minutes']
        if interval < 1:
            print(f"Kiem tra moi: {int(interval * 60)} giay")
        else:
            print(f"Kiem tra moi: {interval} phut")
        print("="*60 + "\n")
        
        # Chạy ngay lần đầu
        print("Bat dau kiem tra lan dau tien...\n")
        self.check_and_notify()
        
        # Đặt lịch chạy định kỳ
        interval = self.config['check_interval_minutes']
        if interval < 1:
            # Dùng seconds cho interval < 1 phút
            interval_seconds = int(interval * 60)
            schedule.every(interval_seconds).seconds.do(self.check_and_notify)
            print(f"Da dat lich kiem tra moi {interval_seconds} giay...")
        else:
            schedule.every(interval).minutes.do(self.check_and_notify)
            print(f"Da dat lich kiem tra moi {interval} phut...")
        print("Nhan Ctrl+C de dung\n")
        print("Tool dang chay, cho den lan kiem tra tiep theo...\n")
        
        # Chạy vòng lặp
        loop_count = 0
        while True:
            schedule.run_pending()
            time.sleep(1)
            loop_count += 1
            # Hiển thị dấu hiệu tool đang chạy mỗi 10 giây
            if loop_count % 10 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Tool dang chay... (cho den lan kiem tra tiep theo)")


def main():
    """Hàm main"""
    try:
        print("="*60)
        print("DANG KHOI TAO TOOL...")
        print("="*60)
        start_time = time.time()
        
        checker = RegistrationChecker()
        
        init_time = time.time() - start_time
        print(f"Khoi tao thanh cong trong {init_time:.2f} giay!")
        print("="*60 + "\n")
        
        checker.run()
    except KeyboardInterrupt:
        print("\n\nDa dung tool. Tam biet!")
    except Exception as e:
        print(f"\nLoi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

