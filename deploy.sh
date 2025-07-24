#!/bin/bash

# Miner Detector Deployment Script
# کاشف - اسکریپت مستقرسازی نسخه بهینه شده

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Configuration
PROJECT_NAME="miner-detector"
PROJECT_DIR="/opt/${PROJECT_NAME}"
BACKUP_DIR="/opt/backups/${PROJECT_NAME}"
LOG_DIR="/var/log/${PROJECT_NAME}"
SERVICE_USER="minerapp"

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        error "Cannot detect operating system"
        exit 1
    fi
    
    log "Detected OS: $OS $OS_VERSION"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y \
                curl \
                wget \
                git \
                docker.io \
                docker-compose \
                postgresql-client \
                redis-tools \
                nmap \
                python3 \
                python3-pip \
                python3-venv \
                build-essential \
                libpq-dev \
                libssl-dev \
                libffi-dev \
                nginx \
                certbot \
                python3-certbot-nginx \
                htop \
                iotop \
                net-tools \
                ufw
            ;;
        centos|rhel|fedora)
            if command -v dnf > /dev/null; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi
            
            $PKG_MANAGER update -y
            $PKG_MANAGER install -y \
                curl \
                wget \
                git \
                docker \
                docker-compose \
                postgresql \
                redis \
                nmap \
                python3 \
                python3-pip \
                python3-devel \
                gcc \
                gcc-c++ \
                make \
                openssl-devel \
                libffi-devel \
                nginx \
                certbot \
                python3-certbot-nginx \
                htop \
                iotop \
                net-tools \
                firewalld
            ;;
        *)
            error "Unsupported operating system: $OS"
            exit 1
            ;;
    esac
    
    log "System dependencies installed successfully"
}

# Create system user
create_user() {
    log "Creating system user: $SERVICE_USER"
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/false -d $PROJECT_DIR $SERVICE_USER
        log "User $SERVICE_USER created"
    else
        info "User $SERVICE_USER already exists"
    fi
}

# Setup directories
setup_directories() {
    log "Setting up directories..."
    
    # Create main directories
    mkdir -p $PROJECT_DIR
    mkdir -p $BACKUP_DIR
    mkdir -p $LOG_DIR
    mkdir -p /etc/$PROJECT_NAME
    
    # Create subdirectories
    mkdir -p $PROJECT_DIR/{logs,data,ssl,config}
    mkdir -p $LOG_DIR/{app,nginx,postgres,redis}
    
    # Set permissions
    chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR
    chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR
    chmod 755 $PROJECT_DIR
    chmod 750 $LOG_DIR
    
    log "Directories created and configured"
}

# Configure Docker
setup_docker() {
    log "Configuring Docker..."
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    # Add service user to docker group
    usermod -aG docker $SERVICE_USER
    
    # Configure Docker daemon
    cat > /etc/docker/daemon.json << EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
EOF
    
    systemctl reload docker
    log "Docker configured successfully"
}

# Generate secrets
generate_secrets() {
    log "Generating security keys..."
    
    # Generate random secrets
    SECRET_KEY=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 32)
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    REDIS_PASSWORD=$(openssl rand -hex 16)
    POSTGRES_PASSWORD=$(openssl rand -hex 16)
    GRAFANA_PASSWORD=$(openssl rand -hex 12)
    
    # Create .env file
    cat > $PROJECT_DIR/.env << EOF
# Generated on $(date)
POSTGRES_DB=minerdb
POSTGRES_USER=mineruser
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_URL=postgresql://mineruser:$POSTGRES_PASSWORD@postgres:5432/minerdb

REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0

SECRET_KEY=$SECRET_KEY
JWT_SECRET=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Set these manually
XAI_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

MAX_WORKERS=4
REDIS_POOL_SIZE=20
HTTP_TIMEOUT=30
MODEL_RETRAIN_INTERVAL=3600
MIN_SAMPLES_FOR_TRAINING=100

GRAFANA_PASSWORD=$GRAFANA_PASSWORD

DEBUG=false
DEVELOPMENT=false
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    
    chmod 600 $PROJECT_DIR/.env
    chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/.env
    
    log "Security keys generated and saved to $PROJECT_DIR/.env"
    warning "Please update XAI_API_KEY, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID in $PROJECT_DIR/.env"
}

# Setup SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    read -p "Enter your domain name (or press Enter to skip SSL setup): " DOMAIN
    
    if [[ -n "$DOMAIN" ]]; then
        # Generate Let's Encrypt certificate
        certbot certonly --nginx --non-interactive --agree-tos \
            --email admin@$DOMAIN \
            -d $DOMAIN
        
        # Copy certificates to project directory
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $PROJECT_DIR/ssl/
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $PROJECT_DIR/ssl/
        
        # Set permissions
        chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/ssl/*
        chmod 644 $PROJECT_DIR/ssl/fullchain.pem
        chmod 600 $PROJECT_DIR/ssl/privkey.pem
        
        log "SSL certificates configured for $DOMAIN"
    else
        warning "SSL setup skipped - using self-signed certificates"
        
        # Generate self-signed certificate
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout $PROJECT_DIR/ssl/privkey.pem \
            -out $PROJECT_DIR/ssl/fullchain.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        
        chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/ssl/*
        chmod 644 $PROJECT_DIR/ssl/fullchain.pem
        chmod 600 $PROJECT_DIR/ssl/privkey.pem
    fi
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    case $OS in
        ubuntu|debian)
            ufw --force enable
            ufw default deny incoming
            ufw default allow outgoing
            ufw allow ssh
            ufw allow 80/tcp
            ufw allow 443/tcp
            ufw allow 8080/tcp  # Application port
            ufw allow 3000/tcp  # Grafana
            ufw allow 9090/tcp  # Prometheus
            ;;
        centos|rhel|fedora)
            systemctl start firewalld
            systemctl enable firewalld
            firewall-cmd --permanent --add-service=ssh
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --permanent --add-port=8080/tcp
            firewall-cmd --permanent --add-port=3000/tcp
            firewall-cmd --permanent --add-port=9090/tcp
            firewall-cmd --reload
            ;;
    esac
    
    log "Firewall configured"
}

# Deploy application
deploy_application() {
    log "Deploying application..."
    
    # Copy application files
    cp -r ./* $PROJECT_DIR/
    chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR
    
    # Navigate to project directory
    cd $PROJECT_DIR
    
    # Build and start containers
    docker-compose build --no-cache
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to start..."
    sleep 30
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        log "Application deployed successfully"
    else
        error "Some services failed to start"
        docker-compose logs
        exit 1
    fi
}

# Create systemd service
create_systemd_service() {
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/${PROJECT_NAME}.service << EOF
[Unit]
Description=Miner Detector Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0
User=root

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable ${PROJECT_NAME}.service
    
    log "Systemd service created and enabled"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring and logging..."
    
    # Configure log rotation
    cat > /etc/logrotate.d/${PROJECT_NAME} << EOF
$LOG_DIR/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload ${PROJECT_NAME} 2>/dev/null || true
    endscript
}
EOF
    
    # Create monitoring script
    cat > /usr/local/bin/${PROJECT_NAME}-monitor << 'EOF'
#!/bin/bash
# Monitor Miner Detector services

check_service() {
    local service=$1
    if docker-compose -f /opt/miner-detector/docker-compose.yml ps $service | grep -q "Up"; then
        echo "✓ $service is running"
        return 0
    else
        echo "✗ $service is not running"
        return 1
    fi
}

cd /opt/miner-detector

echo "=== Miner Detector Service Status ==="
echo "Timestamp: $(date)"
echo

# Check all services
services=("redis" "postgres" "app" "celery_worker" "celery_beat" "nginx" "prometheus" "grafana")
all_ok=true

for service in "${services[@]}"; do
    if ! check_service $service; then
        all_ok=false
    fi
done

echo
if $all_ok; then
    echo "✓ All services are running properly"
    exit 0
else
    echo "✗ Some services are not running"
    echo "Run 'docker-compose logs' for more details"
    exit 1
fi
EOF
    
    chmod +x /usr/local/bin/${PROJECT_NAME}-monitor
    
    # Add to crontab for regular monitoring
    echo "*/5 * * * * root /usr/local/bin/${PROJECT_NAME}-monitor >> $LOG_DIR/monitor.log 2>&1" >> /etc/crontab
    
    log "Monitoring configured"
}

# Backup setup
setup_backup() {
    log "Setting up backup system..."
    
    cat > /usr/local/bin/${PROJECT_NAME}-backup << EOF
#!/bin/bash
# Backup script for Miner Detector

BACKUP_DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_\$BACKUP_DATE"

mkdir -p \$BACKUP_PATH

# Backup database
docker exec miner_detector_db pg_dump -U mineruser minerdb > \$BACKUP_PATH/database.sql

# Backup Redis data
docker exec miner_detector_redis redis-cli --rdb /data/dump.rdb
docker cp miner_detector_redis:/data/dump.rdb \$BACKUP_PATH/redis.rdb

# Backup application data
cp -r $PROJECT_DIR/data \$BACKUP_PATH/
cp $PROJECT_DIR/.env \$BACKUP_PATH/

# Compress backup
tar -czf \$BACKUP_PATH.tar.gz -C $BACKUP_DIR backup_\$BACKUP_DATE
rm -rf \$BACKUP_PATH

# Remove old backups (keep 30 days)
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: \$BACKUP_PATH.tar.gz"
EOF
    
    chmod +x /usr/local/bin/${PROJECT_NAME}-backup
    
    # Schedule daily backups
    echo "0 2 * * * root /usr/local/bin/${PROJECT_NAME}-backup >> $LOG_DIR/backup.log 2>&1" >> /etc/crontab
    
    log "Backup system configured"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait for application to start
    sleep 10
    
    # Check if application is responding
    if curl -f http://localhost:8080/api/status > /dev/null 2>&1; then
        log "✓ Application health check passed"
    else
        error "✗ Application health check failed"
        return 1
    fi
    
    # Check database connection
    if docker exec miner_detector_db pg_isready -U mineruser -d minerdb > /dev/null 2>&1; then
        log "✓ Database health check passed"
    else
        error "✗ Database health check failed"
        return 1
    fi
    
    # Check Redis
    if docker exec miner_detector_redis redis-cli ping | grep -q PONG; then
        log "✓ Redis health check passed"
    else
        error "✗ Redis health check failed"
        return 1
    fi
    
    log "All health checks passed"
}

# Print deployment summary
print_summary() {
    log "Deployment completed successfully!"
    echo
    echo "=== Deployment Summary ==="
    echo "Project Directory: $PROJECT_DIR"
    echo "Log Directory: $LOG_DIR"
    echo "Backup Directory: $BACKUP_DIR"
    echo
    echo "=== Service URLs ==="
    echo "Application: http://localhost:8080"
    echo "Grafana: http://localhost:3000 (admin / $GRAFANA_PASSWORD)"
    echo "Prometheus: http://localhost:9090"
    echo
    echo "=== Useful Commands ==="
    echo "Check status: /usr/local/bin/${PROJECT_NAME}-monitor"
    echo "View logs: docker-compose -f $PROJECT_DIR/docker-compose.yml logs"
    echo "Restart services: systemctl restart ${PROJECT_NAME}"
    echo "Create backup: /usr/local/bin/${PROJECT_NAME}-backup"
    echo
    echo "=== Next Steps ==="
    echo "1. Update API keys in $PROJECT_DIR/.env"
    echo "2. Configure domain and SSL certificates if needed"
    echo "3. Review and adjust firewall rules"
    echo "4. Set up external monitoring (optional)"
    echo
    warning "Remember to securely store the generated passwords!"
}

# Main installation function
main() {
    log "Starting Miner Detector deployment..."
    
    check_root
    detect_os
    install_dependencies
    create_user
    setup_directories
    setup_docker
    generate_secrets
    setup_ssl
    setup_firewall
    deploy_application
    create_systemd_service
    setup_monitoring
    setup_backup
    health_check
    print_summary
    
    log "Deployment completed successfully!"
}

# Parse command line arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    status)
        /usr/local/bin/${PROJECT_NAME}-monitor
        ;;
    backup)
        /usr/local/bin/${PROJECT_NAME}-backup
        ;;
    logs)
        docker-compose -f $PROJECT_DIR/docker-compose.yml logs -f
        ;;
    restart)
        systemctl restart ${PROJECT_NAME}
        ;;
    stop)
        systemctl stop ${PROJECT_NAME}
        ;;
    start)
        systemctl start ${PROJECT_NAME}
        ;;
    update)
        cd $PROJECT_DIR
        git pull
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    *)
        echo "Usage: $0 {deploy|status|backup|logs|restart|stop|start|update}"
        exit 1
        ;;
esac