#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
کاشف - نسخه بهینه شده
سیستم تشخیص ماینر ارزهای دیجیتال
نسخه تولید با امنیت و کارایی بالا
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import warnings

# Third-party imports
import aiofiles
import aioredis
import uvloop
from aiohttp import web, ClientSession
from aiohttp_security import setup as security_setup
from aiohttp_security import SessionIdentityPolicy
from aiohttp_security import authorized_userid
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import redis.asyncio as redis
from celery import Celery
import jwt
from pydantic import BaseModel, ValidationError
import asyncpg
from prometheus_client import Counter, Histogram, Gauge
import structlog

# Suppress warnings
warnings.filterwarnings("ignore")

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configuration
class Config:
    """Application configuration"""
    
    def __init__(self):
        load_dotenv()
        
        # Base paths
        self.BASE_DIR = Path.home() / ".miner_detector"
        self.BASE_DIR.mkdir(exist_ok=True)
        
        # Database
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://user:pass@localhost/minerdb")
        
        # Security
        self.SECRET_KEY = os.getenv("SECRET_KEY", Fernet.generate_key().decode())
        self.JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
        
        # APIs
        self.XAI_API_KEY = os.getenv("XAI_API_KEY", "")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # Performance
        self.MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
        self.REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))
        self.HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
        
        # ML Model
        self.MODEL_RETRAIN_INTERVAL = int(os.getenv("MODEL_RETRAIN_INTERVAL", "3600"))
        self.MIN_SAMPLES_FOR_TRAINING = int(os.getenv("MIN_SAMPLES_FOR_TRAINING", "100"))

config = Config()

# Metrics
DETECTION_COUNTER = Counter('miners_detected_total', 'Total number of miners detected')
SCAN_DURATION = Histogram('network_scan_duration_seconds', 'Time spent scanning network')
ACTIVE_SENSORS = Gauge('active_sensors_count', 'Number of active sensors')

# Data Models
class DeviceData(BaseModel):
    """Device data validation model"""
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    ports: List[int] = []
    temperature: Optional[float] = None
    rf_signal: Optional[float] = None
    sound_level: Optional[float] = None
    location: Optional[Dict[str, float]] = None
    is_miner: bool = False
    confidence: float = 0.0
    detection_time: datetime
    mining_pool: Optional[str] = None

class SensorReading(BaseModel):
    """Sensor reading validation model"""
    sensor_type: str
    value: float
    timestamp: datetime
    unit: str
    device_id: Optional[str] = None

# Core Application Class
class MinerDetectorApp:
    """Main application class with async architecture"""
    
    def __init__(self):
        self.config = config
        self.redis_pool = None
        self.db_pool = None
        self.ml_model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.session_cache = {}
        self.active_scans = set()
        
        # Initialize Celery for background tasks
        self.celery = Celery(
            'miner_detector',
            broker=config.REDIS_URL,
            backend=config.REDIS_URL
        )
        
        # Initialize encryption
        self.cipher = Fernet(config.ENCRYPTION_KEY)
        
    async def init_app(self) -> web.Application:
        """Initialize the web application"""
        app = web.Application()
        
        # Setup routes
        self.setup_routes(app)
        
        # Setup middleware
        app.middlewares.append(self.security_middleware)
        app.middlewares.append(self.logging_middleware)
        
        # Setup security
        security_setup(app, SessionIdentityPolicy(), self.check_credentials)
        
        return app
    
    def setup_routes(self, app: web.Application):
        """Setup application routes"""
        app.router.add_get('/', self.index)
        app.router.add_post('/api/scan', self.scan_network)
        app.router.add_get('/api/devices', self.get_devices)
        app.router.add_post('/api/sensors', self.process_sensor_data)
        app.router.add_get('/api/status', self.health_check)
        app.router.add_post('/api/train', self.train_model)
        app.router.add_get('/ws', self.websocket_handler)
    
    async def init_connections(self):
        """Initialize database connections"""
        try:
            # Redis connection
            self.redis_pool = redis.ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_POOL_SIZE
            )
            
            # PostgreSQL connection
            self.db_pool = await asyncpg.create_pool(
                config.POSTGRES_URL,
                min_size=5,
                max_size=20
            )
            
            logger.info("Database connections initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize connections: {e}")
            raise
    
    async def security_middleware(self, request: web.Request, handler):
        """Security middleware for request validation"""
        # Rate limiting
        client_ip = request.remote
        redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        key = f"rate_limit:{client_ip}"
        current = await redis_client.get(key)
        
        if current and int(current) > 100:  # 100 requests per minute
            raise web.HTTPTooManyRequests()
        
        await redis_client.incr(key)
        await redis_client.expire(key, 60)
        
        # CORS headers
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    
    async def logging_middleware(self, request: web.Request, handler):
        """Logging middleware"""
        start_time = time.time()
        
        try:
            response = await handler(request)
            process_time = time.time() - start_time
            
            logger.info(
                "Request processed",
                method=request.method,
                path=request.path,
                status=response.status,
                process_time=process_time,
                client_ip=request.remote
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                method=request.method,
                path=request.path,
                error=str(e),
                process_time=process_time,
                client_ip=request.remote
            )
            raise
    
    async def check_credentials(self, identity):
        """Check user credentials for security"""
        if not identity:
            return None
        
        # Validate JWT token
        try:
            payload = jwt.decode(identity, config.JWT_SECRET, algorithms=['HS256'])
            return payload.get('user_id')
        except jwt.InvalidTokenError:
            return None
    
    async def index(self, request: web.Request):
        """Main page handler"""
        return web.Response(text="Miner Detector API v2.0", content_type='text/html')
    
    async def health_check(self, request: web.Request):
        """Health check endpoint"""
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "redis": "connected" if self.redis_pool else "disconnected",
            "database": "connected" if self.db_pool else "disconnected",
            "model_trained": self.is_trained,
            "active_scans": len(self.active_scans)
        }
        return web.json_response(status)
    
    async def scan_network(self, request: web.Request):
        """Network scanning endpoint with improved efficiency"""
        try:
            data = await request.json()
            ip_range = data.get('ip_range', '192.168.1.0/24')
            
            if ip_range in self.active_scans:
                raise web.HTTPConflict(text="Scan already in progress for this range")
            
            self.active_scans.add(ip_range)
            
            # Start background scan
            task = asyncio.create_task(self._perform_network_scan(ip_range))
            
            return web.json_response({
                "status": "scan_started",
                "ip_range": ip_range,
                "scan_id": id(task)
            })
            
        except ValidationError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)
        finally:
            self.active_scans.discard(ip_range)
    
    async def _perform_network_scan(self, ip_range: str):
        """Perform actual network scanning"""
        with SCAN_DURATION.time():
            try:
                # Implementation of efficient network scanning
                devices = await self._discover_devices(ip_range)
                
                for device in devices:
                    # Validate device data
                    device_data = DeviceData(**device)
                    
                    # Predict if device is a miner
                    if self.is_trained:
                        prediction = await self._predict_miner(device_data)
                        device_data.is_miner = prediction['is_miner']
                        device_data.confidence = prediction['confidence']
                        
                        if device_data.is_miner:
                            DETECTION_COUNTER.inc()
                            await self._send_alert(device_data)
                    
                    # Store device data
                    await self._store_device_data(device_data)
                
                logger.info(f"Scan completed for {ip_range}, found {len(devices)} devices")
                
            except Exception as e:
                logger.error(f"Network scan failed: {e}")
    
    async def _discover_devices(self, ip_range: str) -> List[Dict]:
        """Discover devices in network range"""
        # Placeholder for actual device discovery logic
        # This would implement nmap scanning, service detection, etc.
        devices = []
        
        # Simulate device discovery
        import ipaddress
        network = ipaddress.IPv4Network(ip_range, strict=False)
        
        for ip in list(network.hosts())[:10]:  # Limit for demo
            device = {
                "ip": str(ip),
                "mac": f"00:11:22:33:44:{str(ip).split('.')[-1]:02x}",
                "hostname": f"device-{str(ip).split('.')[-1]}",
                "ports": [22, 80, 443],
                "detection_time": datetime.utcnow()
            }
            devices.append(device)
        
        return devices
    
    async def _predict_miner(self, device_data: DeviceData) -> Dict[str, Union[bool, float]]:
        """Predict if device is a miner using ML model"""
        if not self.is_trained or not self.ml_model:
            return {"is_miner": False, "confidence": 0.0}
        
        try:
            # Prepare features
            features = np.array([[
                device_data.temperature or 25.0,
                device_data.rf_signal or 0.1,
                device_data.sound_level or 35.0,
                len(device_data.ports)
            ]])
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Predict
            prediction = self.ml_model.predict(features_scaled)[0]
            confidence = self.ml_model.predict_proba(features_scaled)[0].max()
            
            return {
                "is_miner": bool(prediction),
                "confidence": float(confidence)
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"is_miner": False, "confidence": 0.0}
    
    async def _store_device_data(self, device_data: DeviceData):
        """Store device data in database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO devices (ip, mac, hostname, ports, temperature, 
                                       rf_signal, sound_level, is_miner, confidence, 
                                       detection_time, mining_pool)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (ip) DO UPDATE SET
                        mac = EXCLUDED.mac,
                        hostname = EXCLUDED.hostname,
                        ports = EXCLUDED.ports,
                        temperature = EXCLUDED.temperature,
                        rf_signal = EXCLUDED.rf_signal,
                        sound_level = EXCLUDED.sound_level,
                        is_miner = EXCLUDED.is_miner,
                        confidence = EXCLUDED.confidence,
                        detection_time = EXCLUDED.detection_time,
                        mining_pool = EXCLUDED.mining_pool
                """, 
                device_data.ip, device_data.mac, device_data.hostname,
                device_data.ports, device_data.temperature,
                device_data.rf_signal, device_data.sound_level,
                device_data.is_miner, device_data.confidence,
                device_data.detection_time, device_data.mining_pool)
                
        except Exception as e:
            logger.error(f"Database storage error: {e}")
    
    async def _send_alert(self, device_data: DeviceData):
        """Send alert for detected miner"""
        message = (
            f"🚨 ماینر شناسایی شد!\n"
            f"IP: {device_data.ip}\n"
            f"اطمینان: {device_data.confidence:.2%}\n"
            f"زمان: {device_data.detection_time}\n"
            f"پول: {device_data.mining_pool or 'نامشخص'}"
        )
        
        # Send to background task queue
        self.celery.send_task('send_telegram_alert', args=[message])
    
    async def train_model(self, request: web.Request):
        """Train ML model endpoint"""
        try:
            # Load training data
            training_data = await self._load_training_data()
            
            if len(training_data) < config.MIN_SAMPLES_FOR_TRAINING:
                return web.json_response({
                    "error": f"Insufficient training data. Need at least {config.MIN_SAMPLES_FOR_TRAINING} samples"
                }, status=400)
            
            # Train model
            metrics = await self._train_ml_model(training_data)
            
            return web.json_response({
                "status": "training_completed",
                "metrics": metrics,
                "samples_used": len(training_data)
            })
            
        except Exception as e:
            logger.error(f"Model training error: {e}")
            return web.json_response({"error": "Training failed"}, status=500)
    
    async def _load_training_data(self) -> pd.DataFrame:
        """Load training data from database"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT temperature, rf_signal, sound_level, 
                       array_length(ports, 1) as port_count, is_miner
                FROM devices 
                WHERE temperature IS NOT NULL 
                  AND rf_signal IS NOT NULL 
                  AND sound_level IS NOT NULL
                ORDER BY detection_time DESC
                LIMIT 10000
            """)
            
            return pd.DataFrame(rows)
    
    async def _train_ml_model(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train the ML model"""
        try:
            # Prepare features and labels
            X = data[['temperature', 'rf_signal', 'sound_level', 'port_count']].values
            y = data['is_miner'].values
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            self.scaler.fit(X_train)
            X_train_scaled = self.scaler.transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train Random Forest
            self.ml_model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.ml_model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = self.ml_model.predict(X_test_scaled)
            
            metrics = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(precision_score(y_test, y_pred, average='weighted')),
                "recall": float(recall_score(y_test, y_pred, average='weighted'))
            }
            
            self.is_trained = True
            
            logger.info("Model training completed", metrics=metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise
    
    async def process_sensor_data(self, request: web.Request):
        """Process incoming sensor data"""
        try:
            data = await request.json()
            
            # Validate sensor data
            sensor_reading = SensorReading(**data)
            
            # Store in Redis for real-time processing
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            await redis_client.setex(
                f"sensor:{sensor_reading.sensor_type}:{sensor_reading.device_id}",
                300,  # 5 minutes TTL
                json.dumps(sensor_reading.dict(), default=str)
            )
            
            # Update active sensors metric
            ACTIVE_SENSORS.set(await redis_client.scard("active_sensors"))
            
            return web.json_response({"status": "data_received"})
            
        except ValidationError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Sensor data processing error: {e}")
            return web.json_response({"error": "Processing failed"}, status=500)
    
    async def get_devices(self, request: web.Request):
        """Get detected devices"""
        try:
            limit = int(request.query.get('limit', 100))
            offset = int(request.query.get('offset', 0))
            
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT ip, mac, hostname, ports, temperature, rf_signal,
                           sound_level, is_miner, confidence, detection_time,
                           mining_pool
                    FROM devices
                    ORDER BY detection_time DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
                
                devices = [dict(row) for row in rows]
                
                return web.json_response({
                    "devices": devices,
                    "total": len(devices),
                    "limit": limit,
                    "offset": offset
                })
                
        except Exception as e:
            logger.error(f"Get devices error: {e}")
            return web.json_response({"error": "Failed to retrieve devices"}, status=500)
    
    async def websocket_handler(self, request: web.Request):
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            # Subscribe to Redis for real-time updates
            redis_client = redis.Redis(connection_pool=self.redis_pool)
            pubsub = redis_client.pubsub()
            await pubsub.subscribe('miner_alerts', 'sensor_updates')
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await ws.send_str(json.dumps({
                        'channel': message['channel'].decode(),
                        'data': json.loads(message['data'])
                    }))
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await pubsub.unsubscribe('miner_alerts', 'sensor_updates')
            await pubsub.close()
        
        return ws
    
    async def close(self):
        """Clean shutdown"""
        if self.redis_pool:
            await self.redis_pool.disconnect()
        if self.db_pool:
            await self.db_pool.close()


# Background tasks with Celery
@app.celery.task
def send_telegram_alert(message: str):
    """Send Telegram alert (background task)"""
    import requests
    
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")


# Database schema
DATABASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    ip INET UNIQUE NOT NULL,
    mac MACADDR,
    hostname VARCHAR(255),
    ports INTEGER[],
    temperature REAL,
    rf_signal REAL,
    sound_level REAL,
    is_miner BOOLEAN DEFAULT FALSE,
    confidence REAL DEFAULT 0.0,
    detection_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    mining_pool VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip);
CREATE INDEX IF NOT EXISTS idx_devices_is_miner ON devices(is_miner);
CREATE INDEX IF NOT EXISTS idx_devices_detection_time ON devices(detection_time);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    sensor_type VARCHAR(50) NOT NULL,
    device_id VARCHAR(100),
    value REAL NOT NULL,
    unit VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_device ON sensor_readings(device_id);
"""


async def create_tables(db_pool):
    """Create database tables"""
    async with db_pool.acquire() as conn:
        await conn.execute(DATABASE_SCHEMA)
        logger.info("Database tables created successfully")


async def main():
    """Main application entry point"""
    # Use uvloop for better performance on Linux
    if sys.platform != 'win32':
        uvloop.install()
    
    # Create application
    app_instance = MinerDetectorApp()
    
    try:
        # Initialize connections
        await app_instance.init_connections()
        
        # Create database tables
        await create_tables(app_instance.db_pool)
        
        # Initialize web app
        app = await app_instance.init_app()
        
        # Start web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        
        logger.info("Miner Detector started on http://0.0.0.0:8080")
        
        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        
    finally:
        await app_instance.close()


if __name__ == '__main__':
    asyncio.run(main())