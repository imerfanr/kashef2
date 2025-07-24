# کاشف - سیستم تشخیص ماینر پیشرفته
## Kashef - Advanced Cryptocurrency Miner Detection System

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/kashef/miner-detector)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://docker.com)

سیستم هوشمند و پیشرفته برای تشخیص ماینرهای ارزهای دیجیتال با استفاده از یادگیری ماشین، تحلیل شبکه، و حسگرهای سخت‌افزاری.

## 🚀 ویژگی‌های کلیدی

### 🧠 **هوش مصنوعی پیشرفته**
- **یادگیری ماشین:** RandomForestClassifier با بهینه‌سازی عملکرد
- **تحلیل انومالی:** IsolationForest برای تشخیص رفتارهای غیرعادی
- **ادغام xAI:** تحلیل پیشرفته با API گروک
- **یادگیری تطبیقی:** بازآموزی خودکار مدل با داده‌های جدید

### 🌐 **تشخیص شبکه هوشمند**
- **اسکن پیشرفته:** Nmap برای کشف دستگاه‌ها و سرویس‌ها
- **تحلیل پروتکل:** شناسایی Stratum و پروتکل‌های ماینینگ
- **تحلیل ترافیک:** بررسی الگوهای شبکه با Scapy
- **موقعیت‌یابی:** تشخیص موقعیت جغرافیایی با GeoIP2

### 🔧 **حسگرهای سخت‌افزاری**
- **سنسور دما:** DS18B20 برای تشخیص گرمای بیش‌ازحد
- **سیگنال RF:** RTL-SDR برای تحلیل امواج رادیویی
- **نویز صوتی:** میکروفون برای تشخیص صدای فن‌ها
- **مانیتورینگ بلادرنگ:** ذخیره و تحلیل داده‌های حسگرها

### 🛡️ **امنیت و کارایی**
- **رمزگذاری:** Fernet برای امنیت داده‌ها
- **احراز هویت:** JWT و session management
- **Rate Limiting:** محدودیت نرخ درخواست‌ها
- **Async Architecture:** عملکرد بالا با asyncio و aiohttp

### 📊 **مانیتورینگ و تصویرسازی**
- **داشبورد Grafana:** نمایش آمارها و نمودارها
- **Prometheus Metrics:** جمع‌آوری معیارهای عملکرد
- **نقشه‌های پویا:** Folium برای نمایش موقعیت ماینرها
- **هشدارهای Telegram:** اطلاع‌رسانی فوری

## 📋 پیش‌نیازها

### سیستم‌عامل پشتیبانی شده:
- Ubuntu 20.04+ / Debian 11+
- CentOS 8+ / RHEL 8+ / Fedora 35+
- Linux کرنل 6.12.8+

### نرم‌افزارهای مورد نیاز:
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Git

### سخت‌افزار توصیه شده:
- **CPU:** 4+ cores
- **RAM:** 8GB+
- **Storage:** 50GB+ SSD
- **Network:** Gigabit Ethernet

### حسگرهای اختیاری:
- **DS18B20:** سنسور دمای دیجیتال
- **RTL-SDR:** دونگل رادیو نرم‌افزاری
- **USB میکروفون:** برای تشخیص صدا

## 🚀 نصب سریع

### 1. دانلود پروژه
```bash
git clone https://github.com/kashef/miner-detector.git
cd miner-detector
```

### 2. اجرای اسکریپت نصب (توصیه شده)
```bash
sudo ./deploy.sh
```

### 3. نصب دستی

#### نصب وابستگی‌ها:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3-pip docker.io docker-compose postgresql-client redis-tools nmap

# CentOS/RHEL/Fedora
sudo dnf install -y python3.11 python3-pip docker docker-compose postgresql redis nmap
```

#### نصب کتابخانه‌های Python:
```bash
pip3 install -r requirements.txt
```

#### راه‌اندازی با Docker:
```bash
# کپی فایل تنظیمات
cp .env.example .env

# ویرایش متغیرهای محیطی
nano .env

# ساخت و اجرای کانتینرها
docker-compose up -d --build
```

## ⚙️ پیکربندی

### 1. تنظیمات پایه (.env)
```bash
# کلیدهای امنیتی (تولید خودکار در deployment)
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
ENCRYPTION_KEY=your-encryption-key

# پایگاه داده
POSTGRES_URL=postgresql://user:pass@localhost:5432/minerdb
REDIS_URL=redis://localhost:6379/0

# API keys
XAI_API_KEY=your-xai-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

### 2. تنظیمات حسگرها
```bash
# حسگر دما
TEMPERATURE_SENSOR_PORT=/dev/ttyUSB0

# RTL-SDR
RTL_SDR_FREQUENCY=433.92e6
RTL_SDR_GAIN=4

# میکروفون
AUDIO_DEVICE_INDEX=0
AUDIO_SAMPLE_RATE=44100
```

### 3. پیکربندی شبکه
```bash
# محدوده IP پیش‌فرض برای اسکن
DEFAULT_IP_RANGE=192.168.1.0/24

# پورت‌های مشکوک به ماینینگ
MINING_PORTS=3333,4444,1800,4028,8332,8333

# تنظیمات فایروال
ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
```

## 🔧 استفاده

### 1. راه‌اندازی سیستم
```bash
# شروع تمام سرویس‌ها
sudo systemctl start miner-detector

# بررسی وضعیت
sudo miner-detector-monitor

# مشاهده لاگ‌ها
sudo ./deploy.sh logs
```

### 2. دسترسی به رابط‌ها

#### رابط اصلی:
- **API:** http://localhost:8080
- **وضعیت سیستم:** http://localhost:8080/api/status
- **WebSocket:** ws://localhost:8080/ws

#### پنل‌های مانیتورینگ:
- **Grafana:** http://localhost:3000 (admin/password)
- **Prometheus:** http://localhost:9090

### 3. API های کلیدی

#### شروع اسکن شبکه:
```bash
curl -X POST http://localhost:8080/api/scan \
  -H "Content-Type: application/json" \
  -d '{"ip_range": "192.168.1.0/24"}'
```

#### دریافت دستگاه‌های شناسایی شده:
```bash
curl http://localhost:8080/api/devices?limit=100
```

#### آموزش مدل یادگیری ماشین:
```bash
curl -X POST http://localhost:8080/api/train
```

#### ارسال داده حسگر:
```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "temperature",
    "value": 75.5,
    "timestamp": "2024-01-20T10:30:00Z",
    "unit": "celsius",
    "device_id": "sensor_001"
  }'
```

### 4. استفاده از CLI

#### بررسی وضعیت:
```bash
./deploy.sh status
```

#### تهیه پشتیبان:
```bash
./deploy.sh backup
```

#### بازآورانی سیستم:
```bash
./deploy.sh restart
```

#### به‌روزرسانی:
```bash
./deploy.sh update
```

## 🧪 آزمایش عملکرد

### تست اتصال پایگاه داده:
```bash
docker exec miner_detector_db pg_isready -U mineruser -d minerdb
```

### تست Redis:
```bash
docker exec miner_detector_redis redis-cli ping
```

### تست API:
```bash
curl -f http://localhost:8080/api/status
```

### تست حسگرها:
```python
import requests

# تست داده حسگر
response = requests.post('http://localhost:8080/api/sensors', json={
    'sensor_type': 'temperature',
    'value': 45.2,
    'timestamp': '2024-01-20T10:00:00Z',
    'unit': 'celsius'
})
print(response.json())
```

## 📊 مانیتورینگ و نظارت

### 1. معیارهای کلیدی
- **miners_detected_total:** تعداد کل ماینرهای شناسایی شده
- **network_scan_duration_seconds:** زمان اسکن شبکه
- **active_sensors_count:** تعداد حسگرهای فعال
- **api_requests_total:** تعداد کل درخواست‌های API

### 2. هشدارهای Grafana
- **دمای بالا:** بیش از 80°C
- **استفاده بالای CPU:** بیش از 90%
- **ترافیک مشکوک:** الگوهای غیرعادی شبکه
- **خرابی حسگر:** عدم دریافت داده برای 5 دقیقه

### 3. لاگ‌ها
```bash
# لاگ‌های اصلی
tail -f /var/log/miner-detector/app.log

# لاگ‌های نظارت
tail -f /var/log/miner-detector/monitor.log

# لاگ‌های پشتیبان‌گیری
tail -f /var/log/miner-detector/backup.log
```

## 🔐 امنیت

### 1. بهترین روش‌ها
- کلیدهای رمزگذاری قوی تولید کنید
- دسترسی شبکه را محدود کنید
- پشتیبان‌گیری منظم انجام دهید
- لاگ‌ها را مرتب بررسی کنید

### 2. تنظیمات فایروال
```bash
# Ubuntu/Debian
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80,443,8080/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### 3. SSL/TLS
```bash
# نصب گواهی Let's Encrypt
sudo certbot --nginx -d yourdomain.com

# یا استفاده از گواهی خودامضا
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem -out ssl/fullchain.pem
```

## 🐛 عیب‌یابی

### مشکلات رایج:

#### 1. خطای اتصال به پایگاه داده
```bash
# بررسی وضعیت PostgreSQL
docker logs miner_detector_db

# بازنشانی پایگاه داده
docker-compose restart postgres
```

#### 2. مشکل حسگرها
```bash
# بررسی پورت‌های سریال
ls -la /dev/ttyUSB*

# تست RTL-SDR
rtl_test -t
```

#### 3. خطای Docker
```bash
# بررسی فضای دیسک
df -h

# پاکسازی کانتینرهای قدیمی
docker system prune -a
```

#### 4. مشکل عملکرد
```bash
# بررسی استفاده منابع
docker stats

# بررسی لاگ‌های سیستم
journalctl -u miner-detector
```

## 📈 بهینه‌سازی عملکرد

### 1. تنظیمات پایگاه داده
```sql
-- PostgreSQL optimization
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '64MB';
SELECT pg_reload_conf();
```

### 2. تنظیمات Redis
```bash
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
```

### 3. تنظیمات Python
```bash
# .env
MAX_WORKERS=8
REDIS_POOL_SIZE=50
HTTP_TIMEOUT=60
```

## 🔄 به‌روزرسانی

### به‌روزرسانی خودکار:
```bash
# اضافه کردن به crontab
0 3 * * 0 /opt/miner-detector/deploy.sh update >> /var/log/miner-detector/update.log 2>&1
```

### به‌روزرسانی دستی:
```bash
cd /opt/miner-detector
git pull origin main
./deploy.sh update
```

## 🤝 مشارکت

### راه‌های مشارکت:
1. **گزارش باگ:** Issues در GitHub
2. **پیشنهاد ویژگی:** Feature Requests
3. **کد:** Pull Requests
4. **مستندات:** بهبود README و docs

### استانداردهای کد:
```bash
# Code formatting
black miner_detector_optimized.py

# Type checking
mypy miner_detector_optimized.py

# Testing
pytest tests/
```

## 📄 مجوز

این پروژه تحت مجوز MIT منتشر شده است. فایل [LICENSE](LICENSE) را برای جزئیات بیشتر مطالعه کنید.

## 📞 پشتیبانی

### راه‌های تماس:
- **GitHub Issues:** [مشکلات و سوالات](https://github.com/kashef/miner-detector/issues)
- **ایمیل:** support@kashef.ai
- **تلگرام:** @KashefSupport

### مستندات اضافی:
- [راهنمای نصب](docs/installation.md)
- [مرجع API](docs/api-reference.md)
- [راهنمای حسگرها](docs/sensors.md)
- [عیب‌یابی پیشرفته](docs/troubleshooting.md)

---

**توجه:** این سیستم برای اهداف آموزشی و تحقیقاتی طراحی شده است. استفاده در محیط‌های تولیدی باید با احتیاط و رعایت قوانین محلی صورت گیرد.

## 🎯 نقشه راه

### نسخه 2.1 (Q2 2024):
- [ ] پشتیبانی از GPU miners
- [ ] تحلیل deep learning
- [ ] رابط موبایل
- [ ] API GraphQL

### نسخه 2.2 (Q3 2024):
- [ ] Multi-tenancy
- [ ] Cloud deployment
- [ ] Advanced ML models
- [ ] Real-time dashboard

### نسخه 3.0 (Q4 2024):
- [ ] Distributed scanning
- [ ] Blockchain integration
- [ ] AI-powered predictions
- [ ] Enterprise features

---

**Made with ❤️ by Kashef Team**
