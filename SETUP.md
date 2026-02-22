# Habbo Hotel Nitro-Docker Setup Guide

Complete setup guide for running a Habbo Hotel private server using Arcturus Morningstar 4.0, Nitro React client, and AtomCMS.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Issues & Fixes](#issues--fixes)
- [Configuration](#configuration)
- [Accessing the Hotel](#accessing-the-hotel)
- [Troubleshooting](#troubleshooting)

## Overview

This setup includes:
- **Arcturus Morningstar 4.0** - Java-based Habbo emulator
- **Nitro Client** - React/TypeScript-based Habbo client
- **AtomCMS** - PHP Laravel-based content management system
- **MySQL Database** - Data storage
- **Asset Server** - Serves game assets (furniture, clothing, pets)
- **Image Servers** - Avatar and badge rendering

## Architecture

```
┌─────────────────┐
│   AtomCMS       │  Port 8081 (PHP/Laravel)
│   Login & SSO   │  Generates authentication tokens
└────────┬────────┘
         │ SSO Token
         ▼
┌─────────────────┐
│  Nitro Client   │  Port 3000 (React/TypeScript)
│  Frontend UI    │  Served via nginx
└────────┬────────┘
         │ WebSocket (ws://localhost:2096)
         ▼
┌─────────────────┐
│   Arcturus MS4  │  Port 3000 (TCP), 2096 (WebSocket)
│   Game Server   │  Java emulator
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MySQL Database │  Port 3306
│   Data Storage  │
└─────────────────┘
```

## Prerequisites

- Docker Desktop (for Apple Silicon/ARM64 compatible)
- Git
- ~10GB free disk space for assets
- Ports available: 3000, 3001, 3306, 8080, 8081, 8082

## Initial Setup

### 1. Clone and Configure

```bash
# Navigate to project
cd /Users/balaa/src/habbo/nitro-docker

# Copy example configurations
cp .env.example .env
cp .cms.env.example .cms.env
```

### 2. Database Configuration

Edit `.env`:
```bash
DB_HOST=db
DB_PORT=3306
DB_NAME=arcturus
DB_USER=arcturus_user
DB_PASS=arcturus_pw
```

### 3. Download and Build Assets

This step converts SWF files to Nitro-compatible format and takes 30-60 minutes.

```bash
docker compose up assets -d
docker compose logs -f assets
```

Expected output:
- 7750+ furniture items converted
- 2057 clothing items converted
- 35 pet types converted

Assets will be available at `http://127.0.0.1:8080/assets`

### 4. Initialize Database

```bash
# Start database
docker compose up db -d

# Wait for database to be ready
sleep 10

# Initialize with base schema
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus < sqlupdates/3_0_0-to-4_0_0.sql

# Apply permissions update
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus < sqlupdates/4_0_0_permissions.sql
```

### 5. Configure Emulator

Edit `emulator.properties`:
```properties
db.hostname=db
db.port=3306
db.username=arcturus_user
db.password=arcturus_pw
db.database=arcturus

hotel.websockets.whitelist=127.0.0.1,localhost,192.168.65.1
```

### 6. Build and Start Containers

```bash
# Build all containers
docker compose build

# Start all services
docker compose up -d

# Verify all containers are running
docker compose ps
```

Expected containers:
- db (MySQL)
- backup (Database backup)
- assets (Asset conversion/serving)
- imager (Avatar image generation)
- imgproxy (Image proxy)
- arcturus (Emulator)
- nitro (Client)
- cms (AtomCMS)

### 7. Create Admin User

```bash
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus -e "
INSERT INTO users (username, password, mail, account_created, rank, credits, pixels, points)
VALUES ('admin', 'admin', 'admin@localhost.com', UNIX_TIMESTAMP(), 7, 10000, 10000, 10000);
"
```

**Note:** Password will be properly hashed in the CMS setup step.

### 8. Setup AtomCMS

#### Generate Application Key

```bash
docker compose exec cms php artisan key:generate --show
```

Copy the generated key to `.cms.env`:
```bash
APP_KEY=base64:YOUR_GENERATED_KEY_HERE
```

#### Run Migrations and Seeders

```bash
docker compose exec cms php artisan migrate --seed --force
```

This creates:
- 73 database migrations
- Website settings
- Languages (English, German, Spanish, etc.)
- Permissions
- Default articles
- Shop categories
- Rules

#### Configure Website Settings

```bash
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus -e "
UPDATE website_settings SET \`value\` = 'http://127.0.0.1:8080/api/imager/?figure=' WHERE \`key\` = 'avatar_imager';
UPDATE website_settings SET \`value\` = 'http://127.0.0.1:8080/swf/c_images/album1584' WHERE \`key\` = 'badges_path';
UPDATE website_settings SET \`value\` = 'http://127.0.0.1:8080/usercontent/badgeparts/generated' WHERE \`key\` = 'group_badge_path';
UPDATE website_settings SET \`value\` = 'http://127.0.0.1:8080/swf/dcr/hof_furni' WHERE \`key\` = 'furniture_icons_path';
UPDATE website_settings SET \`value\` = '/housekeeping' WHERE \`key\` = 'housekeeping_url';
UPDATE website_settings SET \`value\` = 'arcturus' WHERE \`key\` = 'rcon_ip';
UPDATE website_settings SET \`value\` = '3001' WHERE \`key\` = 'rcon_port';
UPDATE website_settings SET \`value\` = 'http://127.0.0.1:3000' WHERE \`key\` = 'nitro_path';
"
```

#### Get Installation Key

```bash
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus -e "SELECT installation_key FROM website_installation;"
```

Save this key - you'll need it for first-time CMS access.

#### Fix Admin Password Hash

```bash
# Generate bcrypt hash
HASH=$(docker compose exec cms php -r "echo password_hash('admin', PASSWORD_BCRYPT);")

# Update admin user with proper hash
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus -e "
UPDATE users SET password = '$HASH' WHERE username = 'admin';
"
```

#### Clear Laravel Cache

```bash
docker compose exec cms php artisan cache:clear
docker compose exec cms php artisan config:clear
docker compose exec cms php artisan view:clear
```

## Issues & Fixes

### Issue 1: ARM64/Apple Silicon Compatibility

**Problem:** `amazoncorretto:19-alpine` not available for ARM64

**Fix:** Modified `arcturus/Dockerfile`
```dockerfile
# Changed from:
FROM amazoncorretto:19-alpine
RUN apk add --no-cache mariadb-client bash

# To:
FROM amazoncorretto:19
RUN yum install -y mariadb bash && yum clean all
```

### Issue 2: Node.js Native Module Compilation

**Problem:** Missing Python for node-gyp during Nitro build

**Fix:** Modified `nitro/Dockerfile`
```dockerfile
# Changed from:
RUN apk add --no-cache git

# To:
RUN apk add --no-cache git python3 make g++
```

### Issue 3: Content Security Policy Blocking

**Problem:** Browser blocking JavaScript eval in Nitro client

**Fix:** Modified `nitro/nginx.conf`
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: http: https:; connect-src 'self' ws: wss: http: https:; font-src 'self' data:;" always;
```

### Issue 4: Database Name Mismatch

**Problem:** SQL file referenced 'aurora' instead of 'arcturus'

**Fix:** Modified `sqlupdates/4_0_0_permissions.sql`
```sql
# Changed from:
INSERT INTO 'aurora'.'emulator_texts'

# To:
INSERT IGNORE INTO 'arcturus'.'emulator_texts'
```

### Issue 5: PHP Version Compatibility

**Problem:** PHP 8.5+ too new for AtomCMS dependencies

**Fix:** Modified `atomcms/Dockerfile`
```dockerfile
# Changed from:
FROM php:8-cli-alpine AS composer-builder
FROM serversideup/php:8-fpm-nginx-alpine

# To:
FROM php:8.4-cli-alpine AS composer-builder
FROM serversideup/php:8.4-fpm-nginx-alpine
```

### Issue 6: WebSocket Connection Using Wrong Host

**Problem:** Client trying to connect to 127.0.0.1 instead of localhost

**Fix:** Updated configuration files

`nitro/renderer-config.json`:
```json
{
  "socket.url": "ws://localhost:2096"
}
```

`nitro/ui-config.json`:
```json
{
  "socket.url": "ws://localhost:2096",
  ...
}
```

### Issue 7: Handshake Failed - Missing SSO Flow

**Problem:** Direct access to Nitro client bypassed authentication

**Solution:** Access client through CMS which generates SSO tokens
- Don't access http://127.0.0.1:3000 directly
- Use CMS hotel page at http://localhost:8081/game/nitro
- CMS generates SSO ticket and passes to client
- Client authenticates with Arcturus using ticket

### Issue 8: CMS Cache Blocking Updated Settings

**Problem:** Database settings updated but CMS still using old cached values

**Fix:** Clear all Laravel caches after configuration changes
```bash
docker compose exec cms php artisan cache:clear
docker compose exec cms php artisan config:clear
docker compose exec cms php artisan view:clear
```

## Configuration

### Environment Variables (.env)

```bash
# Database
DB_HOST=db
DB_PORT=3306
DB_NAME=arcturus
DB_USER=arcturus_user
DB_PASS=arcturus_pw

# Emulator
RCON_HOST=arcturus
RCON_PORT=3001
```

### CMS Environment (.cms.env)

```bash
APP_NAME=Laravel
APP_ENV=production
APP_KEY=base64:YOUR_KEY_HERE
APP_DEBUG=false
APP_URL=http://127.0.0.1:8081

# Database (must match .env)
DB_CONNECTION=mysql
DB_HOST=db
DB_PORT=3306
DB_DATABASE=arcturus
DB_USERNAME=arcturus_user
DB_PASSWORD=arcturus_pw

# RCON Connection
RCON_HOST=arcturus
RCON_PORT=3001

# Nitro Client Path
NITRO_CLIENT_PATH=http://127.0.0.1:3000

# Language & Theme
APP_LOCALE=de
THEME=dusk
```

### Nitro Client Configuration

`renderer-config.json`:
```json
{
  "socket.url": "ws://localhost:2096",
  "asset.url": "http://127.0.0.1:8080/assets",
  "image.library.url": "http://127.0.0.1:8080/swf/c_images/",
  "hof.furni.url": "http://127.0.0.1:8080/swf/dcr/hof_furni/"
}
```

`ui-config.json`:
```json
{
  "socket.url": "ws://localhost:2096",
  "url.prefix": "http://127.0.0.1:8081"
}
```

### Emulator Properties

`emulator.properties`:
```properties
# Database
db.hostname=db
db.port=3306
db.username=arcturus_user
db.password=arcturus_pw
db.database=arcturus
db.params=useSSL=false

# WebSocket
hotel.websockets.whitelist=127.0.0.1,localhost,192.168.65.1

# Ports
game.host=0.0.0.0
game.port=3000
rcon.host=127.0.0.1
rcon.port=3001
```

## Accessing the Hotel

### 1. Access AtomCMS

URL: http://localhost:8081

On first access:
- Enter the installation key from database
- Log in with: `admin` / `admin`

### 2. Enter the Hotel

After logging into CMS:
1. Click the "Hotel" button in navigation
2. This redirects to: http://localhost:8081/game/nitro
3. CMS generates SSO ticket automatically
4. Nitro client loads with authentication
5. Client connects to Arcturus via WebSocket
6. You're now in the hotel!

### 3. Access Housekeeping (Admin Panel)

URL: http://localhost:8081/housekeeping

Features:
- User management
- Room management
- Catalog editor
- Badge creator
- News/articles
- System settings

### 4. Direct URLs

- **CMS Website:** http://localhost:8081
- **Nitro Client (standalone):** http://localhost:3000
- **Assets Server:** http://127.0.0.1:8080
- **Avatar Imager:** http://127.0.0.1:8080/api/imager/?figure=
- **Image Proxy:** http://localhost:8082

## Troubleshooting

### Client Shows "Handshake Failed"

**Causes:**
1. Accessing client directly instead of through CMS
2. Cached configuration in Laravel
3. WebSocket connection blocked

**Solutions:**
```bash
# Clear Laravel cache
docker compose exec cms php artisan cache:clear
docker compose exec cms php artisan config:clear
docker compose exec cms php artisan view:clear

# Restart containers
docker compose restart arcturus nitro cms

# Always access via CMS, not direct URL
# Use: http://localhost:8081 → Click "Hotel"
# Don't use: http://localhost:3000
```

### Database Connection Errors

```bash
# Check database is running
docker compose ps db

# Check database logs
docker compose logs db

# Restart database
docker compose restart db

# Wait 10 seconds for it to be ready
sleep 10

# Restart dependent services
docker compose restart arcturus cms
```

### Assets Not Loading

```bash
# Check assets container
docker compose logs assets

# Verify assets are built
curl http://127.0.0.1:8080/assets/

# Rebuild assets if needed
docker compose up assets -d
```

### Emulator Won't Start

```bash
# Check logs
docker compose logs arcturus

# Common issues:
# 1. Database not ready - wait and restart
docker compose restart arcturus

# 2. Port conflict - check nothing else on port 3000
lsof -i :3000

# 3. Configuration error - verify emulator.properties
docker compose exec arcturus cat config.ini
```

### CMS 404 Errors

```bash
# Clear all caches
docker compose exec cms php artisan optimize:clear

# Check storage permissions
docker compose exec cms chmod -R 775 storage bootstrap/cache

# Verify routes
docker compose exec cms php artisan route:list | grep game
```

### WebSocket Connection Failed

Check browser console for errors:

```javascript
// Should see:
WebSocket connection to 'ws://localhost:2096/' established

// If seeing socket.io or HTTP:
// Clear browser cache (hard refresh: Cmd+Shift+R)
// Verify renderer-config.json and ui-config.json have socket.url
```

### Viewing Logs

```bash
# All containers
docker compose logs -f

# Specific container
docker compose logs -f arcturus
docker compose logs -f nitro
docker compose logs -f cms

# Last N lines
docker compose logs --tail 50 arcturus
```

## Default Credentials

### Admin User
- **Username:** admin
- **Password:** admin
- **Rank:** 7 (Owner)
- **Starting Credits:** 10,000
- **Starting Pixels:** 10,000
- **Starting Points:** 10,000

### Database
- **Host:** db (or localhost:3306 from host)
- **Username:** arcturus_user
- **Password:** arcturus_pw
- **Database:** arcturus

## Useful Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Rebuild specific service
docker compose build arcturus
docker compose up -d arcturus

# View running containers
docker compose ps

# Access MySQL
docker compose exec db mysql -u arcturus_user -parcturus_pw arcturus

# Access CMS shell
docker compose exec cms bash

# Run artisan commands
docker compose exec cms php artisan [command]

# Check WebSocket connections
docker compose exec arcturus grep -i "websocket" logs/arcturus.log
```

## Asset Statistics

After successful asset conversion:
- **Furniture Items:** 7,750+
- **Clothing Items:** 2,057
- **Pet Types:** 35
- **Total Asset Size:** ~5GB

## Performance Notes

- **Memory Usage:** ~2GB RAM for all containers
- **Startup Time:** ~30 seconds for full stack
- **Asset Build Time:** 30-60 minutes (one-time)
- **Recommended:** 4+ CPU cores, 8GB+ RAM

## Development Tips

### Hot Reload Nitro Client

```bash
# Stop nginx container
docker compose stop nitro

# Run development server on host
cd nitro
npm run dev
```

### Database Backups

Automatic backups run via the `backup` container.

Manual backup:
```bash
docker compose exec db mysqldump -u arcturus_user -parcturus_pw arcturus > backup.sql
```

Restore:
```bash
docker compose exec -T db mysql -u arcturus_user -parcturus_pw arcturus < backup.sql
```

### Update Arcturus to Latest

Edit `arcturus/Dockerfile`:
```dockerfile
ARG COMMIT=53ea66d  # Change to latest commit hash
```

Then rebuild:
```bash
docker compose build arcturus
docker compose up -d arcturus
```

## Security Notes

⚠️ **For Development/Local Use Only**

Before deploying publicly:
1. Change all default passwords
2. Use strong APP_KEY in .cms.env
3. Enable HTTPS/SSL
4. Configure firewall rules
5. Set APP_DEBUG=false
6. Enable CSRF protection
7. Configure rate limiting
8. Regular security updates

## Support & Resources

- **Arcturus MS4:** https://git.krews.org/morningstar/Arcturus-Community
- **Nitro Client:** https://github.com/nitro-renderer/nitro-react
- **AtomCMS:** https://github.com/ObjectRetros/atomcms
- **Docker Compose:** https://docs.docker.com/compose/

## License

This setup uses multiple open-source projects, each with their own licenses. Refer to individual project repositories for license details.

---

**Setup completed successfully on:** 2026-02-22
**Platform:** macOS (Apple Silicon/ARM64)
**Docker Version:** Compatible with ARM64
**Total Setup Time:** ~2 hours (including asset build)
