# Video Agent - 视频搬运/二创自动化工具

基于 Docker 运行的视频搬运自动化系统，支持 YouTube 监控、自动下载、AI 二创(翻译+配音)、多平台发布。

## 🎯 功能特性

- ✅ **YouTube 监控** - 自动检测指定频道新视频
- ✅ **智能下载** - yt-dlp 下载，支持字幕
- ✅ **AI 二创** - Whisper 语音转文字 + 翻译 + Edge-TTS 配音
- ✅ **多平台发布** - 抖音/B站/小红书自动发布
- ✅ **Web UI** - 实时监控任务状态
- ✅ **Docker 部署** - 不影响宿主机环境

## 🚀 快速开始

### 方式 1: Docker 运行 (推荐)

```bash
cd /root/video-agent

# 1. 编辑配置文件
vim config/config.yaml

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f video-agent

# 4. 打开 Web UI
open http://localhost:8080
```

### 方式 2: 本地 Python 运行

```bash
cd /root/video-agent

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 FFmpeg (系统依赖)
# macOS: brew install ffmpeg
# Ubuntu: apt-get install ffmpeg

# 运行
python main.py schedule
```

## ⚙️ 配置说明

所有配置集中在 `config/config.yaml`

### 1. 添加监控频道

```yaml
youtube:
  channels:
    - name: "频道名称"
      url: "https://www.youtube.com/@频道ID"
      language: "en"  # 视频语言
      category: "科技"  # 分类
      filter:
        min_duration: 300      # 最短5分钟
        max_duration: 1800     # 最长30分钟
        keywords: ["review"]   # 标题必须包含
        exclude_keywords: ["sponsor"]
```

### 2. 配置大模型接口

```yaml
openai:
  enabled: true
  api_key: "sk-your-key"
  base_url: "https://api.openai.com/v1"  # 可替换为代理
  model: "gpt-4o-mini"
```

### 3. 配置目标平台

```yaml
platforms:
  douyin:
    enabled: true
    login_type: "cookie"
    cookies: "sessionid=xxx; ..."  # 从浏览器复制
```

## 📋 命令行使用

```bash
# 初始化数据库
python main.py init

# 运行一次监控
python main.py monitor

# 启动定时监控 (后台运行)
python main.py schedule

# 处理指定视频
python main.py process VIDEO_ID

# 列出所有视频
python main.py list

# 启动 Web UI
python main.py webui
```

## 🐳 Docker 说明

### 是否影响系统环境?

**完全不影响！**

- 所有服务运行在 Docker 容器内
- 宿主机只需安装 Docker 和 Docker Compose
- 数据通过 Volume 挂载到宿主机 `./downloads`, `./outputs` 等目录
- 容器内运行使用非 root 用户

### 目录映射

```yaml
volumes:
  - ./config:/app/config:ro      # 配置
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

## 💰 AI 端到端实现成本估算

### 方案 A: AI 生成完整代码 (不推荐)

| 项目 | 费用 | 说明 |
|------|------|------|
| Claude Pro | $20/月 | 代码生成 |
| 调试时间 | 40-60 小时 | 反复修改 |
| **总成本** | **~$500-1000** | 时间成本极高 |

**问题**: AI 生成的代码需要大量调试，且难以处理复杂的浏览器自动化。

### 方案 B: 使用本项目 + AI 辅助优化 (推荐)

| 项目 | 费用 | 说明 |
|------|------|------|
| OpenAI API | $10-20/月 | 翻译 + 标题优化 |
| Whisper (本地) | $0 | 免费运行 |
| Edge TTS | $0 | 免费 |
| **总成本** | **~$20/月** | 仅需 API 费用 |

**建议**: 使用本项目作为基础框架，用 AI 辅助：
- 生成标题/标签
- 优化翻译质量
- 调试特定问题

## 📊 处理流程

```
YouTube 新视频
    ↓
[监控] yt-dlp 检测
    ↓
[下载] 1080p + 原字幕
    ↓
[识别] Whisper 语音转文字
    ↓
[翻译] OpenAI / DeepL 翻译
    ↓
[配音] Edge TTS 生成中文语音
    ↓
[合成] FFmpeg 合并视频+配音+字幕
    ↓
[发布] 抖音 / B站 / 小红书
```

## ⚠️ 版权/合规提醒

1. **不要纯搬运** - 必须进行实质性二创 (翻译+配音+剪辑)
2. **遵守平台规则** - 控制发布频率，避免封号
3. **内容审核** - 建议开启 `review_required: true` 人工审核
4. **合理使用** - 仅用于学习研究，遵守《著作权法》

## 🔧 故障排查

### FFmpeg 未找到
```bash
# Ubuntu/Debian
apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Whisper 模型下载慢
```bash
# 手动下载放到 ~/.cache/whisper/
# 或使用镜像源
export WHISPER_MODEL_DIR=/path/to/models
```

### 下载失败
- 检查网络是否可访问 YouTube
- 检查 yt-dlp 是否为最新版: `yt-dlp -U`

## 📝 TODO

- [ ] Web UI 完善
- [ ] 更多平台适配 (快手、视频号)
- [ ] GPT-SoVITS 音色克隆
- [ ] 自动剪辑 (去除静音片段)
- [ ] 数据分析面板

## 📄 License

仅供学习研究使用，请遵守相关法律法规。
