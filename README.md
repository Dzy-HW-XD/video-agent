# Video Agent - 视频搬运/二创自动化工具

基于 Docker 运行的视频搬运自动化系统，支持 YouTube 监控、自动下载、AI 二创(翻译+配音)、多平台发布。

**当前版本**: 阿里云语音 + Kimi 大模型方案

---

## 🎯 功能特性

- ✅ **YouTube 监控** - 自动检测指定频道新视频
- ✅ **智能下载** - yt-dlp 下载，支持字幕
- ✅ **AI 二创** - 阿里云 ASR 语音转文字 + Kimi 翻译 + 阿里云 TTS 配音
- ✅ **多平台发布** - 抖音/B站/小红书自动发布
- ✅ **Web UI** - 实时监控任务状态
- ✅ **Docker 部署** - 不影响宿主机环境

---

## 📋 环境需求

### 1. 系统环境

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| **Python** | 3.10+ | 运行主程序 |
| **FFmpeg** | 4.0+ | 视频处理必需 |
| **Docker** | 20.10+ | Docker 部署方式 |
| **Docker Compose** | 2.0+ | Docker 部署方式 |

### 2. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install ffmpeg python@3.12
```

**Windows:**
- 下载 FFmpeg: https://ffmpeg.org/download.html
- 添加到系统 PATH

### 3. Python 虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或: venv\Scripts\activate  # Windows
```

---

## 🔑 API 配置需求

### 必需配置（当前方案）

| 服务 | 用途 | 获取地址 | 费用 |
|------|------|----------|------|
| **Moonshot Kimi** | 翻译、标题生成 | https://platform.moonshot.cn/ | 按量计费，有免费额度 |
| **阿里云 NLS** | ASR 语音识别 + TTS 语音合成 | https://nls-portal.console.aliyun.com/ | ¥1.8-4/万字 |

### 配置步骤

1. **Kimi (Moonshot)**
   - 注册账号 → 创建 API Key
   - 复制到 `.env` 的 `MOONSHOT_API_KEY`

2. **阿里云 NLS**
   - 开通服务 → 创建项目
   - 获取 `AppKey`
   - 在 RAM 控制台获取 `AccessKey ID` 和 `AccessKey Secret`
   - 给 RAM 用户授权 `AliyunNLSFullAccess`

### .env 文件配置

```bash
cp .env.example .env
vim .env
```

填写以下内容：
```env
# Kimi 大模型
MOONSHOT_API_KEY=sk-your-key-here

# 阿里云语音服务
ALIYUN_ACCESS_KEY_ID=your-access-key-id
ALIYUN_ACCESS_KEY_SECRET=your-access-key-secret
ALIYUN_TTS_APP_KEY=your-app-key
ALIYUN_ASR_APP_KEY=your-app-key

# Web UI 密码（可选）
WEBUI_PASSWORD=your-password
```

---

## 🚀 快速开始

### 方式 1: Docker 运行 (推荐)

```bash
# 1. 克隆项目
git clone https://github.com/Dzy-HW-XD/video-agent.git
cd video-agent

# 2. 配置环境变量
cp .env.example .env
vim .env  # 填入你的 API Key

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f video-agent

# 5. 打开 Web UI
open http://localhost:8080
```

### 方式 2: 本地 Python 运行

```bash
# 1. 克隆项目
git clone https://github.com/Dzy-HW-XD/video-agent.git
cd video-agent

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
vim .env  # 填入你的 API Key

# 5. 初始化数据库
python3 main.py init

# 6. 运行
python3 main.py schedule
```

---

## ⚙️ 配置说明

### 当前技术栈配置

**`config/config.yaml` 已配置为：**
- ✅ **翻译**: Moonshot Kimi (启用)
- ✅ **语音识别**: 阿里云 ASR (启用)
- ✅ **语音合成**: 阿里云 TTS - `zhimiao_emo` 情感版音色 (启用)
- ❌ 其他方案（DeepSeek、讯飞、Azure 等）均已禁用

### 修改音色

如需更换 TTS 音色，编辑 `config/config.yaml`：

```yaml
tts:
  aliyun:
    voice: "zhimiao_emo"  # 当前：知妙情感版女声
    # 可选:
    # "zhinan" - 知楠男声
    # "zhimao" - 知猫女声
    # "zhishu" - 知树童声
    # "zhistella" - 英文好
```

### 添加 YouTube 监控频道

```yaml
youtube:
  channels:
    - name: "Linus Tech Tips"
      url: "https://www.youtube.com/@LinusTechTips"
      language: "en"
      category: "科技"
      filter:
        min_duration: 300      # 最短5分钟
        max_duration: 1800     # 最长30分钟
```

---

## 📋 命令行使用

```bash
# 初始化数据库
python3 main.py init

# 运行一次监控（测试）
python3 main.py monitor

# 启动定时监控 (后台运行)
python3 main.py schedule

# 处理指定视频
python3 main.py process VIDEO_ID

# 列出所有视频
python3 main.py list

# 启动 Web UI
python3 main.py webui
```

---

## 🐳 Docker 说明

### 目录映射

```yaml
volumes:
  - ./config:/app/config:ro      # 配置（只读）
  - ./downloads:/app/downloads   # 下载的视频
  - ./outputs:/app/outputs       # 成品视频
  - ./logs:/app/logs             # 日志
  - ./database:/app/database     # 数据库
```

### 常用命令

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f

# 更新代码后重建
docker-compose up -d --build
```

---

## 📊 处理流程

```
YouTube 新视频
    ↓
[监控] yt-dlp 检测
    ↓
[下载] 1080p + 原字幕
    ↓
[识别] 阿里云 ASR 语音转文字
    ↓
[翻译] Kimi 大模型翻译
    ↓
[配音] 阿里云 TTS 生成中文语音
    ↓
[合成] FFmpeg 合并视频+配音+字幕
    ↓
[发布] 抖音 / B站 / 小红书
```

---

## 💰 成本估算

| 服务 | 费用 | 说明 |
|------|------|------|
| **Kimi** | 有免费额度 | 超出后约 ¥10-20/月 |
| **阿里云 ASR** | ¥1.8-3.5/小时 | 语音识别 |
| **阿里云 TTS** | ¥2-4/万字 | 语音合成 |
| **总计** | **~¥30-50/月** | 按中等使用量估算 |

---

## ⚠️ 版权/合规提醒

1. **不要纯搬运** - 必须进行实质性二创 (翻译+配音+剪辑)
2. **遵守平台规则** - 控制发布频率，避免封号
3. **内容审核** - 建议开启 `review_required: true` 人工审核
4. **合理使用** - 仅用于学习研究，遵守《著作权法》

---

## 🔧 故障排查

### FFmpeg 未找到
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### 阿里云权限错误
- 检查 RAM 用户是否已授权 `AliyunNLSFullAccess`
- 检查 AccessKey 是否正确

### Kimi API 错误
- 检查 `MOONSHOT_API_KEY` 是否有效
- 检查账户是否有余额或免费额度

---

## 📝 TODO

- [ ] Web UI 完善
- [ ] 更多平台适配 (快手、视频号)
- [ ] GPT-SoVITS 音色克隆
- [ ] 自动剪辑 (去除静音片段)
- [ ] 数据分析面板

---

## 📄 License

仅供学习研究使用，请遵守相关法律法规。
