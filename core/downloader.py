#!/usr/bin/env python3
"""
视频下载模块
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger

from core.monitor import VideoInfo


class VideoDownloader:
    """视频下载器"""
    
    def __init__(self, download_path: str = "./downloads"):
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
    
    async def download(
        self, 
        video: VideoInfo,
        quality: str = "1080p",
        download_subtitles: bool = True
    ) -> Optional[Path]:
        """
        下载 YouTube 视频
        
        Args:
            video: 视频信息
            quality: 画质 (1080p/720p/best)
            download_subtitles: 是否下载字幕
            
        Returns:
            下载后的视频文件路径
        """
        logger.info(f"开始下载: {video.title[:50]}...")
        
        # 构建输出文件名
        safe_title = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # 限制长度
        output_filename = f"{video.channel_name}_{safe_title}_{video.id}.mp4"
        output_path = self.download_path / output_filename
        
        # 如果已存在，直接返回
        if output_path.exists():
            logger.info(f"视频已存在: {output_path}")
            return output_path
        
        try:
            # 构建 yt-dlp 命令
            cmd = [
                'yt-dlp',
                video.original_url,
                '-o', str(output_path),
                '--merge-output-format', 'mp4',
            ]
            
            # 画质选择
            if quality == "1080p":
                cmd.extend(['-f', 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'])
            elif quality == "720p":
                cmd.extend(['-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]'])
            else:
                cmd.extend(['-f', 'bestvideo+bestaudio/best'])
            
            # 下载字幕
            if download_subtitles:
                cmd.extend([
                    '--write-subs',
                    '--write-auto-subs',
                    '--sub-langs', 'en,zh-Hans,zh-Hant',
                    '--convert-subs', 'srt',
                ])
            
            # 其他选项
            cmd.extend([
                '--no-warnings',
                '--no-check-certificate',
                '--retries', '3',
                '--fragment-retries', '3',
            ])
            
            # 执行下载
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"下载失败: {stderr.decode()}")
                return None
            
            if output_path.exists():
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                logger.success(f"下载完成: {output_path} ({file_size:.1f} MB)")
                return output_path
            else:
                logger.error("下载后文件未找到")
                return None
                
        except Exception as e:
            logger.error(f"下载异常: {e}")
            return None
    
    async def get_video_info(self, video_url: str) -> dict:
        """获取视频信息 (不下癐)"""
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-download',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        return {}


# 测试代码
if __name__ == "__main__":
    from datetime import datetime
    
    async def test():
        downloader = VideoDownloader()
        
        # 测试视频
        test_video = VideoInfo(
            id="dQw4w9WgXcQ",
            title="Test Video",
            description="Test",
            duration=212,
            upload_date=datetime.now(),
            channel_name="TestChannel",
            channel_url="",
            thumbnail="",
            original_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        
        path = await downloader.download(test_video, quality="720p")
        print(f"下载路径: {path}")
    
    # asyncio.run(test())
    print("下载模块已就绪")
