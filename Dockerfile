FROM python:3.11-slim-bookworm

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg (视频处理必需)
    ffmpeg \
    # yt-dlp 依赖
    wget \
    curl \
    # 字体
    fonts-noto-cjk \
    # 清理
    && rm -rf /var/lib/apt/lists/*

# 安装 yt-dlp
RUN wget -qO /usr/local/bin/yt-dlp https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p downloads outputs temp logs database

# 非 root 用户运行 (安全)
RUN useradd -m -u 1000 videoagent && \
    chown -R videoagent:videoagent /app
USER videoagent

# 启动命令
CMD ["python", "main.py"]
