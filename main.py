#!/usr/bin/env python3
"""
Video Agent - 视频搬运/二创自动化工具
主入口文件
"""
import asyncio
import sys
from pathlib import Path

import click
import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.monitor import YouTubeMonitor
from core.downloader import VideoDownloader
from core.processor import VideoProcessor
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


class VideoAgent:
    """视频 Agent 主类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 初始化组件
        self.monitor = YouTubeMonitor(config_path)
        self.downloader = VideoDownloader(self.config['system']['download_path'])
        self.processor = VideoProcessor(config_path)
        
        # 初始化数据库
        init_database(config_path)
        
        logger.info("Video Agent 初始化完成")
    
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
            # Step 1: 下载
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
            
            # Step 2: 处理 (语音转文字 + 翻译 + 配音 + 合成)
            video.status = VideoStatus.PROCESSING
            session.commit()
            
            output_path = await self.processor.process_video(
                download_path,
                self.config['system']['output_path']
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
def webui():
    """启动 Web UI"""
    console.print("[bold]启动 Web UI...[/bold]")
    # 这里启动 FastAPI
    import uvicorn
    from webui.app import app
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    cli()
