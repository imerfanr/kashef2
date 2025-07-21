import os
import subprocess
import sys
import requests
import zipfile
import io
import platform
import shutil
from pathlib import Path
import winreg
from dotenv import load_dotenv, set_key

# تنظیمات
LOG_FILE = os.path.join(os.path.expanduser("~"), "Documents", "setup_logs.txt")
MINER_DETECTOR_FILE = "miner_detector.py"
MAXMIND_DB = os.path.join(os.path.expanduser("~"), "Documents", "GeoIP2-City.mmdb")
NMAP_URL = "https://nmap.org/dist/nmap-7.95-setup.exe"
NMAP_INSTALLER = "nmap-7.95-setup.exe"
PYTHON_URL = "https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe"
PYTHON_INSTALLER = "python-3.9.13-amd64.exe"
ZADIG_URL = "https://github.com/pbatard/zadig/releases/download/v2.8/zadig-2.8.exe"
ZADIG_INSTALLER = "zadig-2.8.exe"

# لیست کتابخانه‌های مورد نیاز
REQUIRED_PACKAGES = [
    "requests", "flask", "flask-socketio", "pyrtlsdr", "pyaudio", "scikit-learn",
    "numpy", "pandas", "pyqt5", "paho-mqtt", "pyjwt", "python-telegram-bot",
    "aiocoap", "httpx", "cryptography", "python-dotenv", "scapy", "folium", "pywin32", "geoip2"
]

# لاگ‌گذاری
def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()}: {message}\n")
    print(message)

# بررسی وجود پایتون
def check_python():
    try:
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        if "Python 3.9" in version or "Python 3.10" in version or "Python 3.11" in version:
            log("پایتون نسخه مناسب نصب شده است: " + version)
            return True
        else:
            log("نسخه پایتون نامناسب است: " + version)
            return False
    except:
        log("پایتون یافت نشد.")
        return False

# دانلودbejrtall python
def install_python():
    log("دانلود پایتون...")
    response = requests.get(PYTHON_URL)
    with open(PYTHON_INSTALLER, "wb") as f:
        f.write(response.content)
    log("نصب پایتون...")
    subprocess.run([PYTHON_INSTALLER, "/quiet", "InstallAllUsers=1", "PrependPath=1"], check=True)
    os.remove(PYTHON_INSTALLER)
    log("پایتون نصب شد.")

# بررسی و نصب کتابخانه‌ها
def check_and_install_packages():
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
            log(f"کتابخانه {pkg} نصب شده است.")
        except ImportError:
            log(f"نصب کتابخانه {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# بررسی و نصب nmap
def check_and_install_nmap():
    try:
        subprocess.check_output(["nmap", "--version"])
        log("nmap نصب شده است.")
    except:
        log("دانلود nmap...")
        response = requests.get(NMAP_URL)
        with open(NMAP_INSTALLER, "wb") as f:
            f.write(response.content)
        log("نصب nmap...")
        subprocess.run([NMAP_INSTALLER, "/S"], check=True)
        os.remove(NMAP_INSTALLER)
        # افزودن nmap به PATH
        nmap_path = r"C:\Program Files (x86)\Nmap"
        add_to_path(nmap_path)
        log("nmap نصب شد.")

# بررسی و نصب درایور Zadig برای RTL-SDR
def check_and_install_zadig():
    zadig_path = r"C:\Program Files\Zadig\zadig.exe"
    if not os.path.exists(zadig_path):
        log("دانلود Zadig...")
        response = requests.get(ZADIG_URL)
        with open(ZADIG_INSTALLER, "wb") as f:
            f.write(response.content)
        log("نصب Zadig...")
        subprocess.run([ZADIG_INSTALLER, "/S"], check=True)
        os.remove(ZADIG_INSTALLER)
        log("Zadig نصب شد.")

# افزودن به PATH
def add_to_path(path):
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0, winreg.KEY_ALL_ACCESS)
        current_path, _ = winreg.QueryValueEx(key, "Path")
        if path not in current_path:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, current_path + ";" + path)
        winreg.CloseKey(key)
        os.environ["PATH"] = current_path + ";" + path
    except Exception as e:
        log(f"خطا در افزودن به PATH: {e}")

# بررسی و دانلود پایگاه داده MaxMind
def check_and_install_maxmind():
    if not os.path.exists(MAXMIND_DB):
        log("دانلود پایگاه داده MaxMind GeoIP2...")
        # فرض بر این است که کاربر حساب MaxMind دارد
        maxmind_url = "https://download.maxmind.com/app/geoip_download?edition_id=GeoIP2-City&license_key=YOUR_LICENSE_KEY&suffix=tar.gz"
        # کاربر باید لینک واقعی را جایگزین کند
        log("لطفاً فایل GeoIP2-City.mmdb را به صورت دستی دانلود و در Documents قرار دهید.")
        # برای دانلود خودکار، نیاز به کلید لایسنس MaxMind است
        # response = requests.get(maxmind_url)
        # with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
        #     tar.extract("GeoIP2-City.mmdb", path=os.path.dirname(MAXMIND_DB))

# بررسی وجود miner_detector.py
def check_miner_detector():
    if not os.path.exists(MINER_DETECTOR_FILE):
        log(f"فایل {MINER_DETECTOR_FILE} یافت نشد. لطفاً فایل را در پوشه فعلی قرار دهید.")
        sys.exit(1)

# اجرای برنامه اصلی
def run_miner_detector():
    try:
        log("اجرای برنامه miner_detector.py...")
        subprocess.run([sys.executable, MINER_DETECTOR_FILE], check=True)
    except Exception as e:
        log(f"خطا در اجرای برنامه: {e}")
        sys.exit(1)

# تابع اصلی راه‌انداز
def main():
    log("شروع فرآیند نصب پیش‌نیازها...")
    
    # بررسی و نصب پایتون
    if not check_python():
        install_python()
    
    # نصب کتابخانه‌ها
    check_and_install_packages()
    
    # نصب nmap
    check_and_install_nmap()
    
    # نصب Zadig
    check_and_install_zadig()
    
    # نصب پایگاه داده MaxMind
    check_and_install_maxmind()
    
    # بررسی وجود فایل miner_detector.py
    check_miner_detector()
    
    # اجرای برنامه
    run_miner_detector()

if __name__ == "__main__":
    main()