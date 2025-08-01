# Discord Bot Deployment Guide for Raspberry Pi

This guide provides instructions for deploying the Discord bot on a Raspberry Pi, with optimizations for resource-constrained environments.

## System Requirements

### Minimum Requirements
- Raspberry Pi 3 Model B or newer
- 1GB RAM (2GB+ recommended)
- 8GB+ SD card (16GB+ recommended)
- Raspberry Pi OS Lite (32-bit or 64-bit)
- Internet connection

### Recommended Specifications
- Raspberry Pi 4 Model B with 2GB+ RAM
- 32GB Class 10 SD card
- Raspberry Pi OS 64-bit
- Wired internet connection for stability

## Installation Steps

### 1. Set Up Raspberry Pi OS

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
2. Insert your SD card into your computer
3. Open Raspberry Pi Imager and select:
   - OS: Raspberry Pi OS Lite (32-bit or 64-bit)
   - Storage: Your SD card
4. Click on the gear icon (advanced options) and:
   - Enable SSH
   - Set hostname (e.g., `discordbot`)
   - Set username and password
   - Configure WiFi (if not using Ethernet)
5. Click "Write" to flash the OS to the SD card
6. Insert the SD card into your Raspberry Pi and power it on

### 2. Update System and Install Dependencies

Connect to your Raspberry Pi via SSH:

```bash
ssh username@hostname.local
```

Update the system and install required packages:

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git sqlite3

# Install MySQL if you prefer it over SQLite (optional)
# sudo apt install -y mariadb-server
```

### 3. Clone the Repository

```bash
# Create directory for the bot
mkdir -p ~/discord_bot
cd ~/discord_bot

# Clone the repository
git clone https://github.com/yourusername/discord_bot.git .
```

### 4. Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add psutil for memory monitoring
pip install psutil
```

### 5. Configure the Bot for Raspberry Pi

Create a `.env` file with optimized settings for Raspberry Pi:

```bash
nano .env
```

Add the following content (adjust as needed):

```
# Discord Bot Settings
DISCORD_TOKEN=your_discord_token_here
GUILD_ID=your_guild_id_here
COMMAND_PREFIX=/

# Database Settings (SQLite recommended for Raspberry Pi)
DB_TYPE=sqlite
DB_SQLITE_PATH=database/discord_bot.db

# If using MySQL instead:
# DB_TYPE=mysql
# DB_HOST=localhost
# DB_PORT=3306
# DB_USER=discord_bot
# DB_PASSWORD=your_password_here
# DB_NAME=discord_bot_db
# DB_POOL_SIZE=3

# Role IDs
ADMIN_ROLE_ID=your_admin_role_id
MODERATOR_ROLE_ID=your_moderator_role_id
TRUSTED_ROLE_ID=your_trusted_role_id
BOT_OWNER_ID=your_user_id

# Logging Settings
LOG_LEVEL=INFO
LOG_CHANNEL_ID=your_log_channel_id
LOG_TO_FILE=true

# Raspberry Pi Optimizations
LIGHTWEIGHT_MODE=true
ENABLED_COGS=permissions,points,message_manager,logging_system
BACKGROUND_TASK_INTERVAL=120
MEMORY_LIMIT_MB=200
```

### 6. Test the Bot

Run the bot manually to ensure it works:

```bash
# Make sure you're in the bot directory with venv activated
python main.py
```

If everything is working correctly, you should see the bot come online in your Discord server.

## Setting Up Systemd Service for Auto-Start

Create a systemd service file to automatically start the bot on boot:

```bash
sudo nano /etc/systemd/system/discord-bot.service
```

Add the following content (adjust paths as needed):

```ini
[Unit]
Description=Discord Bot Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/discord_bot
ExecStart=/home/your_username/discord_bot/venv/bin/python /home/your_username/discord_bot/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=discord-bot
Environment="PATH=/home/your_username/discord_bot/venv/bin"

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-bot.service
sudo systemctl start discord-bot.service
```

Check the status of the service:

```bash
sudo systemctl status discord-bot.service
```

View logs:

```bash
sudo journalctl -u discord-bot.service -f
```

## SD Card Optimization Tips

Raspberry Pi's SD cards can wear out from frequent writes. Here are some tips to extend SD card life:

1. **Use SQLite instead of MySQL** for lower resource usage and fewer writes

2. **Disable file logging** if not needed by setting `LOG_TO_FILE=false` in your `.env` file

3. **Mount temporary directories in RAM**:
   ```bash
   # Add to /etc/fstab
   tmpfs /tmp tmpfs defaults,noatime,size=100M 0 0
   tmpfs /var/tmp tmpfs defaults,noatime,size=30M 0 0
   ```

4. **Enable ZRAM** to reduce swap usage:
   ```bash
   sudo apt install zram-tools
   sudo nano /etc/default/zramswap
   # Set: PERCENT=50
   sudo systemctl restart zramswap
   ```

5. **Reduce swappiness**:
   ```bash
   echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

6. **Use a high-quality SD card** (Class 10 or higher) from a reputable brand

## Performance Monitoring

### Checking Memory Usage

```bash
# Check bot's memory usage
ps -o pid,user,%mem,command ax | grep python

# Check system memory
free -h

# Monitor in real-time
top
```

### Checking CPU Usage

```bash
# Check CPU usage
mpstat

# Monitor in real-time with htop (install if needed)
sudo apt install htop
htop
```

### Checking Disk Usage

```bash
# Check disk space
df -h

# Check disk I/O
sudo apt install iotop
sudo iotop
```

## Troubleshooting

### Bot Crashes Due to Memory Issues

1. Enable lightweight mode: `LIGHTWEIGHT_MODE=true`
2. Reduce enabled cogs to only essential ones
3. Increase background task intervals: `BACKGROUND_TASK_INTERVAL=300`
4. Switch to SQLite if using MySQL: `DB_TYPE=sqlite`
5. Reduce connection pool size if using MySQL: `DB_POOL_SIZE=2`

### High CPU Usage

1. Increase background task intervals
2. Disable resource-intensive cogs (gambling, betting)
3. Reduce logging level: `LOG_LEVEL=WARNING`

### SD Card Corruption

1. Use a UPS (Uninterruptible Power Supply) to prevent power loss
2. Implement proper shutdown: `sudo shutdown -h now`
3. Consider using a USB drive for the database instead of the SD card

## Upgrading

To update the bot:

```bash
# Navigate to bot directory
cd ~/discord_bot

# Pull latest changes
git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Restart the service
sudo systemctl restart discord-bot.service
```

## Backup Strategy

Regularly back up your bot data:

```bash
# Create backup directory
mkdir -p ~/backups

# Backup SQLite database
cp ~/discord_bot/database/discord_bot.db ~/backups/discord_bot_$(date +%Y%m%d).db

# Backup .env file
cp ~/discord_bot/.env ~/backups/.env_$(date +%Y%m%d)

# Automate with cron
# crontab -e
# Add: 0 0 * * * cp ~/discord_bot/database/discord_bot.db ~/backups/discord_bot_$(date +\%Y\%m\%d).db
```

For MySQL:
```bash
# Backup MySQL database
mysqldump -u your_username -p discord_bot_db > ~/backups/discord_bot_$(date +%Y%m%d).sql
```