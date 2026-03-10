# 代理配置指南

本项目支持通过代理访问 YouTube，以下是配置方法。

## 方法 1: 环境变量（推荐）

### HTTP/HTTPS 代理

```bash
# 临时设置（当前终端有效）
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export NO_PROXY=localhost,127.0.0.1

# 运行程序
python3 main.py monitor
```

### SOCKS5 代理

```bash
export ALL_PROXY=socks5://127.0.0.1:1080
```

### 永久配置（写入 .env 文件）

编辑 `.env` 文件：

```env
# 代理配置（二选一）

# HTTP 代理
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# 或 SOCKS5 代理
# ALL_PROXY=socks5://127.0.0.1:1080
```

## 方法 2: 系统级代理

### Ubuntu 系统代理

```bash
# 设置系统代理
sudo nano /etc/environment

# 添加以下内容
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

## 方法 3: Docker 代理

如果使用 Docker，在 `docker-compose.yml` 中配置：

```yaml
services:
  video-agent:
    environment:
      - HTTP_PROXY=http://host.docker.internal:7890
      - HTTPS_PROXY=http://host.docker.internal:7890
```

## 常见代理工具端口

| 工具 | HTTP 端口 | SOCKS5 端口 |
|------|-----------|-------------|
| **Clash** | 7890 | 7890 |
| **Clash Verge** | 7890 | 7890 |
| **v2rayN** | 10809 | 10808 |
| **SSR** | 1080 | 1080 |
| **Shadowsocks** | - | 1080 |

## 验证代理

```bash
# 检查代理环境变量
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 测试 YouTube 连接
curl -I --proxy $HTTP_PROXY https://www.youtube.com

# 或测试 yt-dlp
yt-dlp --proxy $HTTP_PROXY --list-formats "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## 故障排查

### 连接超时

```
ERROR: Unable to download webpage: <urlopen error timed out>
```

**解决方案**:
1. 检查代理是否正常运行
2. 检查代理地址和端口是否正确
3. 尝试更换代理节点

### SSL 证书错误

```
ERROR: Unable to download webpage: SSL certificate verify failed
```

**解决方案**:
```bash
# 跳过证书验证（不推荐长期使用）
export PYTHONWARNINGS="ignore:Unverified HTTPS request"
```

### Docker 中无法连接代理

如果代理运行在宿主机，Docker 容器内使用：

```bash
# Linux
export HTTP_PROXY=http://172.17.0.1:7890

# macOS/Windows
export HTTP_PROXY=http://host.docker.internal:7890
```

## 配置示例

### 使用 Clash

```bash
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
python3 main.py monitor
```

### 使用 v2rayN

```bash
export HTTP_PROXY=http://127.0.0.1:10809
export HTTPS_PROXY=http://127.0.0.1:10809
python3 main.py monitor
```

### 使用 Shadowsocks

```bash
export ALL_PROXY=socks5://127.0.0.1:1080
python3 main.py monitor
```
