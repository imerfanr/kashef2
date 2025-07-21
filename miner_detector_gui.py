
import json
import os
import subprocess
import time
import threading
import re
import socket
import asyncio
import requests
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import serial
from rtlsdr import RtlSdr
import pyaudio
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import jwt
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMenuBar, QAction
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer
from scapy.all import sniff
from telegram import Bot
from aiocoap import *
from httpx import AsyncClient
from cryptography.fernet import Fernet
import folium
from folium.plugins import MarkerCluster
from dotenv import load_dotenv, set_key
import win32com.client
import psutil
import serial.tools.list_ports
import geoip2.database
import whois
import sys

# بارگذاری متغیرهای محیطی
load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# تنظیمات
sensor_status = {"thermal": False, "rf": False, "sound": False}
sensor_data = {"thermal": [], "rf": [], "sound": []}
logs = []
data_file = os.path.join(os.path.expanduser("~"), "Documents", "miner_data.csv")
map_file = os.path.join(os.path.expanduser("~"), "Documents", "miner_map.html")
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "miner/detector"
XAI_API_KEY = os.getenv("XAI_API_KEY", "xai-9PhOVnjlR1GbZ9r7ahcjxb0mpyMwDUKg8kvvySFlARmCN30MIQwFyxZvlBJuXYKMdpGDQwBx3uX9mxde")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7391505668:AAHIk1c5zW2B5o0zN1HKB2WHzxG3yL5X6S8")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002230229470")
JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(32).hex())
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "your_email@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")
MAXMIND_DB = os.path.join(os.path.expanduser("~"), "Documents", "GeoIP2-City.mmdb")
XAI_API_URL = "https://api.x.ai/v1/grok"
model = RandomForestClassifier(n_estimators=100, random_state=42)
model_trained = False
JWT_ALGORITHM = "HS256"

# ذخیره کلیدها در .env
def save_env_keys():
    env_file = os.path.join(os.path.expanduser("~"), ".env")
    set_key(env_file, "XAI_API_KEY", XAI_API_KEY)
    set_key(env_file, "TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    set_key(env_file, "TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)
    set_key(env_file, "JWT_SECRET", JWT_SECRET)
    set_key(env_file, "EMAIL_ADDRESS", EMAIL_ADDRESS)
    set_key(env_file, "EMAIL_PASSWORD", EMAIL_PASSWORD)

# تنظیم خودکار پیش‌نیازها
def setup_system():
    logs.append("شروع تنظیم خودکار سامانه...")
    try:
        # نصب کتابخانه‌ها
        required_packages = [
            "requests", "flask", "flask-socketio", "pyrtlsdr", "pyaudio", "scikit-learn",
            "numpy", "pandas", "pyqt5", "paho-mqtt", "pyjwt", "python-telegram-bot",
            "aiocoap", "httpx", "cryptography", "python-dotenv", "scapy", "folium", "pywin32", "geoip2"
        ]
        for pkg in required_packages:
            try:
                subprocess.check_call(["pip", "install", pkg])
                logs.append(f"نصب {pkg} با موفقیت انجام شد.")
            except Exception as e:
                logs.append(f"خطا در نصب {pkg}: {e}")

        # بررسی nmap
        try:
            subprocess.check_output(["nmap", "--version"])
            logs.append("nmap نصب شده است.")
        except:
            logs.append("nmap یافت نشد. لطفاً از https://nmap.org/download.html نصب کنید.")

        # بررسی پورت‌های COM برای DS18B20
        ports = list(serial.tools.list_ports.comports())
        if ports:
            logs.append(f"پورت‌های COM یافت‌شده: {[p.device for p in ports]}")
        else:
            logs.append("هیچ پورت COM یافت نشد. لطفاً مبدل USB-to-TTL را بررسی کنید.")

        # بررسی RTL-SDR
        try:
            sdr = RtlSdr()
            sdr.close()
            logs.append("RTL-SDR شناسایی شد.")
        except:
            logs.append("RTL-SDR شناسایی نشد. لطفاً درایور WinUSB را با Zadig نصب کنید.")

        # تنظیم میکروفون
        try:
            p = pyaudio.PyAudio()
            p.terminate()
            logs.append("میکروفون شناسایی شد.")
        except:
            logs.append("میکروفون شناسایی نشد. لطفاً تنظیمات صدا را بررسی کنید.")

        # بررسی پایگاه داده MaxMind
        if not os.path.exists(MAXMIND_DB):
            logs.append(f"پایگاه داده MaxMind یافت نشد. لطفاً GeoIP2-City.mmdb را در {MAXMIND_DB} قرار دهید.")

        logs.append("تنظیم خودکار سامانه با موفقیت انجام شد.")
    except Exception as e:
        logs.append(f"خطا در تنظیم سامانه: {e}")

# شبیه‌سازی داده‌های واقعی
def generate_sample_data():
    data = []
    np.random.seed(42)
    for _ in range(100):  # 100 نمونه ماینر
        data.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": f"192.168.1.{np.random.randint(1, 255)}",
            "mac": f"00:1A:2B:{np.random.randint(10,99)}:{np.random.randint(10,99)}:{np.random.randint(10,99)}",
            "hostname": f"miner{random.randint(1,100)}.local",
            "isp": "Sample ISP",
            "org": "Mining Corp",
            "owner": f"Miner Owner {random.randint(1,100)}",
            "lat": np.random.uniform(35.6, 35.8),
            "lon": np.random.uniform(51.3, 51.5),
            "ports": "3333/tcp open, 4444/tcp open",
            "ports_count": np.random.randint(1, 4),
            "temp": np.random.uniform(30, 50),
            "rf": np.random.uniform(0.5, 2.0),
            "sound": np.random.uniform(60, 80),
            "is_miner": 1
        })
    for _ in range(100):  # 100 نمونه غیر ماینر
        data.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": f"192.168.1.{np.random.randint(1, 255)}",
            "mac": f"00:1A:2B:{np.random.randint(10,99)}:{np.random.randint(10,99)}:{np.random.randint(10,99)}",
            "hostname": f"device{random.randint(1,100)}.local",
            "isp": "Sample ISP",
            "org": "Non-Mining Org",
            "owner": f"User {random.randint(1,100)}",
            "lat": np.random.uniform(35.6, 35.8),
            "lon": np.random.uniform(51.3, 51.5),
            "ports": "No ports open",
            "ports_count": 0,
            "temp": np.random.uniform(20, 25),
            "rf": np.random.uniform(0.0, 0.3),
            "sound": np.random.uniform(30, 40),
            "is_miner": 0
        })
    df = pd.DataFrame(data)
    df.to_csv(data_file, mode='w', index=False)
    encrypt_file(data_file)
    logs.append("200 نمونه داده شبیه‌سازی‌شده ذخیره شدند.")

# خواندن دما از DS18B20
def read_temperature(com_port=None):
    if not com_port:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        com_port = ports[0] if ports else "COM3"
    try:
        ser = serial.Serial(com_port, 9600, timeout=1)
        ser.write(b"READ_TEMP\n")
        time.sleep(0.75)
        temp = ser.readline().decode().strip()
        ser.close()
        return float(temp) if temp else None
    except Exception as e:
        logs.append(f"خطا در خواندن DS18B20: {e}")
        return None

# خواندن سیگنال RF
def read_rf():
    try:
        sdr = RtlSdr()
        sdr.sample_rate = 2.4e6
        sdr.center_freq = 433.92e6
        sdr.gain = 4
        samples = sdr.read_samples(256*1024)
        sdr.close()
        return float(np.abs(np.mean(samples)))
    except Exception as e:
        logs.append(f"خطا در خواندن RTL-SDR: {e}")
        return None

# خواندن نویز صوتی
def read_sound():
    try:
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        data = stream.read(CHUNK)
        stream.stop_stream()
        stream.close()
        p.terminate()
        samples = np.frombuffer(data, dtype=np.int16)
        return float(20 * np.log10(np.sqrt(np.mean(samples**2))))
    except Exception as e:
        logs.append(f"خطا در خواندن حسگر صوتی: {e}")
        return None

# اسکن شبکه پیشرفته
def advanced_network_scan(ip_range):
    try:
        logs.append(f"شروع اسکن شبکه برای محدوده {ip_range}...")
        process = subprocess.run(["nmap", "-sS", "-p-", "--open", "-sV", ip_range], capture_output=True, text=True, timeout=300)
        nmap_result = process.stdout
        devices = []
        ip_pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        current_ip = None
        for line in nmap_result.split("\n"):
            if "Nmap scan report for" in line:
                ip = re.search(ip_pattern, line)
                if ip:
                    current_ip = ip.group(0)
                    devices.append({"ip": current_ip, "ports": "", "services": []})
            if "open" in line.lower() and current_ip:
                devices[-1]["ports"] += line + "; "
                if "tcp" in line:
                    service = re.search(r"(\d+)/tcp\s+open\s+(\S+)", line)
                    if service:
                        devices[-1]["services"].append({"port": service.group(1), "service": service.group(2)})
        return devices
    except Exception as e:
        logs.append(f"خطا در اسکن شبکه: {e}")
        return []

# جمع‌آوری اطلاعات خصوصی دستگاه
def collect_device_info(ip):
    info = {"ip": ip, "mac": "", "hostname": "", "isp": "", "org": "", "owner": "", "lat": None, "lon": None, "address": ""}
    try:
        # دریافت MAC
        arp_result = subprocess.run(["arp", "-a", ip], capture_output=True, text=True)
        mac_match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", arp_result.stdout)
        if mac_match:
            info["mac"] = mac_match.group(0)

        # دریافت hostname
        try:
            info["hostname"] = socket.gethostbyaddr(ip)[0]
        except:
            info["hostname"] = "N/A"

        # اطلاعات جغرافیایی با MaxMind
        if os.path.exists(MAXMIND_DB):
            reader = geoip2.database.Reader(MAXMIND_DB)
            try:
                response = reader.city(ip)
                info.update({
                    "isp": response.traits.isp or "N/A",
                    "org": response.traits.organization or "N/A",
                    "lat": response.location.latitude,
                    "lon": response.location.longitude,
                    "address": f"{response.city.name}, {response.subdivisions.most_specific.name}, {response.country.name}"
                })
            except:
                pass
            reader.close()

        # اطلاعات WHOIS
        try:
            w = whois.whois(ip)
            info["org"] = w.get("org", info["org"])
            info["owner"] = w.get("registrar", "N/A")
        except:
            pass

        # اطلاعات ip-api.com به‌عنوان پشتیبان
        try:
            response = requests.get(f"https://ip-api.com/json/{ip}?fields=status,country,city,lat,lon,isp,org")
            geo_data = response.json()
            if geo_data["status"] == "success":
                info["isp"] = info["isp"] or geo_data.get("isp", "N/A")
                info["org"] = info["org"] or geo_data.get("org", "N/A")
                info["lat"] = info["lat"] or geo_data.get("lat")
                info["lon"] = info["lon"] or geo_data.get("lon")
                info["address"] = info["address"] or f"{geo_data.get('city', 'N/A')}, {geo_data.get('country', 'N/A')}"
        except:
            pass

        return info
    except Exception as e:
        logs.append(f"خطا در جمع‌آوری اطلاعات دستگاه {ip}: {e}")
        return info

# اسکن پروتکل Stratum
def scan_mining_protocol(ip, port=3333):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        if result == 0:
            sock.send(b'{"id":1,"method":"mining.subscribe","params":["MinerDetector/1.0"]}\n')
            response = sock.recv(1024).decode()
            sock.close()
            return "mining.subscribe" in response
        sock.close()
        return False
    except Exception as e:
        logs.append(f"خطا در اسکن پروتکل Stratum برای {ip}: {e}")
        return False

# تحلیل ترافیک برای شناسایی Poolهای ماینینگ
def analyze_traffic(ip):
    try:
        packets = sniff(filter=f"host {ip}", count=100, timeout=30)
        tcp_packets = [p for p in packets if p.haslayer("TCP")]
        mining_pools = ["antpool.com", "f2pool.com", "poolin.com", "slushpool.com"]
        for pkt in tcp_packets:
            if pkt.haslayer("Raw"):
                payload = pkt["Raw"].load.decode(errors="ignore")
                for pool in mining_pools:
                    if pool in payload.lower():
                        return {"is_mining": True, "pool": pool}
        return {"is_mining": len(tcp_packets) > 50, "pool": None}
    except Exception as e:
        logs.append(f"خطا در تحلیل ترافیک برای {ip}: {e}")
        return {"is_mining": False, "pool": None}

# جمع‌آوری داده‌ها
def collect_data(ip, ports, temp, rf, sound, is_miner, device_info, mining_pool):
    try:
        ports_count = len(re.findall(r"open", ports, re.IGNORECASE))
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip,
            "mac": device_info["mac"],
            "hostname": device_info["hostname"],
            "isp": device_info["isp"],
            "org": device_info["org"],
            "owner": device_info["owner"],
            "lat": device_info["lat"],
            "lon": device_info["lon"],
            "address": device_info["address"],
            "ports": ports,
            "ports_count": ports_count,
            "temp": temp or 0,
            "rf": rf or 0,
            "sound": sound or 0,
            "mining_pool": mining_pool or "N/A",
            "is_miner": is_miner
        }
        df = pd.DataFrame([data])
        df.to_csv(data_file, mode='a', header=not os.path.exists(data_file), index=False)
        encrypt_file(data_file)
    except Exception as e:
        logs.append(f"خطا در جمع‌آوری داده‌ها: {e}")

# رمزنگاری فایل
def encrypt_file(file_path):
    try:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        with open(file_path, "rb") as f:
            data = f.read()
        encrypted = fernet.encrypt(data)
        with open(file_path + ".enc", "wb") as f:
            f.write(encrypted)
        return key
    except Exception as e:
        logs.append(f"خطا در رمزنگاری: {e}")
        return None

# آموزش مدل
def train_model():
    global model_trained
    try:
        if not os.path.exists(data_file):
            generate_sample_data()
        df = pd.read_csv(data_file)
        X = df[["temp", "rf", "sound", "ports_count"]]
        y = df["is_miner"]
        if len(X) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model.fit(X_train, y_train)
            score = model.score(X_test, y_test)
            model_trained = True
            logs.append(f"مدل با {len(X)} نمونه آموزش داده شد. دقت: {score:.2f}")
        else:
            logs.append("نمونه‌های کافی برای آموزش وجود ندارد.")
    except Exception as e:
        logs.append(f"خطا در آموزش مدل: {e}")

# تحلیل با xAI API
async def analyze_with_xai(data):
    try:
        async with AsyncClient(http2=True) as client:
            headers = {"Authorization": f"Bearer {XAI_API_KEY}"}
            response = await client.post(XAI_API_URL, headers=headers, json={"query": json.dumps(data)})
            result = response.json().get("result", "تحلیل انجام نشدcoloap://localhost/sensorsد")
            is_miner = 1 if "ماینر" in result.lower() else 0
            return result, is_miner
    except Exception as e:
        logs.append(f"خطا در تحلیل xAI: {e}")
        return f"خطا: {e}", 0

# ارسال هشدار
async def send_alert(message):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logs.append(f"هشدار ارسال شد: {message}")
    except Exception as e:
        logs.append(f"خطا در ارسال هشدار: {e}")

# ایجاد نقشه پویا
def create_dynamic_map(devices):
    try:
        m = folium.Map(location=[35.7, 51.4], zoom_start=12)  # مرکز تهران
        marker_cluster = MarkerCluster().add_to(m)
        for device in devices:
            if device["lat"] and device["lon"]:
                popup = (f"IP: {device['ip']}<br>"
                         f"MAC: {device['mac']}<br>"
                         f"Hostname: {device['hostname']}<br>"
                         f"ISP: {device['isp']}<br>"
                         f"Org: {device['org']}<br>"
                         f"Owner: {device['owner']}<br>"
                         f"Address: {device['address']}<br>"
                         f"Ports: {device['ports']}<br>"
                         f"Mining Pool: {device['mining_pool']}<br>"
                         f"Miner: {'بله' if device['is_miner'] else 'خیر'}")
                folium.Marker(
                    location=[device["lat"], device["lon"]],
                    popup=popup,
                    icon=folium.Icon(color="red" if device["is_miner"] else "blue")
                ).add_to(marker_cluster)
        m.save(map_file)
        logs.append(f"نقشه پویا در {map_file} ذخیره شد.")
    except Exception as e:
        logs.append(f"خطا در ایجاد نقشه: {e}")

# بررسی حسگرها
def check_sensors():
    while True:
        try:
            temp = read_temperature()
            rf = read_rf()
            sound = read_sound()
            sensor_status["thermal"] = bool(temp)
            sensor_status["rf"] = bool(rf)
            sensor_status["sound"] = bool(sound)
            if temp:
                sensor_data["thermal"].append(temp)
            if rf:
                sensor_data["rf"].append(rf)
            if sound:
                sensor_data["sound"].append(sound)
            socketio.emit('sensor_status', sensor_status)
            socketio.emit('sensor_data', sensor_data)
            mqtt_client.publish(MQTT_TOPIC, json.dumps(sensor_data))
            threading.Thread(target=lambda: asyncio.run(coap_send(sensor_data))).start()
        except Exception:
            pass
        time.sleep(60)

# ارسال به CoAP
async def coap_send(data):
    try:
        protocol = await Context.create_client_context()
        request = Message(code=POST, uri="coap://localhost/sensors", payload=json.dumps(data).encode())
        response = await protocol.request(request).response
        logs.append(f"CoAP response: {response.payload.decode()}")
    except Exception as e:
        logs.append(f"خطا در CoAP: {e}")

# رابط گرافیکی
class MinerDetectorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تشخیص و مکان‌یابی ماینر")
        self.setGeometry(100, 100, 1000, 700)
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # منوی اصلی
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)
        self.setup_menus()

        self.ip_label = QLabel("محدوده IP (مثال: 192.168.1.0/24):")
        self.ip_input = QLineEdit()
        self.scan_button = QPushButton("اسکن شبکه")
        self.scan_button.clicked.connect(self.scan_network)
        self.chat_output = QTextEdit()
        self.chat_output.setReadOnly(True)
        self.sensor_output = QTextEdit()
        self.sensor_output.setReadOnly(True)
        self.map_view = QWebEngineView()
        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.scan_button)
        layout.addWidget(QLabel("نتایج اسکن و تحلیل:"))
        layout.addWidget(self.chat_output)
        layout.addWidget(QLabel("داده‌های حسگرها:"))
        layout.addWidget(self.sensor_output)
        layout.addWidget(QLabel("نقشه پویا:"))
        layout.addWidget(self.map_view)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sensors)
        self.timer.start(60000)
        self.update_map()

    def setup_menus(self):
        sensor_menu = self.menu_bar.addMenu("تنظیم حسگرها")
        ds18b20_action = QAction("DS18B20", self)
        ds18b20_action.triggered.connect(lambda: self.show_info("DS18B20"))
        sensor_menu.addAction(ds18b20_action)
        rtlsdr_action = QAction("RTL-SDR", self)
        rtlsdr_action.triggered.connect(lambda: self.show_info("RTL-SDR"))
        sensor_menu.addAction(rtlsdr_action)
        sound_action = QAction("میکروفون", self)
        sound_action.triggered.connect(lambda: self.show_info("میکروفون"))
        sensor_menu.addAction(sound_action)

        training_menu = self.menu_bar.addMenu("آموزش مدل")
        collect_action = QAction("جمع‌آوری داده", self)
        collect_action.triggered.connect(lambda: self.show_info("جمع‌آوری داده"))
        training_menu.addAction(collect_action)
        train_action = QAction("آموزش مدل", self)
        train_action.triggered.connect(lambda: self.show_info("آموزش مدل"))
        training_menu.addAction(train_action)
        validate_action = QAction("اعتبارسنجی", self)
        validate_action.triggered.connect(lambda: self.show_info("اعتبارسنجی"))
        training_menu.addAction(validate_action)

        expansion_menu = self.menu_bar.addMenu("گسترش ربات")
        stratum_action = QAction("اسکن Stratum", self)
        stratum_action.triggered.connect(lambda: self.show_info("اسکن Stratum"))
        expansion_menu.addAction(stratum_action)
        traffic_action = QAction("تحلیل ترافیک", self)
        traffic_action.triggered.connect(lambda: self.show_info("تحلیل ترافیک"))
        expansion_menu.addAction(traffic_action)
        alerts_action = QAction("هشدارها", self)
        alerts_action.triggered.connect(lambda: self.show_info("هشدارها"))
        expansion_menu.addAction(alerts_action)

        troubleshoot_menu = self.menu_bar.addMenu("عیب‌یابی")
        sensor_trouble = QAction("حسگرها", self)
        sensor_trouble.triggered.connect(lambda: self.show_info("عیب‌یابی حسگرها"))
        troubleshoot_menu.addAction(sensor_trouble)
        api_trouble = QAction("API", self)
        api_trouble.triggered.connect(lambda: self.show_info("عیب‌یابی API"))
        troubleshoot_menu.addAction(api_trouble)
        network_trouble = QAction("شبکه", self)
        network_trouble.triggered.connect(lambda: self.show_info("عیب‌یابی شبکه"))
        troubleshoot_menu.addAction(network_trouble)

    def show_info(self, section):
        info = {
            "DS18B20": """
            **تنظیم حسگر DS18B20**:
            - اتصالات: GND به GND، DQ به TXD/RXD با مقاومت 4.7kΩ، VDD به 5V.
            - در Device Manager، پورت COM (مثلاً COM3) را بررسی کنید.
            - درایور CH340/FT232R را نصب کنید.
            - عیب‌یابی:
              - بررسی اتصالات و مقاومت pull-up.
              - تست با OneWireViewer.
              - استفاده از PuTTY برای بررسی پورت COM.
            """,
            "RTL-SDR": """
            **تنظیم RTL-SDR**:
            - اتصال به USB با آنتن 433.92 MHz.
            - نصب درایور WinUSB با Zadig.
            - تست با SDR#.
            - عیب‌یابی:
              - بررسی درایور در Device Manager.
              - تغییر فرکانس (مثلاً 915 MHz).
              - اطمینان از اتصال آنتن.
            """,
            "میکروفون": """
            **تنظیم میکروفون**:
            - اتصال به USB یا جک 3.5mm.
            - تنظیم به‌عنوان دستگاه پیش‌فرض در Control Panel > Sound.
            - عیب‌یابی:
              - به‌روزرسانی درایورهای صدا.
              - تست با Audacity.
              - کاهش RATE به 16000 اگر نویز زیاد است.
            """,
            "جمع‌آوری داده": """
            **جمع‌آوری داده**:
            - حداقل 200 نمونه (100 ماینر، 100 غیر ماینر).
            - ماینر: دما 30-50°C، نویز >60dB، RF قوی.
            - غیر ماینر: دما 20-25°C، نویز <40dB، RF ضعیف.
            - اسکن IPهای شناخته‌شده با nmap.
            - ذخیره در miner_data.csv با رمزنگاری.
            """,
            "آموزش مدل": """
            **آموزش مدل**:
            - استفاده از RandomForestClassifier.
            - ویژگی‌ها: دما، RF، صدا، تعداد پورت‌های باز.
            - حداقل 10 نمونه برای آموزش.
            - استفاده از train_test_split برای اعتبارسنجی.
            - بازآموزی دوره‌ای با داده‌های جدید.
            """,
            "اعتبارسنجی": """
            **اعتبارسنجی مدل**:
            - تقسیم داده‌ها به 80% آموزشی و 20% آزمایشی.
            - بررسی دقت مدل با score.
            - استفاده از xAI API برای برچسب‌گذاری خودکار.
            - بررسی داده‌ها در Jupyter Notebook.
            """,
            "اسکن Stratum": """
            **اسکن پروتکل Stratum**:
            - بررسی پورت 3333 برای پروتکل ماینینگ.
            - ارسال درخواست mining.subscribe.
            - بررسی پاسخ برای تأیید ماینر.
            """,
            "تحلیل ترافیک": """
            **تحلیل ترافیک شبکه**:
            - استفاده از scapy برای بررسی TCP.
            - شناسایی poolهای ماینینگ (مانند AntPool، F2Pool).
            - آستانه: بیش از 50 بسته TCP در 30 ثانیه.
            """,
            "هشدارها": """
            **هشدارهای چندکاناله**:
            - ارسال به Telegram.
            - Telegram: نیاز به Bot Token و Chat ID.
            - عیب‌یابی: بررسی اتصال اینترنت و اعتبار کلیدها.
            """,
            "عیب‌یابی حسگرها": """
            **عیب‌یابی حسگرها**:
            - DS18B20: بررسی پورت COM، مقاومت pull-up، درایور.
            - RTL-SDR: بررسی درایور WinUSB، اتصال آنتن.
            - میکروفون: بررسی تنظیمات صدا، درایورها.
            """,
            "عیب‌یابی API": """
            **عیب‌یابی API**:
            - xAI API: بررسی اعتبار کلید در https://console.x.ai.
            - MaxMind: بررسی وجود GeoIP2-City.mmdb.
            - Telegram: بررسی Bot Token و Chat ID.
            """,
            "عیب‌یابی شبکه": """
            **عیب‌یابی شبکه**:
            - nmap: نصب و افزودن به PATH.
            - MQTT: بررسی اتصال به broker.hivemq.com.
            - MaxMind: بررسی دسترسی به پایگاه داده.
            """
        }
        self.chat_output.append(info.get(section, "اطلاعات یافت نشد."))

    def scan_network(self):
        ip_range = self.ip_input.text()
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$", ip_range):
            self.chat_output.append("محدوده IP نامعتبر است! مثال: 192.168.1.0/24")
            return

        devices = advanced_network_scan(ip_range)
        detected_devices = []
        for device in devices:
            ip = device["ip"]
            ports = device["ports"]
            temp = read_temperature()
            rf = read_rf()
            sound = read_sound()
            stratum_result = scan_mining_protocol(ip)
            traffic_result = analyze_traffic(ip)
            device_info = collect_device_info(ip)
            data = {
                "ip": ip,
                "ports": ports,
                "temp": temp,
                "rf": rf,
                "sound": sound,
                "stratum": stratum_result,
                "traffic": traffic_result["is_mining"],
                "mining_pool": traffic_result["pool"]
            }
            result, is_miner = asyncio.run(analyze_with_xai(data))
            device_info.update({
                "ports": ports,
                "services": device["services"],
                "is_miner": is_miner,
                "stratum": stratum_result,
                "traffic": traffic_result["is_mining"],
                "mining_pool": traffic_result["pool"] or "N/A"
            })
            collect_data(ip, ports, temp, rf, sound, is_miner, device_info, traffic_result["pool"])
            detected_devices.append(device_info)
            self.chat_output.append(
                f"دستگاه: {ip}\n"
                f"MAC: {device_info['mac']}\n"
                f"Hostname: {device_info['hostname']}\n"
                f"ISP: {device_info['isp']}\n"
                f"Org: {device_info['org']}\n"
                f"Owner: {device_info['owner']}\n"
                f"Address: {device_info['address']}\n"
                f"موقعیت: ({device_info['lat']}, {device_info['lon']})\n"
                f"پورت‌ها: {ports}\n"
                f"خدمات: {device['services']}\n"
                f"Stratum: {'بله' if stratum_result else 'خیر'}\n"
                f"ترافیک مشکوک: {'بله' if traffic_result['is_mining'] else 'خیر'}\n"
                f"Mining Pool: {traffic_result['pool'] or 'N/A'}\n"
                f"ماینر: {'بله' if is_miner else 'خیر'}\n"
                f"تحلیل xAI: {result}"
            )
            if is_miner:
                asyncio.run(send_alert(f"ماینر شناسایی شد: {ip}, موقعیت: ({device_info['lat']}, {device_info['lon']}), Pool: {traffic_result['pool'] or 'N/A'}"))

        create_dynamic_map(detected_devices)
        self.update_map()
        train_model()

    def update_map(self):
        if os.path.exists(map_file):
            self.map_view.setUrl(f"file:///{map_file}")

    def update_sensors(self):
        self.sensor_output.setText(
            f"حسگرها:\n"
            f"حرارتی: {sensor_data['thermal'][-1] if sensor_data['thermal'] else 'N/A'}\n"
            f"RF: {sensor_data['rf'][-1] if sensor_data['rf'] else 'N/A'}\n"
            f"صوتی: {sensor_data['sound'][-1] if sensor_data['sound'] else 'N/A'}"
        )

# تنظیم MQTT
def on_connect(client, userdata, flags, rc):
    logs.append("به سرور MQTT متصل شد: " + str(rc))
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    socketio.emit('message', {'message': f'MQTT: {msg.payload.decode()}'})

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# مسیرهای API
@app.route('/logs')
def get_logs():
    return jsonify(logs)

if __name__ == '__main__':
    save_env_keys()
    threading.Thread(target=setup_system, daemon=True).start()
    threading.Thread(target=check_sensors, daemon=True).start()
    threading.Thread(target=train_model, daemon=True).start()
    app_gui = QApplication(sys.argv)
    window = MinerDetectorGUI()
    window.show()
    asyncio.run(send_alert("سامانه آماده است!"))
    socketio.run(app, host='0.0.0.0', port=5000)
