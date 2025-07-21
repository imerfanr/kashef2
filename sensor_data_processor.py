
import requests
import subprocess
import re
import json
import os
import datetime
import threading
import time
import webbrowser
import pyserial
import pyaudio
import numpy as np
from rtlsdr import RtlSdr
from flask import Flask, jsonify
from flask_socketio import SocketIO
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import glob

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# تنظیمات حسگرها و APIها
SENSOR_API_URL = "http://localhost:5001/sensors"  # API محلی برای حسگرها
XAI_API_URL = "https://x.ai/api"  # API xAI برای تحلیل و چت
XAI_API_KEY = "your_xai_api_key"  # جایگزین با کلید واقعی
IP_API_URL = "https://ip-api.com/json/"
SURICATA_API_URL = "http://localhost:5000/logs"

sensor_status = {"thermal": False, "rf": False, "sound": False}
sensor_data = {"thermal": [], "rf": [], "sound": []}
logs = []

# مدل یادگیری ماشین برای تشخیص ماینر
clf = RandomForestClassifier(n_estimators=100, random_state=42)
model_trained = False

def read_thermal_sensor():
    try:
        base_dir = 'C:\\Program Files\\Sensors\\thermal\\'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '\\w1_slave'
        with open(device_file, 'r') as f:
            lines = f.readlines()
        temp_string = lines[1].strip().split('t=')[1]
        return float(temp_string) / 1000.0  # دما به سلسیوس
    except Exception:
        return None

def read_rf_sensor():
    try:
        sdr = RtlSdr()
        sdr.sample_rate = 2.4e6
        sdr.center_freq = 2.4e9
        samples = sdr.read_samples(256*1024)
        sdr.close()
        return np.abs(np.mean(samples))  # شدت سیگنال
    except Exception:
        return None

def read_sound_sensor():
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
        return 20 * np.log10(np.sqrt(np.mean(samples**2)))  # دسی‌بل
    except Exception:
        return None

def check_sensors():
    while True:
        try:
            sensor_status["thermal"] = os.path.exists("C:\\Program Files\\Sensors\\thermal\\28*")
            if sensor_status["thermal"]:
                temp = read_thermal_sensor()
                if temp is not None:
                    sensor_data["thermal"].append(temp)
            sensor_status["rf"] = os.path.exists("C:\\Program Files\\Sensors\\rf\\")
            if sensor_status["rf"]:
                rf = read_rf_sensor()
                if rf is not None:
                    sensor_data["rf"].append(rf)
            sensor_status["sound"] = True  # فرض می‌کنیم میکروفون همیشه در دسترس است
            sound = read_sound_sensor()
            if sound is not None:
                sensor_data["sound"].append(sound)
            socketio.emit('sensor_status', sensor_status)
            socketio.emit('sensor_data', sensor_data)
        except Exception:
            pass
        time.sleep(60)

def train_ml_model():
    global model_trained
    # داده‌های نمونه برای آموزش (واقعی باید جایگزین شود)
    data = {
        "ports_open": [1, 0, 1, 0, 1],
        "thermal": [45.0, 25.0, 50.0, 20.0, 55.0],
        "rf": [0.1, 0.05, 0.15, 0.02, 0.2],
        "sound": [60.0, 40.0, 65.0, 35.0, 70.0],
        "is_miner": [1, 0, 1, 0, 1]
    }
    df = pd.DataFrame(data)
    X = df[["ports_open", "thermal", "rf", "sound"]]
    y = df["is_miner"]
    clf.fit(X, y)
    model_trained = True
    print("مدل یادگیری ماشین آموزش داده شد.")

@app.route('/analyze_ip/<ip>')
def analyze_ip(ip):
    ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    if not re.match(ip_pattern, ip):
        return jsonify({"status": "fail", "message": "Invalid IP address"})

    # دریافت اطلاعات شبکه از ip-api.com
    network_info = {}
    try:
        response = requests.get(f"{IP_API_URL}{ip}?fields=status,country,city,lat,lon,isp,org")
        network_info = response.json() if response.status_code == 200 else {"status": "fail", "message": "API error"}
    except Exception as e:
        network_info = {"status": "fail", "message": str(e)}

    # اسکن پورت‌ها با nmap
    nmap_result = "N/A"
    ports_open = 0
    try:
        result = subprocess.run(["nmap", "-p", "3333,4444,1800,4028", "--open", ip], capture_output=True, text=True, timeout=300)
        nmap_result = result.stdout
        ports_open = 1 if "open" in nmap_result else 0
    except Exception as e:
        nmap_result = str(e)

    # دریافت داده‌های حسگر
    sensor_values = {
        "thermal": sensor_data["thermal"][-1] if sensor_data["thermal"] else 0.0,
        "rf": sensor_data["rf"][-1] if sensor_data["rf"] else 0.0,
        "sound": sensor_data["sound"][-1] if sensor_data["sound"] else 0.0
    }

    # تحلیل با مدل یادگیری ماشین
    is_miner = False
    if model_trained:
        try:
            prediction = clf.predict([[ports_open, sensor_values["thermal"], sensor_values["rf"], sensor_values["sound"]]])[0]
            is_miner = bool(prediction)
        except Exception:
            is_miner = False

    # دریافت لاگ‌های Suricata
    suricata_logs = []
    try:
        response = requests.get(SURICATA_API_URL)
        suricata_logs = response.json() if response.status_code == 200 else []
    except Exception:
        suricata_logs = []

    # ذخیره داده‌ها
    data_to_save = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_name": "N/A",
        "number": "N/A",
        "ip_address": ip,
        "network_info": network_info,
        "nmap_result": nmap_result,
        "sensor_data": sensor_values,
        "is_miner": is_miner,
        "suricata_logs": suricata_logs
    }
    file_path = os.path.join(os.path.expanduser("~"), "Documents", "user_data.json")
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False)
            f.write("\n")
    except Exception as e:
        print(f"خطا در ذخیره داده‌ها: {e}")

    socketio.emit('analysis_result', data_to_save)
    return jsonify(data_to_save)

@socketio.on('connect')
def handle_connect():
    socketio.emit('sensor_status', sensor_status)
    socketio.emit('sensor_data', sensor_data)

@socketio.on('chat')
def handle_chat(data):
    message = data.get('message', '')
    mode = data.get('mode', 'chat')
    if mode == 'chat':
        # استفاده از xAI API برای پاسخ هوشمند
        try:
            response = requests.post(
                f"{XAI_API_URL}/chat",
                headers={"Authorization": f"Bearer {XAI_API_KEY}"},
                json={"message": message}
            )
            reply = response.json().get("reply", "پاسخ دریافت نشد.") if response.status_code == 200 else "خطا در API"
            socketio.emit('chat', {'message': reply})
        except Exception as e:
            socketio.emit('chat', {'message': f"خطا در چت: {e}"})
    elif mode == 'execute':
        # اجرای دستورات (مثال: باز کردن مرورگر یا IDE)
        if "open browser" in message.lower():
            webbrowser.open("https://www.google.com")
            socketio.emit('chat', {'message': 'مرورگر باز شد.'})
        elif "open ide" in message.lower():
            subprocess.run(["code"])  # فرضاً Visual Studio Code
            socketio.emit('chat', {'message': 'IDE باز شد.'})
        elif "read file" in message.lower():
            try:
                file_path = message.split("read file ")[1]
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                socketio.emit('chat', {'message': f'محتوای فایل: {content}'})
            except Exception as e:
                socketio.emit('chat', {'message': f'خطا در خواندن فایل: {e}'})
    elif mode == 'analyze':
        socketio.emit('chat', {'message': 'در حال تحلیل داده‌ها...'})

def main():
    print("Hello Python!")
    user_name = input("لطفاً نام خود را وارد کنید: ")
    if not user_name:
        print("نامی وارد نشده، خوش‌آمد به کاربر ناشناس!")
    else:
        print(f"سلام، {user_name}! به این برنامه پایتون خوش آمدید!")

    number = input("لطفاً یک عدد برای بررسی زوج یا فرد بودن وارد کنید: ")
    try:
        number = int(number)
        print(f"عدد {number} {'زوج' if number % 2 == 0 else 'فرد'} است!")
    except ValueError:
        print("ورودی نامعتبر! لطفاً یک عدد معتبر وارد کنید.")

    ip_address = input("لطفاً یک آدرس IP برای بررسی وارد کنید (مثال: 192.168.1.1): ")
    response = requests.get(f"http://127.0.0.1:5000/analyze_ip/{ip_address}")
    print("نتایج تحلیل:", json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # آموزش مدل یادگیری ماشین
    threading.Thread(target=train_ml_model, daemon=True).start()
    # بررسی حسگرها
    threading.Thread(target=check_sensors, daemon=True).start()
    # اجرای سرور Flask
    threading.Thread(target=lambda: socketio.run(app, host='0.0.0.0', port=5000), daemon=True).start()
    # اجرای برنامه اصلی
    main()
