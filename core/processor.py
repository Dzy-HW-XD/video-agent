#!/usr/bin/env python3
"""
视频处理模块 - 简化版
仅保留字幕处理和视频合成功能
"""
import asyncio
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from loguru import logger


@dataclass
class Subtitle:
    """字幕条目"""
    start: float
    end: float
    text: str
    translation: str = ""


class VideoProcessor:
    """视频处理器 - 仅保留合成功能"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        logger.info("视频处理器初始化完成 (字幕合成版)")
    
    async def add_subtitles_to_video(
        self,
        video_path: Path,
        srt_path: Path,
        output_path: Path
    ) -> Path:
        """
        给视频添加字幕
        """
        logger.info(f"添加字幕: {video_path.name}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # FFmpeg: 添加字幕，保留原声
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', f"subtitles={srt_path}:force_style='FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'copy',  # 复制音频，不重新编码
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"添加字幕失败: {stderr.decode()[:500]}")
        
        logger.success(f"字幕添加完成: {output_path}")
        return output_path
    
    async def concat_with_intro(
        self,
        intro_path: Path,
        main_path: Path,
        output_path: Path
    ) -> Path:
        """
        拼接片头和主视频
        """
        logger.info(f"拼接片头: {intro_path.name} + {main_path.name}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建 concat 列表文件
        concat_list = output_path.parent / 'concat_list.txt'
        with open(concat_list, 'w', encoding='utf-8') as f:
            f.write(f"file '{intro_path.absolute()}'\n")
            f.write(f"file '{main_path.absolute()}'\n")
        
        # FFmpeg: 拼接视频
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy',  # 直接复制，不重新编码（快速）
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # 清理列表文件
        concat_list.unlink(missing_ok=True)
        
        if process.returncode != 0:
            # 如果直接复制失败，尝试重新编码
            logger.warning("直接拼接失败，尝试重新编码...")
            return await self._concat_with_reencode(intro_path, main_path, output_path)
        
        logger.success(f"拼接完成: {output_path}")
        return output_path
    
    async def _concat_with_reencode(
        self,
        intro_path: Path,
        main_path: Path,
        output_path: Path
    ) -> Path:
        """使用重新编码方式拼接（兼容性更好）"""
        cmd = [
            'ffmpeg', '-y',
            '-i', str(intro_path),
            '-i', str(main_path),
            '-filter_complex', '[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]',
            '-map', '[outv]',
            '-map', '[outa]',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"视频拼接失败: {stderr.decode()[:500]}")
        
        logger.success(f"重新编码拼接完成: {output_path}")
        return output_path
