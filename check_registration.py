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
import pickle
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
        self.cookies_file = 'session_cookies.pkl'
        self.load_session()
        
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
                    "Tên mẫu"
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
    
    def save_session(self):
        """Lưu session cookies vào file"""
        try:
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(self.session.cookies, f)
            print(f"[SESSION] Đã lưu session vào {self.cookies_file}")
        except Exception as e:
            print(f"[SESSION] Lỗi khi lưu session: {e}")
    
    def load_session(self):
        """Tải session cookies từ file"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    self.session.cookies.update(cookies)
                print(f"[SESSION] Đã tải {len(cookies)} cookies từ {self.cookies_file}")
                # Kiểm tra session còn hợp lệ không
                self.verify_session()
            else:
                print(f"[SESSION] Chưa có file session {self.cookies_file}")
        except Exception as e:
            print(f"[SESSION] Lỗi khi tải session: {e}")
    
    def verify_session(self):
        """Kiểm tra session còn hợp lệ không"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = self.session.get(self.config['target_url'], headers=headers, timeout=5)
            
            # Nếu không bị redirect về login thì session còn hợp lệ
            if 'dangnhaptaikhoan' not in response.url and 'Dang nhap' not in response.text:
                print("[SESSION] Session còn hợp lệ, không cần đăng nhập lại")
                self.is_logged_in = True
            else:
                print("[SESSION] Session đã hết hạn")
                self.is_logged_in = False
        except Exception as e:
            print(f"[SESSION] Lỗi khi kiểm tra session: {e}")
            self.is_logged_in = False
    
    def login(self):
        """Đăng nhập vào hệ thống"""
        try:
            print(f"[LOGIN] Dang dang nhap voi user: {self.config['username']}...")
            
            # Bước 1: Truy cập trang login trước để lấy session/cookies
            login_page_url = self.config.get('login_url', 'https://nafiqpm1.vn/thanhvien/dangnhaptaikhoan')
            print(f"[LOGIN] Buoc 1: Truy cap trang login: {login_page_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # GET trang login để lấy session
            login_page_response = self.session.get(login_page_url, headers=headers, timeout=5)
            print(f"[LOGIN] Trang login status: {login_page_response.status_code}")
            print(f"[LOGIN] Cookies sau khi truy cap trang login: {len(self.session.cookies)}")
            
            # Bước 2: Thử cả form-based và JSON API
            login_api_url = self.config.get('login_api_url', 'https://nafiqpm1.vn/thanhvien/checkdangnhap')
            print(f"[LOGIN] Buoc 2: Thu form-based login den: {login_api_url}")
            
            # Thử form-based login trước
            login_data = {
                'user': self.config['username'],
                'pass': self.config['password']
            }
            
            # Headers cho form POST
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': login_page_url
            })
            
            print(f"[LOGIN] Thu form-based POST...")
            response = self.session.post(
                login_api_url,
                data=login_data,  # Dùng data thay vì json
                headers=headers,
                timeout=5,
                allow_redirects=True
            )
            
            print(f"[LOGIN] Form-based response status: {response.status_code}")
            print(f"[LOGIN] Response URL: {response.url}")
            print(f"[LOGIN] Cookies sau form-based: {len(self.session.cookies)}")
            
            # Nếu form-based không thành công, thử JSON
            if len(self.session.cookies) == 0 or response.status_code != 200:
                print(f"[LOGIN] Thu JSON API...")
                headers['Content-Type'] = 'application/json'
                
                response = self.session.post(
                    login_api_url,
                    json=login_data,
                    headers=headers,
                    timeout=5,
                    allow_redirects=True
                )
                print(f"[LOGIN] JSON response status: {response.status_code}")
                print(f"[LOGIN] Cookies sau JSON: {len(self.session.cookies)}")
            
            # In chi tiết cookies để debug
            for cookie in self.session.cookies:
                print(f"[LOGIN] Cookie: {cookie.name}={cookie.value[:20]}...")
            
            # Kiểm tra đăng nhập thành công bằng cách kiểm tra response
            login_success = False
            
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    print(f"[LOGIN] Response JSON: {response_json}")
                    # Kiểm tra response có thông báo thành công không
                    if isinstance(response_json, dict):
                        if response_json.get('success') or response_json.get('status') == 'success':
                            login_success = True
                        elif 'không đúng' in str(response_json).lower() or 'sai' in str(response_json).lower():
                            print("[LOGIN] Tên đăng nhập hoặc mật khẩu không đúng")
                            return False
                except:
                    response_text = response.text[:500]
                    print(f"[LOGIN] Response text: {response_text}")
                    # Kiểm tra có thông báo lỗi không
                    if 'không đúng' in response_text.lower() or 'sai' in response_text.lower():
                        print("[LOGIN] Tên đăng nhập hoặc mật khẩu không đúng")
                        return False
                    # Nếu có cookies và không có thông báo lỗi thì coi như thành công
                    if len(self.session.cookies) > 0:
                        login_success = True
            
            if login_success or (response.status_code == 200 and len(self.session.cookies) > 0):
                print("[LOGIN] Đăng nhập thành công!")
                self.is_logged_in = True
                self.save_session()
                return True
            else:
                print(f"[LOGIN] Đăng nhập thất bại: Status {response.status_code}, Cookies: {len(self.session.cookies)}")
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
            
            # Đăng nhập nếu chưa đăng nhập hoặc session hết hạn
            if not self.is_logged_in:
                print("[CHECK] Chưa đăng nhập hoặc session hết hạn, đăng nhập lại...")
                if not self.login():
                    print("[CHECK] Không thể đăng nhập, thử lại lần sau...")
                    return None
            else:
                print("[CHECK] Đã đăng nhập, tiếp tục kiểm tra...")
            
            # Gửi request đến trang đăng ký với session đã login
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': self.config['login_url']
            }
            print("file la:",self.config['target_url'])
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
            
            # Debug: Hiển thị URL và một phần nội dung để đảm bảo đúng trang
            print(f"[CHECK] Dang kiem tra noi dung tu URL: {response.url}")
            print(f"[CHECK] Noi dung trang (100 ky tu dau): {page_text[:100].strip()}")
            
            # Kiểm tra có bị redirect về trang login không
            if ('dangnhaptaikhoan' in response.url or 
                'Tên đăng nhập' in page_text or 
                'Đăng nhập' in page_text or
                'Vui lòng nhập tên đăng nhập' in page_text):
                print("[CHECK] Bị redirect về trang login hoặc chưa đăng nhập thành công...")
                self.is_logged_in = False
                # Xóa file session cũ
                if os.path.exists(self.cookies_file):
                    os.remove(self.cookies_file)
                    print("[CHECK] Đã xóa session cũ")
                return None
            
            # Parse form đăng ký từ trang dangkylaymau
            print(f"[CHECK] Parse form tu trang: {response.url}")
            forms = soup.find_all('form')
            print(f"[CHECK] Tim thay {len(forms)} form(s) trong trang")
            
            # Chỉ cần tìm "Tên mẫu" là gửi mail
            target_text = "Tên mẫu"
            # Kiểm tra text trong trang
            if target_text in page_text:
                print(f"[CHECK] *** FORM ĐĂNG KÝ ĐÃ XUẤT HIỆN! (Tìm thấy: {target_text}) ***")
                return True
            else:
                print(f"[CHECK] Chưa có form đăng ký (Không tìm thấy: {target_text})")
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

