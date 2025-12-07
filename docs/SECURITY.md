# 安全部署指南

## 问题：.env 文件中的密钥安全性

你说得对，直接在 .env 中存储密钥并注入到容器环境变量有安全风险：

1. **.env 文件可能被意外提交到 Git**
2. **环境变量可通过 `docker inspect` 查看**
3. **容器内进程可以读取所有环境变量**

---

## 解决方案

### 方案一：Docker Secrets（推荐用于 Docker Swarm）

```yaml
# docker-compose.prod.yml
services:
  app:
    secrets:
      - dashscope_api_key
      - amap_api_key
    environment:
      - DASHSCOPE_API_KEY_FILE=/run/secrets/dashscope_api_key

secrets:
  dashscope_api_key:
    file: ./secrets/dashscope_api_key.txt
```

### 方案二：云服务商密钥管理（推荐用于云部署）

**阿里云 KMS + 配置中心：**
```python
# 从阿里云配置中心读取
from alibabacloud_kms import Client

def get_secret(key_name):
    client = Client(region_id="cn-hangzhou")
    return client.get_secret_value(secret_name=key_name)

# 启动时获取密钥
DASHSCOPE_API_KEY = get_secret("travelmind/dashscope_api_key")
```

### 方案三：HashiCorp Vault

```bash
# 存储密钥
vault kv put secret/travelmind \
  dashscope_api_key=sk-xxx \
  amap_api_key=xxx

# 应用读取
vault kv get -field=dashscope_api_key secret/travelmind
```

### 方案四：运行时注入（简单有效）

**不在 docker-compose.yml 中写死，启动时传入：**

```bash
# 方法 1：启动时传入环境变量
DASHSCOPE_API_KEY=sk-xxx docker-compose up -d

# 方法 2：使用 .env 文件但不提交到 Git（确保 .gitignore 包含 .env）

# 方法 3：从安全存储读取后导出
export DASHSCOPE_API_KEY=$(cat /secure/path/dashscope_key)
docker-compose up -d
```

---

## 本地开发 vs 生产环境

| 环境 | 方案 | 说明 |
|------|------|------|
| **本地开发** | .env 文件 | 简单方便，确保不提交 Git |
| **测试服务器** | 环境变量注入 | CI/CD 中配置 secrets |
| **生产环境** | 云密钥管理服务 | 阿里云 KMS / AWS Secrets Manager |

---

## 生产环境部署清单

### 1. 密钥管理
```bash
# 不要这样做 ❌
DASHSCOPE_API_KEY=sk-xxx  # 写在文件里

# 应该这样做 ✅
# 使用云服务商的密钥管理，或启动时注入
```

### 2. Docker 安全配置
```yaml
services:
  app:
    # 使用只读文件系统
    read_only: true
    tmpfs:
      - /tmp
    
    # 限制权限
    security_opt:
      - no-new-privileges:true
    
    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 3. 网络安全
```yaml
services:
  app:
    # 不暴露到公网，通过反向代理
    expose:
      - "8000"  # 只暴露给内部网络
    # ports: 不使用

  nginx:
    ports:
      - "443:443"  # 只有 nginx 对外
```

### 4. 日志脱敏
```python
# 确保日志不包含密钥
import structlog

def filter_secrets(logger, method_name, event_dict):
    # 过滤敏感字段
    for key in ['api_key', 'password', 'secret', 'token']:
        if key in event_dict:
            event_dict[key] = '***REDACTED***'
    return event_dict

structlog.configure(processors=[filter_secrets, ...])
```

---

## GitHub Actions CI/CD 安全配置

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        env:
          # 从 GitHub Secrets 读取
          DASHSCOPE_API_KEY: ${{ secrets.DASHSCOPE_API_KEY }}
          AMAP_API_KEY: ${{ secrets.AMAP_API_KEY }}
        run: |
          # 密钥通过环境变量传递，不写入文件
          ssh user@server "
            export DASHSCOPE_API_KEY='$DASHSCOPE_API_KEY'
            cd /app && docker-compose up -d
          "
```

---

## 总结

| 风险 | 解决方案 |
|------|---------|
| .env 被提交 Git | .gitignore 包含 .env，使用 .env.example 作为模板 |
| docker inspect 可见 | 使用 Docker Secrets 或云密钥服务 |
| 日志泄露 | 日志脱敏处理 |
| 网络暴露 | 反向代理 + 内网通信 |

**本地开发**：使用 .env 文件即可，简单方便
**生产环境**：使用云密钥管理服务（如阿里云 KMS）
