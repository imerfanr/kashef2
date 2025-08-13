# راه اندازی نسخه دسکتاپ شناساگر ماینر
# Miner Detector Desktop Setup Guide

## نمای کلی / Overview

این راهنما شما را در فرآیند ایجاد و نصب نسخه دسکتاپ برنامه شناساگر ماینر راهنمایی می‌کند.

This guide will walk you through the process of building and installing the desktop version of the Miner Detector application.

## پیش‌نیازها / Prerequisites

### سیستم‌عامل / Operating System
- Linux (Ubuntu, Debian, CentOS, etc.)
- Windows 10/11
- macOS 10.14+

### نرم‌افزارهای مورد نیاز / Required Software
- Python 3.8 یا بالاتر / Python 3.8 or higher
- pip (Python package installer)
- Git (اختیاری / optional)

### بررسی نصب پایتون / Check Python Installation
```bash
python3 --version
pip3 --version
```

## مراحل نصب / Installation Steps

### ۱. آماده‌سازی محیط / Environment Setup

```bash
# Clone or download the project
git clone <repository-url>
cd miner-detector

# Or if you have the files locally
cd /path/to/miner-detector
```

### ۲. ساخت فایل اجرایی / Build Executable

#### روش آسان / Easy Method
```bash
# Make the build script executable (Linux/macOS)
chmod +x build.sh

# Run the build script
./build.sh
```

#### روش دستی / Manual Method
```bash
# Run the Python build script directly
python3 build_desktop.py
```

### ۳. نصب برنامه / Install Application

#### Linux/macOS
```bash
# Run the installer script
./install_desktop.sh
```

#### Windows
```batch
REM Run the Windows installer
install_desktop.bat
```

## ساختار فایل‌ها / File Structure

پس از ساخت، فایل‌های زیر ایجاد می‌شوند:

After building, the following files are created:

```
project/
├── dist/
│   └── MinerDetector          # فایل اجرایی / Executable file
├── build/                     # فایل‌های موقت ساخت / Temporary build files
├── venv_desktop/              # محیط مجازی / Virtual environment
├── build_desktop.py           # اسکریپت ساخت / Build script
├── miner_detector_desktop.spec # تنظیمات PyInstaller
├── desktop_requirements.txt   # وابستگی‌های دسکتاپ / Desktop dependencies
├── install_desktop.sh         # نصب‌کننده Linux/macOS
└── install_desktop.bat        # نصب‌کننده Windows / Windows installer
```

## استفاده از برنامه / Using the Application

### اجرای مستقیم / Direct Execution
```bash
# Run from dist directory
./dist/MinerDetector
```

### اجرای از منوی دسکتاپ / Desktop Menu
پس از نصب، برنامه در منوی برنامه‌ها و دسکتاپ در دسترس خواهد بود.

After installation, the application will be available in the applications menu and desktop.

## ویژگی‌های نسخه دسکتاپ / Desktop Features

- ✅ رابط گرافیکی PyQt5 / PyQt5 GUI interface
- ✅ شناسایی خودکار ماینر / Automatic miner detection
- ✅ نمایش داده‌های سنسور / Sensor data visualization
- ✅ ذخیره تنظیمات / Settings persistence
- ✅ گزارش‌گیری / Reporting functionality
- ✅ اتصال به شبکه / Network connectivity
- ✅ پشتیبانی از چندین پلتفرم / Multi-platform support

## عیب‌یابی / Troubleshooting

### مشکلات رایج / Common Issues

#### خطای وابستگی / Dependency Error
```bash
# Install missing system packages (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3-dev python3-pip build-essential

# Install missing system packages (CentOS/RHEL)
sudo yum install python3-devel python3-pip gcc
```

#### خطای PyQt5 در Linux / PyQt5 Error on Linux
```bash
# Install Qt5 development packages
sudo apt-get install qt5-default qttools5-dev-tools

# Or for newer Ubuntu versions
sudo apt-get install qtbase5-dev qttools5-dev-tools
```

#### خطای صوتی / Audio Error
```bash
# Install audio development packages
sudo apt-get install portaudio19-dev python3-pyaudio
```

#### خطای دسترسی سریال / Serial Access Error
```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER
# Logout and login again
```

### لاگ‌های خطا / Error Logs
لاگ‌های ساخت در فایل `build.log` ذخیره می‌شوند.

Build logs are saved in `build.log` file.

## تنظیمات پیشرفته / Advanced Configuration

### سفارسی‌سازی ساخت / Build Customization

فایل `miner_detector_desktop.spec` را ویرایش کنید:

Edit the `miner_detector_desktop.spec` file:

```python
# Add custom icon
exe = EXE(
    # ...
    icon='path/to/icon.ico',  # Add your icon
    # ...
)

# Add additional data files
datas=[
    ('custom_file.txt', '.'),
    ('config/', 'config/'),
],
```

### متغیرهای محیطی / Environment Variables

برای تنظیمات خاص، فایل `.env` ایجاد کنید:

Create a `.env` file for specific configurations:

```env
# API Configuration
TELEGRAM_TOKEN=your_telegram_token
MQTT_BROKER=your_mqtt_broker
REDIS_URL=redis://localhost:6379

# Detection Settings
DETECTION_SENSITIVITY=high
LOG_LEVEL=info
```

## پشتیبانی / Support

### گزارش مشکل / Report Issues
- مشکلات را در بخش Issues گزارش دهید
- Report issues in the Issues section

### مستندات / Documentation
- راهنمای کامل در فایل README.md
- Complete guide in README.md file

### تماس / Contact
- ایمیل پشتیبانی / Support email: support@example.com
- مستندات آنلاین / Online docs: https://docs.example.com

## لایسنس / License

این پروژه تحت لایسنس MIT منتشر شده است.

This project is released under the MIT License.

---

## نکات امنیتی / Security Notes

⚠️ **هشدار / Warning**: 
- برنامه نیاز به دسترسی‌های سیستمی دارد
- The application requires system-level access
- فقط از منابع معتبر دانلود کنید
- Only download from trusted sources
- فایروال و آنتی‌ویروس خود را بررسی کنید
- Check your firewall and antivirus settings

## به‌روزرسانی / Updates

برای دریافت آخرین نسخه:

To get the latest version:

```bash
git pull origin main
./build.sh
```

یا فایل‌های جدید را جایگزین کنید و مجدداً ساخت دهید.

Or replace the files and rebuild.