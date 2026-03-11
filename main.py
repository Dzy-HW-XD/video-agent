#!/usr/bin/env python3
"""
Video Agent - 视频搬运/二创自动化工具
主入口文件 - 简化版：YouTube字幕+翻译
"""
import asyncio
import sys
from pathlib import Path

# 先加载环境变量
from dotenv import load_dotenv
load_dotenv()

import click
import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.monitor import YouTubeMonitor
from core.downloader import VideoDownloader
from subtitle_processor import YouTubeSubtitleProcessor, process_video_with_youtube_subtitles
from database.models import init_database, Video, VideoStatus, get_session

console = Console()

# 配置日志
logger.remove()
logger.add(
    "logs/video-agent.log",
    rotation="100 MB",
    retention="7 days",
    level="INFO",
    encoding="utf-8"
)
logger.add(sys.stderr, level="INFO")


def load_config_with_env(config_path: str) -> dict:
    """加载配置并替换环境变量"""
    import os
    import re
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换 ${VAR_NAME} 为环境变量值
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value is None:
            print(f"警告: 环境变量 {var_name} 未设置")
            return match.group(0)  # 返回原始值
        return env_value
    
    content = re.sub(r'\$\{([^}]+)\}', replace_var, content)
    config = yaml.safe_load(content)
    
    # 调试输出
    for provider in ['moonshot', 'deepseek', 'openai']:
        if config.get(provider, {}).get('enabled'):
            api_key = config.get(provider, {}).get('api_key', '')
            print(f"使用 {provider} API: {api_key[:10]}..." if api_key else f"{provider} API key 未设置")
    
    return config


class VideoAgent:
    """视频 Agent 主类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = load_config_with_env(config_path)
        
        # 初始化组件
        self.monitor = YouTubeMonitor(config_path)
        self.downloader = VideoDownloader(self.config['system']['download_path'])
        
        # 获取 LLM 配置
        self.llm_config = self._get_llm_config()
        
        # 初始化数据库
        init_database(config_path)
        
        logger.info("Video Agent 初始化完成 (字幕翻译版)")
    
    def _get_llm_config(self) -> dict:
        """获取启用的 LLM 配置"""
        llm_providers = ['deepseek', 'zhipu', 'moonshot', 'dashscope', 'openai']
        for provider in llm_providers:
            if self.config.get(provider, {}).get('enabled'):
                return {'provider': provider, **self.config[provider]}
        raise ValueError("未启用任何大模型API")
    
    async def run_monitor_cycle(self):
        """运行一次监控循环"""
        console.print("\n[bold blue]🔍 检查 YouTube 新视频...[/bold blue]")
        
        # 1. 检查新视频
        new_videos = await self.monitor.check_all_channels()
        
        if not new_videos:
            console.print("[yellow]没有发现新视频[/yellow]")
            return
        
        console.print(f"[green]发现 {len(new_videos)} 个新视频![/green]")
        
        # 2. 保存到数据库
        session = get_session()
        for video in new_videos:
            # 检查是否已存在
            existing = session.query(Video).filter(Video.id == video.id).first()
            if not existing:
                db_video = Video(
                    id=video.id,
                    title=video.title,
                    description=video.description,
                    channel_name=video.channel_name,
                    channel_url=video.channel_url,
                    original_url=video.original_url,
                    duration=video.duration,
                    language=video.language,
                    category=video.category,
                    upload_date=video.upload_date,
                    status=VideoStatus.PENDING
                )
                session.add(db_video)
        
        session.commit()
        session.close()
        
        # 3. 自动处理 (如果启用)
        if self.config['workflow']['auto_process']:
            for video in new_videos:
                await self.process_video(video.id)
    
    async def process_video(self, video_id: str):
        """处理单个视频"""
        session = get_session()
        video = session.query(Video).filter(Video.id == video_id).first()
        
        if not video:
            logger.error(f"视频不存在: {video_id}")
            return
        
        console.print(f"\n[bold]开始处理: {video.title[:50]}...[/bold]")
        
        try:
            # Step 1: 下载视频
            video.status = VideoStatus.DOWNLOADING
            session.commit()
            
            from core.monitor import VideoInfo
            video_info = VideoInfo(
                id=video.id,
                title=video.title,
                description=video.description,
                duration=video.duration,
                upload_date=video.upload_date,
                channel_name=video.channel_name,
                channel_url=video.channel_url,
                thumbnail="",
                original_url=video.original_url
            )
            
            download_path = await self.downloader.download(
                video_info,
                quality=self.config['youtube']['download']['quality']
            )
            
            if not download_path:
                raise Exception("下载失败")
            
            video.download_path = str(download_path)
            video.status = VideoStatus.DOWNLOADED
            session.commit()
            console.print(f"[green]✓ 下载完成[/green]")
            
            # Step 2: 处理字幕（下载+翻译+合成）
            video.status = VideoStatus.PROCESSING
            session.commit()
            
            output_path = await process_video_with_youtube_subtitles(
                video_url=video.original_url,
                video_path=Path(download_path),
                output_dir=Path(self.config['system']['output_path']),
                llm_config=self.llm_config,
                intro_path=None
            )
            
            if not output_path:
                raise Exception("处理失败")
            
            video.output_path = str(output_path)
            video.status = VideoStatus.PROCESSED
            session.commit()
            console.print(f"[green]✓ 处理完成: {output_path}[/green]")
            
        except Exception as e:
            logger.error(f"处理失败 {video_id}: {e}")
            video.status = VideoStatus.FAILED
            video.error_message = str(e)
            session.commit()
            console.print(f"[red]✗ 处理失败: {e}[/red]")
        
        finally:
            session.close()
    
    async def run_scheduler(self):
        """运行定时监控"""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        
        scheduler = AsyncIOScheduler()
        interval = self.config['youtube']['check_interval']
        
        scheduler.add_job(
            self.run_monitor_cycle,
            'interval',
            seconds=interval,
            id='monitor_job',
            replace_existing=True
        )
        
        scheduler.start()
        console.print(f"[bold green]定时监控已启动 (每 {interval} 秒检查一次)[/bold green]")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            scheduler.shutdown()
            console.print("[yellow]监控已停止[/yellow]")


@click.group()
def cli():
    """Video Agent - 视频搬运/二创自动化工具"""
    pass


@cli.command()
def monitor():
    """启动监控 (检查一次)"""
    agent = VideoAgent()
    asyncio.run(agent.run_monitor_cycle())


@cli.command()
def schedule():
    """启动定时监控"""
    agent = VideoAgent()
    asyncio.run(agent.run_scheduler())


@cli.command()
@click.argument('video_id')
def process(video_id):
    """处理指定视频"""
    agent = VideoAgent()
    asyncio.run(agent.process_video(video_id))


@cli.command()
def list():
    """列出所有视频"""
    session = get_session()
    videos = session.query(Video).order_by(Video.created_at.desc()).limit(20).all()
    
    table = Table(title="视频列表")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("标题", style="green")
    table.add_column("频道", style="blue")
    table.add_column("状态", style="yellow")
    table.add_column("创建时间")
    
    for v in videos:
        status_color = {
            VideoStatus.PENDING: "white",
            VideoStatus.DOWNLOADING: "blue",
            VideoStatus.PROCESSING: "yellow",
            VideoStatus.PUBLISHED: "green",
            VideoStatus.FAILED: "red"
        }.get(v.status, "white")
        
        table.add_row(
            v.id[:10] + "...",
            v.title[:40] + "..." if len(v.title) > 40 else v.title,
            v.channel_name,
            f"[{status_color}]{v.status.value}[/{status_color}]",
            v.created_at.strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)
    session.close()


@cli.command()
def init():
    """初始化数据库"""
    init_database()
    console.print("[green]数据库初始化完成[/green]")


@cli.command()
@click.argument('video_url')
def download_translate(video_url):
    """直接下载并翻译视频字幕"""
    async def process():
        console.print(f"[bold]处理视频: {video_url}[/bold]")
        
        # 加载配置
        config = load_config_with_env("config/config.yaml")
        llm_config = None
        for provider in ['deepseek', 'zhipu', 'moonshot', 'dashscope', 'openai']:
            if config.get(provider, {}).get('enabled'):
                llm_config = {'provider': provider, **config[provider]}
                break
        
        if not llm_config:
            console.print("[red]错误: 未配置 LLM API[/red]")
            return
        
        # 下载视频
        from datetime import datetime
        from core.monitor import VideoInfo
        
        # 获取视频信息
        import subprocess
        result = subprocess.run(
            ['yt-dlp', '--dump-json', '--no-download', video_url],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode != 0:
            console.print(f"[red]获取视频信息失败: {result.stderr}[/red]")
            return
        
        import json
        info = json.loads(result.stdout)
        
        video_info = VideoInfo(
            id=info['id'],
            title=info['title'],
            description=info.get('description', '')[:200],
            duration=info.get('duration', 0),
            upload_date=datetime.now(),
            channel_name=info.get('channel', 'Unknown'),
            channel_url=info.get('channel_url', ''),
            thumbnail=info.get('thumbnail', ''),
            original_url=video_url
        )
        
        downloader = VideoDownloader(config['system']['download_path'])
        download_path = await downloader.download(video_info, quality='720p', download_subtitles=False)
        
        if not download_path:
            console.print("[red]下载失败[/red]")
            return
        
        console.print(f"[green]✓ 下载完成: {download_path}[/green]")
        
        # 处理字幕
        output_path = await process_video_with_youtube_subtitles(
            video_url=video_url,
            video_path=Path(download_path),
            output_dir=Path(config['system']['output_path']),
            llm_config=llm_config
        )
        
        if output_path:
            console.print(f"[green]✅ 完成! 输出文件: {output_path}[/green]")
        else:
            console.print("[red]处理失败[/red]")
    
    asyncio.run(process())


@cli.command()
def webui():
    """启动 Web UI"""
    console.print("[bold]启动 Web UI...[/bold]")
    import uvicorn
    from webui.app import app
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    cli()
