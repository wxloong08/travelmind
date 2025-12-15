# TravelMind 阿里云部署指南

## 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                      阿里云 ECS                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Docker                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────┐   │   │
│  │  │ Frontend │  │ Backend  │  │    Langfuse     │   │   │
│  │  │ (Nginx)  │  │ (FastAPI)│  │  (可观测性)     │   │   │
│  │  │  :80/443 │  │  :8000   │  │    :3000        │   │   │
│  │  └──────────┘  └──────────┘  └─────────────────┘   │   │
│  │                      │                │              │   │
│  │                      └────────────────┘              │   │
│  │                    travelmind-network               │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                    Security Group                           │
│                    (80, 443, 22)                            │
└─────────────────────────────────────────────────────────────┘
```

## 第一部分：服务器准备

### 1.1 购买阿里云 ECS

推荐配置：
| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 规格 | 2核4G 或 4核8G | 中小流量 2核4G 足够 |
| 系统 | Ubuntu 22.04 LTS | 或 CentOS 8+ |
| 磁盘 | 40G+ SSD | 存储 Docker 镜像和数据 |
| 带宽 | 按量付费 5Mbps+ | 或固定带宽 |
| 地域 | 靠近用户的区域 | 如华东1(杭州) |

### 1.2 配置安全组

入方向规则：
```
端口        协议    来源          说明
22          TCP     你的IP        SSH 访问
80          TCP     0.0.0.0/0     HTTP
443         TCP     0.0.0.0/0     HTTPS
8000        TCP     你的IP        API 测试（可选）
3000        TCP     你的IP        Langfuse（可选）
```

### 1.3 连接服务器

```bash
ssh root@你的服务器IP
```

---

## 第二部分：环境安装

### 2.1 更新系统

```bash
# Ubuntu
apt update && apt upgrade -y

# CentOS
yum update -y
```

### 2.2 安装 Docker

```bash
# Ubuntu 一键安装
curl -fsSL https://get.docker.com | sh

# 启动 Docker
systemctl start docker
systemctl enable docker

# 验证安装
docker --version
docker compose version
```

### 2.3 安装 Git（可选）

```bash
apt install -y git
```

---

## 第三部分：部署 TravelMind

### 3.1 上传项目文件

**方式一：使用 scp 上传压缩包**
```bash
# 本地执行
scp travelmind.zip root@你的服务器IP:/root/

# 服务器上解压
cd /root
unzip travelmind.zip
mv travelmind /opt/travelmind
```

**方式二：使用 Git 克隆（如果有仓库）**
```bash
cd /opt
git clone https://github.com/your-username/travelmind.git
```

### 3.2 配置环境变量

```bash
cd /opt/travelmind

# 复制环境变量模板
cp .env.example .env

# 编辑配置
nano .env
```

**必须配置的变量：**
```env
# 基础配置
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# LLM 配置【必须】
DASHSCOPE_API_KEY=sk-your-key-here

# 外部 API【推荐】
AMAP_API_KEY=your-amap-key
BOCHA_API_KEY=your-bocha-key

# 端口配置
API_PORT=8000
LANGFUSE_PORT=3000
```

### 3.3 构建并启动服务

```bash
cd /opt/travelmind

# 构建镜像（首次需要几分钟）
docker compose build

# 启动所有服务
docker compose up -d

# 查看启动状态
docker compose ps

# 查看日志
docker compose logs -f app
```

### 3.4 验证部署

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 测试对话 API
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我规划北京3天游"}'
```

---

## 第四部分：部署前端

### 4.1 构建前端

```bash
cd /opt/travelmind/frontend

# 安装 Node.js（如果没有）
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 安装依赖并构建
npm install
npm run build
```

### 4.2 配置 Nginx

```bash
# 安装 Nginx
apt install -y nginx

# 创建配置文件
nano /etc/nginx/sites-available/travelmind
```

**Nginx 配置内容：**
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    # 前端静态文件
    location / {
        root /opt/travelmind/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
        
        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 86400s;
    }

    # Langfuse（可选，内部访问）
    location /langfuse/ {
        proxy_pass http://127.0.0.1:3000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

**启用配置：**
```bash
# 创建软链接
ln -s /etc/nginx/sites-available/travelmind /etc/nginx/sites-enabled/

# 删除默认配置
rm /etc/nginx/sites-enabled/default

# 测试配置
nginx -t

# 重启 Nginx
systemctl restart nginx
systemctl enable nginx
```

---

## 第五部分：配置 HTTPS（推荐）

### 5.1 申请免费 SSL 证书

```bash
# 安装 Certbot
apt install -y certbot python3-certbot-nginx

# 申请证书（需要域名已解析到服务器）
certbot --nginx -d your-domain.com
```

### 5.2 自动续期

```bash
# 测试续期
certbot renew --dry-run

# Certbot 会自动添加定时任务
```

---

## 第六部分：运维管理

### 6.1 常用命令

```bash
cd /opt/travelmind

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f          # 所有服务
docker compose logs -f app      # 仅后端

# 重启服务
docker compose restart app      # 重启后端
docker compose restart          # 重启所有

# 更新部署
git pull                        # 如果用 Git
docker compose build --no-cache
docker compose up -d
```

### 6.2 设置开机自启

```bash
# Docker 已默认开机启动
# 确保容器设置了 restart: unless-stopped
```

### 6.3 日志管理

```bash
# 查看 Docker 日志
docker compose logs --tail=100 app

# 配置日志轮转（可选）
nano /etc/docker/daemon.json
```

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### 6.4 监控告警（可选）

```bash
# 使用阿里云监控
# 或安装 Prometheus + Grafana
```

---

## 第七部分：安全加固

### 7.1 防火墙配置

```bash
# 安装 UFW
apt install -y ufw

# 配置规则
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https

# 启用防火墙
ufw enable
```

### 7.2 禁用 root SSH（推荐）

```bash
# 创建普通用户
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy

# 复制 SSH 密钥
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh

# 测试新用户登录后，禁用 root 登录
nano /etc/ssh/sshd_config
# 设置 PermitRootLogin no
systemctl restart sshd
```

### 7.3 密钥安全

```bash
# 不要在 .env 中存储敏感信息到 Git
# 使用阿里云 KMS 或 Secrets Manager（生产环境）

# 简单方案：限制 .env 权限
chmod 600 /opt/travelmind/.env
```

---

## 快速部署脚本

创建一键部署脚本 `deploy.sh`：

```bash
#!/bin/bash
set -e

echo "=== TravelMind 部署脚本 ==="

# 1. 更新系统
echo ">>> 更新系统..."
apt update && apt upgrade -y

# 2. 安装 Docker
echo ">>> 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
fi

# 3. 安装 Nginx
echo ">>> 安装 Nginx..."
apt install -y nginx

# 4. 进入项目目录
cd /opt/travelmind

# 5. 检查 .env
if [ ! -f .env ]; then
    echo "错误：请先配置 .env 文件"
    exit 1
fi

# 6. 构建并启动
echo ">>> 构建 Docker 镜像..."
docker compose build

echo ">>> 启动服务..."
docker compose up -d

# 7. 等待服务就绪
echo ">>> 等待服务启动..."
sleep 10

# 8. 健康检查
echo ">>> 健康检查..."
curl -f http://localhost:8000/api/v1/health || echo "警告：API 未就绪"

echo "=== 部署完成 ==="
echo "访问地址: http://$(curl -s ifconfig.me)"
```

运行：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 常见问题

### Q1: 容器启动失败
```bash
# 查看详细日志
docker compose logs app

# 常见原因：
# 1. API Key 未配置
# 2. 端口被占用
# 3. 内存不足
```

### Q2: 前端无法访问 API
```bash
# 检查 Nginx 配置
nginx -t
cat /var/log/nginx/error.log

# 检查后端是否运行
curl http://localhost:8000/api/v1/health
```

### Q3: Langfuse 启动慢
```bash
# 首次启动需要 1-2 分钟进行数据库迁移
docker compose logs -f langfuse
```

### Q4: 磁盘空间不足
```bash
# 清理 Docker
docker system prune -a

# 查看磁盘使用
df -h
docker system df
```

---

## 联系支持

部署遇到问题，请提供：
1. `docker compose ps` 输出
2. `docker compose logs app` 日志
3. 服务器配置信息