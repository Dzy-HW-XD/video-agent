# Video Agent - 视频字幕翻译工具

简化版：YouTube 视频下载 + 字幕翻译 + 字幕版视频生成

**支持平台**: Ubuntu Linux (20.04/22.04/24.04)

---

## 🎯 功能特性

- ✅ **YouTube 下载** - 自动下载视频和字幕
- ✅ **字幕翻译** - 使用 LLM (Kimi/DeepSeek等) 翻译字幕
- ✅ **视频合成** - FFmpeg 合成带中文字幕的视频
- ✅ **Web UI** - 监控任务状态

---

## 📋 环境配置

### 系统要求

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| **操作系统** | Ubuntu 20.04+ | 运行平台 |
| **Python** | 3.10+ | 运行主程序 |
| **FFmpeg** | 4.0+ | 视频处理（必需）|

### 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3 python3-pip python3-venv git
```

### 2. 克隆项目

```bash
git clone https://github.com/Dzy-HW-XD/video-agent.git
cd video-agent
```

### 3. 安装 Python 依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置 API 密钥

**⚠️ 重要：不要直接修改 .env.example，而是创建自己的 .env 文件**

```bash
# 从模板创建配置文件
cp .env.github .env

# 编辑 .env 文件，填入你的 API Key
vim .env
```

需要配置的密钥：
- `MOONSHOT_API_KEY` - Kimi 大模型 API Key (https://platform.moonshot.cn/)

可选配置：
- `DEEPSEEK_API_KEY` - DeepSeek API (https://platform.deepseek.com/)
- `OPENAI_API_KEY` - OpenAI API (https://platform.openai.com/)

**安全提示：**
- `.env` 文件已被 `.gitignore` 忽略，不会上传到 GitHub
- 永远不要将真实的 API Key 提交到代码仓库

---

## 🚀 使用方法

### 快速开始 - 翻译单个视频

```bash
source venv/bin/activate

# 下载并翻译视频
python3 main.py download-translate "https://www.youtube.com/watch?v=VIDEO_ID"
```

输出文件将保存在 `outputs/` 目录。

### 其他命令

```bash
# 初始化数据库
python3 main.py init

# 监控配置的 YouTube 频道
python3 main.py monitor

# 启动定时监控
python3 main.py schedule

# 列出所有视频
python3 main.py list

# 启动 Web UI
python3 main.py webui
```

---

## 📁 项目结构

```
video-agent/
├── main.py                 # 主入口
├── subtitle_processor.py   # 字幕下载和翻译
├── config/
│   └── config.yaml         # 配置文件
├── core/
│   ├── monitor.py          # YouTube 监控
│   ├── downloader.py       # 视频下载
│   └── processor.py        # 视频合成
├── .env.github             # 环境变量模板（可提交）
├── .env                    # 真实配置（已忽略，勿提交）
├── .gitignore              # Git 忽略规则
├── downloads/              # 下载的视频
├── outputs/                # 输出的成品视频
└── logs/                   # 日志文件
```

---

## ⚙️ 配置说明

### 添加监控频道

编辑 `config/config.yaml`：

```yaml
youtube:
  channels:
    - name: "频道名称"
      url: "https://www.youtube.com/@ChannelName"
      language: "en"
      category: "科技"
      filter:
        min_duration: 300  # 最短5分钟
```

### 选择翻译引擎

编辑 `config/config.yaml`，启用一个 LLM：

```yaml
# 启用 Moonshot Kimi
moonshot:
  enabled: true
  api_key: "${MOONSHOT_API_KEY}"
  base_url: "https://api.moonshot.cn/v1"
  model: "moonshot-v1-8k"

# 其他设为 false
deepseek:
  enabled: false
```

---

## 🔒 安全最佳实践

1. **永远不要提交敏感信息**
   - API Key
   - 密码
   - 私钥

2. **使用环境变量**
   - 开发时使用 `.env` 文件
   - 生产环境使用系统环境变量

3. **保护 .env 文件**
   - 已配置 `.gitignore` 忽略 `.env`
   - 定期轮换 API Key

---

## ⚠️ 注意事项

1. **YouTube 限制**
   - 频繁下载可能触发 429 错误（请求过多）
   - 某些视频需要登录验证

2. **API 费用**
   - Kimi API: 按量计费，有免费额度
   - 监控使用量避免超额

3. **版权合规**
   - 仅用于学习研究
   - 遵守《著作权法》
   - 不要纯搬运，需进行实质性二创

---

## 📝 License

仅供学习研究使用，请遵守相关法律法规。
