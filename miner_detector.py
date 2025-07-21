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
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMenuBar, QAction, QTableWidget, QTableWidgetItem, QTabWidget
from PyQt5.QtGui import QFont, QFontDatabase, QTextCursor, QTextCharFormat, QPalette, QColor, QKeySequence
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QKeySequence
from scapy.all import sniff
from telegram import Bot
from aiocoap import *
from httpx import AsyncClient
from cryptography.fernet import Fernet
import folium
from folium.plugins import MarkerCluster
from dotenv import load_dotenv, set_key
import platform
import serial.tools.list_ports
import geoip2.database
import whois
import sys
import random
import shutil

# تنظیمات
SYSTEM = platform.system()
if SYSTEM == "Linux":
    BASE_DIR = os.path.join(os.path.expanduser("~"), ".miner_detector")
    os.makedirs(BASE_DIR, exist_ok=True)
else:
    BASE_DIR = os.path.join(os.path.expanduser("~"), "Documents")

# بارگذاری متغیرهای محیطی
load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# تنظیمات
sensor_status = {"thermal": False, "rf": False, "sound": False}
sensor_data = {"thermal": [], "rf": [], "sound": []}
logs = []
data_file = os.path.join(BASE_DIR, "miner_data.csv")
map_file = os.path.join(BASE_DIR, "miner_map.html")
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "miner/detector"
XAI_API_KEY = os.getenv("XAI_API_KEY", "xai-9PhOVnjlR1GbZ9r7ahcjxb0mpyMwDUKg8kvvySFlARmCN30MIQwFyxZvlBJuXYKMdpGDQwBx3uX9mxde")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7391505668:AAHIk1c5zW2B5o0zN1HKB2WHzxG3yL5X6S8")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002230229470")
JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(32).hex())
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "your_email@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_app_password")
MAXMIND_DB = os.path.join(BASE_DIR, "GeoIP2-City.mmdb")
XAI_API_URL = "https://api.x.ai/v1/grok"
model = RandomForestClassifier(n_estimators=100, random_state=42)
model_trained = False
JWT_ALGORITHM = "HS256"

# ذخیره کلیدها در .env
def save_env_keys():
    env_file = os.path.join(BASE_DIR, ".env")
    set_key(env_file, "XAI_API_KEY", XAI_API_KEY)
    set_key(env_file, "TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    set_key(env_file, "TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)
    set_key(env_file, "JWT_SECRET", JWT_SECRET)
    set_key(env_file, "EMAIL_ADDRESS", EMAIL_ADDRESS)
    set_key(env_file, "EMAIL_PASSWORD", EMAIL_PASSWORD)

# تنظیم خودکار پیش‌نیازها
def setup_system():
    logs.append("Starting system setup...")
    try:
        required_packages = [
            "requests", "flask", "flask-socketio", "pyrtlsdr", "pyaudio", "scikit-learn",
            "numpy", "pandas", "pyqt5", "paho-mqtt", "pyjwt", "python-telegram-bot",
            "aiocoap", "httpx", "cryptography", "python-dotenv", "scapy", "folium", "geoip2"
        ]
        if SYSTEM == "Windows":
            required_packages.append("pywin32")
        for pkg in required_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                logs.append(f"Installed {pkg} successfully.")
            except Exception as e:
                logs.append(f"Error installing {pkg}: {e}")

        # نصب nmap
        try:
            subprocess.check_output(["nmap", "--version"])
            logs.append("nmap is installed.")
        except:
            logs.append("nmap not found. Installing...")
            if SYSTEM == "Linux":
                subprocess.check_call(["sudo", "apt-get", "install", "-y", "nmap"])
            else:
                logs.append("Please install nmap from https://nmap.org/download.html")

        # نصب libusb در لینوکس
        if SYSTEM == "Linux":
            try:
                subprocess.check_call(["sudo", "apt-get", "install", "-y", "libusb-1.0-0-dev"])
                logs.append("libusb installed.")
            except:
                logs.append("Error installing libusb.")

        # بررسی پورت‌های COM
        ports = list(serial.tools.list_ports.comports())
        if ports:
            logs.append(f"Found COM ports: {[p.device for p in ports]}")
        else:
            logs.append("No COM ports found. Check USB-to-TTL converter.")

        # بررسی RTL-SDR
        try:
            sdr = RtlSdr()
            sdr.close()
            logs.append("RTL-SDR detected.")
        except:
            logs.append("RTL-SDR not detected. Install WinUSB (Windows) or libusb (Linux).")

        # بررسی میکروفون
        try:
            p = pyaudio.PyAudio()
            p.terminate()
            logs.append("Microphone detected.")
        except:
            logs.append("Microphone not detected. Check audio settings.")

        # بررسی MaxMind
        if not os.path.exists(MAXMIND_DB):
            logs.append(f"MaxMind database not found. Place GeoIP2-City.mmdb in {MAXMIND_DB}")

        # کپی فونت در لینوکس
        if SYSTEM == "Linux":
            font_path = "Px437_IBM_VGA8.ttf"
            if os.path.exists(font_path):
                font_dir = "/usr/share/fonts/truetype/custom/"
                os.makedirs(font_dir, exist_ok=True)
                shutil.copy(font_path, font_dir)
                subprocess.run(["fc-cache", "-f", "-v"])
                logs.append("DOS font installed in Linux.")

        logs.append("System setup completed.")
    except Exception as e:
        logs.append(f"System setup error: {e}")

# شبیه‌سازی داده‌های واقعی
def generate_sample_data():
    data = []
    np.random.seed(42)
    for _ in range(100):
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
            "address": "Tehran, Tehran Province, Iran",
            "ports": "3333/tcp open, 4444/tcp open",
            "ports_count": np.random.randint(1, 4),
            "temp": np.random.uniform(30, 50),
            "rf": np.random.uniform(0.5, 2.0),
            "sound": np.random.uniform(60, 80),
            "mining_pool": random.choice(["AntPool", "F2Pool", "Poolin", "N/A"]),
            "is_miner": 1
        })
    for _ in range(100):
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
            "address": "Tehran, Tehran Province, Iran",
            "ports": "No ports open",
            "ports_count": 0,
            "temp": np.random.uniform(20, 25),
            "rf": np.random.uniform(0.0, 0.3),
            "sound": np.random.uniform(30, 40),
            "mining_pool": "N/A",
            "is_miner": 0
        })
    df = pd.DataFrame(data)
    df.to_csv(data_file, mode='w', index=False)
    encrypt_file(data_file)
    logs.append("Generated and saved 200 sample data entries.")

# خواندن دما از DS18B20
def read_temperature(com_port=None):
    if not com_port:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        com_port = ports[0] if ports else "/dev/ttyUSB0" if SYSTEM == "Linux" else "COM3"
    try:
        ser = serial.Serial(com_port, 9600, timeout=1)
        ser.write(b"READ_TEMP\n")
        time.sleep(0.75)
        temp = ser.readline().decode().strip()
        ser.close()
        return float(temp) if temp else None
    except Exception as e:
        logs.append(f"Error reading DS18B20: {e}")
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
        logs.append(f"Error reading RTL-SDR: {e}")
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
        logs.append(f"Error reading sound sensor: {e}")
        return None

# اسکن شبکه پیشرفته
def advanced_network_scan(ip_range):
    try:
        logs.append(f"Starting network scan for range {ip_range}...")
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
        logs.append(f"Error in network scan: {e}")
        return []

# جمع‌آوری اطلاعات خصوصی دستگاه
def collect_device_info(ip):
    info = {"ip": ip, "mac": "", "hostname": "", "isp": "", "org": "", "owner": "", "lat": None, "lon": None, "address": ""}
    try:
        arp_result = subprocess.run(["arp", "-a", ip], capture_output=True, text=True)
        mac_match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", arp_result.stdout)
        if mac_match:
            info["mac"] = mac_match.group(0)

        try:
            info["hostname"] = socket.gethostbyaddr(ip)[0]
        except:
            info["hostname"] = "N/A"

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

        try:
            w = whois.whois(ip)
            info["org"] = w.get("org", info["org"])
            info["owner"] = w.get("registrar", "N/A")
        except:
            pass

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
        logs.append(f"Error collecting device info for {ip}: {e}")
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
        logs.append(f"Error scanning Stratum protocol for {ip}: {e}")
        return False

# تحلیل ترافیک
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
        logs.append(f"Error analyzing traffic for {ip}: {e}")
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
        logs.append(f"Error collecting data: {e}")

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
        logs.append(f"Error encrypting file: {e}")
        return None

# آموزش مدل
def train_model():
    global model_trained, X_test, y_test
    try:
        if not os.path.exists(data_file):
            generate_sample_data()
        df = pd.read_csv(data_file)
        X = df[["temp", "rf", "sound", "ports_count"]]
        y = df["is_miner"]
        if len(X) >= 10:
            global X_test, y_test
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model.fit(X_train, y_train)
            score = model.score(X_test, y_test)
            model_trained = True
            logs.append(f"Model trained with {len(X)} samples. Accuracy: {score:.2f}")
        else:
            logs.append("Insufficient samples for training.")
    except Exception as e:
        logs.append(f"Error training model: {e}")

# تحلیل با xAI API
async def analyze_with_xai(data):
    try:
        async with AsyncClient(http2=True) as client:
            headers = {"Authorization": f"Bearer {XAI_API_KEY}"}
            response = await client.post(XAI_API_URL, headers=headers, json={"query": json.dumps(data)})
            result = response.json().get("result", "Analysis failed")
            is_miner = 1 if "ماینر" in result.lower() else 0
            return result, is_miner
    except Exception as e:
        logs.append(f"Error in xAI analysis: {e}")
        return f"Error: {e}", 0

# ارسال هشدار
async def send_alert(message):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logs.append(f"Alert sent: {message}")
    except Exception as e:
        logs.append(f"Error sending alert: {e}")

# ایجاد نقشه پویا
def create_dynamic_map(devices):
    try:
        m = folium.Map(location=[35.7, 51.4], zoom_start=12)
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
                         f"Miner: {'Yes' if device['is_miner'] else 'No'}")
                folium.Marker(
                    location=[device["lat"], device["lon"]],
                    popup=popup,
                    icon=folium.Icon(color="red" if device["is_miner"] else "blue")
                ).add_to(marker_cluster)
        m.save(map_file)
        logs.append(f"Dynamic map saved at {map_file}")
    except Exception as e:
        logs.append(f"Error creating map: {e}")

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
        logs.append(f"Error in CoAP: {e}")

# رابط گرافیکی Norton Commander
class MinerDetectorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Miner Detector - Norton Commander Style")
        self.setGeometry(100, 100, 800, 600)

        # تنظیم فونت DOS
        font_db = QFontDatabase()
        font_path = "Px437_IBM_VGA8.ttf"
        if os.path.exists(font_path):
            font_id = font_db.addApplicationFont(font_path)
            font_family = font_db.applicationFontFamilies(font_id)[0]
        else:
            font_family = "Courier New"
        self.dos_font = QFont(font_family, 10)

        # تنظیم پالت رنگ Norton Commander
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#000080"))
        palette.setColor(QPalette.WindowText, QColor("#FFFFFF"))
        palette.setColor(QPalette.Base, QColor("#000080"))
        palette.setColor(QPalette.Text, QColor("#FFFFFF"))
        palette.setColor(QPalette.Highlight, QColor("#FFFF00"))
        palette.setColor(QPalette.HighlightedText, QColor("#000000"))
        palette.setColor(QPalette.Button, QColor("#C0C0C0"))
        palette.setColor(QPalette.ButtonText, QColor("#000000"))
        self.setPalette(palette)

        # ویجت اصلی
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # منوی بالا
        self.menu_bar = QMenuBar()
        self.menu_bar.setFont(self.dos_font)
        self.menu_bar.setStyleSheet("background-color: #C0C0C0; color: #000000; border: 1px solid #FFFFFF;")
        self.setMenuBar(self.menu_bar)
        self.setup_menus()

        # کادرهای دوگانه
        panels_layout = QHBoxLayout()
        main_layout.addLayout(panels_layout)

        # پنل چپ: لیست دستگاه‌ها
        self.left_panel = QTableWidget()
        self.left_panel.setFont(self.dos_font)
        self.left_panel.setStyleSheet("background-color: #000080; color: #FFFFFF; border: 2px double #C0C0C0;")
        self.left_panel.setColumnCount(4)
        self.left_panel.setHorizontalHeaderLabels(["IP", "MAC", "Hostname", "Miner"])
        self.left_panel.setRowCount(0)
        self.left_panel.setSelectionMode(QTableWidget.SingleSelection)
        self.left_panel.setSelectionBehavior(QTableWidget.SelectRows)
        self.left_panel.itemSelectionChanged.connect(self.update_right_panel)
        panels_layout.addWidget(self.left_panel)

        # پنل راست: تب‌های اطلاعات و نقشه
        self.right_panel = QTabWidget()
        self.right_panel.setFont(self.dos_font)
        self.right_panel.setStyleSheet("background-color: #000080; color: #FFFFFF; border: 2px double #C0C0C0;")
        
        # تب اطلاعات
        self.info_panel = QTextEdit()
        self.info_panel.setFont(self.dos_font)
        self.info_panel.setStyleSheet("background-color: #000080; color: #FFFFFF;")
        self.info_panel.setReadOnly(True)
        self.right_panel.addTab(self.info_panel, "Info")

        # تب نقشه
        self.map_panel = QWebEngineView()
        self.map_panel.setStyleSheet("border: 2px double #C0C0C0;")
        self.right_panel.addTab(self.map_panel, "Map")
        panels_layout.addWidget(self.right_panel)

        # ورودی IP و دکمه اسکن
        input_layout = QHBoxLayout()
        self.ip_label = QLabel("IP Range:")
        self.ip_label.setFont(self.dos_font)
        self.ip_label.setStyleSheet("color: #FFFFFF;")
        self.ip_input = QLineEdit()
        self.ip_input.setFont(self.dos_font)
        self.ip_input.setStyleSheet("background-color: #000080; color: #FFFFFF; border: 1px solid #C0C0C0;")
        self.scan_button = QPushButton("Scan")
        self.scan_button.setFont(self.dos_font)
        self.scan_button.setStyleSheet("background-color: #C0C0C0; color: #000000; border: 1px solid #FFFFFF;")
        self.scan_button.clicked.connect(self.scan_network)
        input_layout.addWidget(self.ip_label)
        input_layout.addWidget(self.ip_input)
        input_layout.addWidget(self.scan_button)
        main_layout.addLayout(input_layout)

        # مکان‌نمای چشمک‌زن
        self.cursor_timer = QTimer()
        self.cursor_timer.timeout.connect(self.toggle_cursor)
        self.cursor_timer.start(500)
        self.cursor_visible = True

        # تایمر به‌روزرسانی حسگرها
        self.sensor_timer = QTimer()
        self.sensor_timer.timeout.connect(self.update_sensors)
        self.sensor_timer.start(60000)

        # میانبرهای کیبورد
        self.setup_shortcuts()

        # ذخیره اطلاعات دستگاه‌ها
        self.devices = []

    def setup_shortcuts(self):
        from PyQt5.QtWidgets import QShortcut
        QShortcut(QKeySequence("F3"), self, self.show_map)
        QShortcut(QKeySequence("F5"), self, self.scan_network)
        QShortcut(QKeySequence("F10"), self, self.close)
        QShortcut(QKeySequence("Tab"), self, self.switch_focus)

    def toggle_cursor(self):
        if self.ip_input.hasFocus():
            cursor = self.ip_input.text()
            if self.cursor_visible:
                self.ip_input.setText(cursor + "|")
            else:
                self.ip_input.setText(cursor.rstrip("|"))
            self.cursor_visible = not self.cursor_visible

    def switch_focus(self):
        if self.left_panel.hasFocus():
            self.right_panel.setFocus()
        elif self.right_panel.hasFocus():
            self.ip_input.setFocus()
        else:
            self.left_panel.setFocus()

    def setup_menus(self):
        file_menu = self.menu_bar.addMenu("File")
        file_menu.setFont(self.dos_font)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menu_bar.addMenu("Edit")
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(lambda: self.info_panel.copy())
        edit_menu.addAction(copy_action)

        view_menu = self.menu_bar.addMenu("View")
        map_action = QAction("Show Map (F3)", self)
        map_action.triggered.connect(self.show_map)
        view_menu.addAction(map_action)

        options_menu = self.menu_bar.addMenu("Options")
        sensor_action = QAction("Sensors", self)
        sensor_action.triggered.connect(lambda: self.show_info("Sensors"))
        options_menu.addAction(sensor_action)

        tools_menu = self.menu_bar.addMenu("Tools")
        train_action = QAction("Train Model", self)
        train_action.triggered.connect(lambda: self.show_info("Train Model"))
        tools_menu.addAction(train_action)

        help_menu = self.menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda: self.show_info("About"))
        help_menu.addAction(about_action)

    def show_info(self, section):
        info = {
            "Sensors": """
            Sensors Status:
            - Thermal: {}
            - RF: {}
            - Sound: {}
            """.format(
                "Active" if sensor_status["thermal"] else "Inactive",
                "Active" if sensor_status["rf"] else "Inactive",
                "Active" if sensor_status["sound"] else "Inactive"
            ),
            "Train Model": """
            Training Model:
            - Uses RandomForestClassifier
            - Features: Temperature, RF, Sound, Open Ports
            - Minimum 10 samples required
            - Accuracy: {}
            """.format("N/A" if not model_trained else model.score(X_test, y_test)),
            "About": """
            Miner Detector v1.0
            Norton Commander Style Interface
            Developed for cryptocurrency miner detection
            Contact: support@x.ai
            """
        }
        self.right_panel.setCurrentIndex(0)
        self.info_panel.setText(info.get(section, "Information not available."))

    def show_map(self):
        if os.path.exists(map_file):
            self.right_panel.setCurrentIndex(1)
            self.map_panel.setUrl(f"file:///{map_file}")

    def update_right_panel(self):
        selected = self.left_panel.selectedItems()
        if not selected or not self.devices:
            return
        row = self.left_panel.currentRow()
        device = self.devices[row]
        self.right_panel.setCurrentIndex(0)
        self.info_panel.setText(
            f"Device: {device['ip']}\n"
            f"MAC: {device['mac']}\n"
            f"Hostname: {device['hostname']}\n"
            f"ISP: {device['isp']}\n"
            f"Org: {device['org']}\n"
            f"Owner: {device['owner']}\n"
            f"Address: {device['address']}\n"
            f"Location: ({device['lat']}, {device['lon']})\n"
            f"Ports: {device['ports']}\n"
            f"Services: {device['services']}\n"
            f"Stratum: {'Yes' if device['stratum'] else 'No'}\n"
            f"Traffic: {'Yes' if device['traffic'] else 'No'}\n"
            f"Mining Pool: {device['mining_pool']}\n"
            f"Miner: {'Yes' if device['is_miner'] else 'No'}\n"
            f"xAI Analysis: {device['xai_result']}"
        )

    def scan_network(self):
        ip_range = self.ip_input.text().rstrip("|")
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$", ip_range):
            self.right_panel.setCurrentIndex(0)
            self.info_panel.setText("Invalid IP range! Example: 192.168.1.0/24")
            return

        self.left_panel.setRowCount(0)
        self.devices = []
        devices = advanced_network_scan(ip_range)
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
                "mining_pool": traffic_result["pool"] or "N/A",
                "xai_result": result
            })
            collect_data(ip, ports, temp, rf, sound, is_miner, device_info, traffic_result["pool"])
            self.devices.append(device_info)

            row = self.left_panel.rowCount()
            self.left_panel.insertRow(row)
            self.left_panel.setItem(row, 0, QTableWidgetItem(ip))
            self.left_panel.setItem(row, 1, QTableWidgetItem(device_info["mac"]))
            self.left_panel.setItem(row, 2, QTableWidgetItem(device_info["hostname"]))
            self.left_panel.setItem(row, 3, QTableWidgetItem("Yes" if is_miner else "No"))

            if is_miner:
                asyncio.run(send_alert(f"Miner detected: {ip}, Location: ({device_info['lat']}, {device_info['lon']}), Pool: {traffic_result['pool'] or 'N/A'}"))

        create_dynamic_map(self.devices)
        self.show_map()
        train_model()

    def update_sensors(self):
        self.right_panel.setCurrentIndex(0)
        self.info_panel.append(
            f"Sensors:\n"
            f"Thermal: {sensor_data['thermal'][-1] if sensor_data['thermal'] else 'N/A'}\n"
            f"RF: {sensor_data['rf'][-1] if sensor_data['rf'] else 'N/A'}\n"
            f"Sound: {sensor_data['sound'][-1] if sensor_data['sound'] else 'N/A'}\n"
        )

# تنظیم MQTT
def on_connect(client, userdata, flags, rc):
    logs.append("Connected to MQTT broker: " + str(rc))
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
    asyncio.run(send_alert("System ready!"))
    socketio.run(app, host='0.0.0.0', port=5000)