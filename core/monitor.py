#!/usr/bin/env python3
"""
YouTube 监控模块 - 检测新视频
"""
import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

import httpx
import yaml
from loguru import logger


@dataclass
class VideoInfo:
    """视频信息"""
    id: str
    title: str
    description: str
    duration: int  # 秒
    upload_date: datetime
    channel_name: str
    channel_url: str
    thumbnail: str
    original_url: str
    language: str = "en"
    category: str = ""


@dataclass  
class ChannelConfig:
    """频道配置"""
    name: str
    url: str
    language: str
    category: str
    filter_rules: Dict


class YouTubeMonitor:
    """YouTube 新视频监控器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.channels = self._parse_channels()
        self.state_file = Path("database/monitor_state.json")
        self.state = self._load_state()
        
    def _load_config(self, path: str) -> dict:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _parse_channels(self) -> List[ChannelConfig]:
        """解析频道配置"""
        channels = []
        for ch in self.config['youtube']['channels']:
            channels.append(ChannelConfig(
                name=ch['name'],
                url=ch['url'],
                language=ch.get('language', 'en'),
                category=ch.get('category', ''),
                filter_rules=ch.get('filter', {})
            ))
        return channels
    
    def _load_state(self) -> dict:
        """加载监控状态 (记录已处理的视频)"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_state(self):
        """保存监控状态"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    async def fetch_channel_videos(self, channel: ChannelConfig) -> List[VideoInfo]:
        """
        获取频道最新视频列表
        使用 yt-dlp 获取，无需 API Key
        """
        logger.info(f"正在检查频道: {channel.name}")
        
        try:
            # yt-dlp 命令获取最新10个视频
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--playlist-end', '10',
                '--dump-single-json',
                '--match-filter', 'duration > 60',  # 过滤短视频
                channel.url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"yt-dlp 错误: {result.stderr}")
                return []
            
            data = json.loads(result.stdout)
            videos = []
            
            for entry in data.get('entries', []):
                # 解析上传时间
                upload_date_str = entry.get('upload_date', '')  # 格式: 20240309
                if upload_date_str:
                    upload_date = datetime.strptime(upload_date_str, '%Y%m%d')
                else:
                    upload_date = datetime.now()
                
                video = VideoInfo(
                    id=entry['id'],
                    title=entry['title'],
                    description=entry.get('description', '')[:200],
                    duration=entry.get('duration', 0),
                    upload_date=upload_date,
                    channel_name=channel.name,
                    channel_url=channel.url,
                    thumbnail=entry.get('thumbnails', [{}])[0].get('url', ''),
                    original_url=f"https://www.youtube.com/watch?v={entry['id']}",
                    language=channel.language,
                    category=channel.category
                )
                videos.append(video)
            
            return videos
            
        except Exception as e:
            logger.error(f"获取频道视频失败 {channel.name}: {e}")
            return []
    
    def _passes_filter(self, video: VideoInfo, rules: Dict) -> bool:
        """检查视频是否通过过滤规则"""
        # 时长检查
        min_duration = rules.get('min_duration', 0)
        max_duration = rules.get('max_duration', float('inf'))
        
        if video.duration < min_duration:
            logger.debug(f"视频 {video.title[:30]}... 时长太短: {video.duration}s")
            return False
        
        if video.duration > max_duration:
            logger.debug(f"视频 {video.title[:30]}... 时长太长: {video.duration}s")
            return False
        
        # 关键词检查
        keywords = rules.get('keywords', [])
        if keywords:
            title_lower = video.title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                logger.debug(f"视频 {video.title[:30]}... 未包含关键词")
                return False
        
        # 排除关键词检查
        exclude_keywords = rules.get('exclude_keywords', [])
        if exclude_keywords:
            title_lower = video.title.lower()
            if any(kw.lower() in title_lower for kw in exclude_keywords):
                logger.debug(f"视频 {video.title[:30]}... 包含排除关键词")
                return False
        
        return True
    
    def _is_new_video(self, video: VideoInfo) -> bool:
        """检查是否是新视频 (未处理过)"""
        channel_state = self.state.get(video.channel_name, [])
        return video.id not in channel_state
    
    def _mark_as_processed(self, video: VideoInfo):
        """标记视频为已处理"""
        if video.channel_name not in self.state:
            self.state[video.channel_name] = []
        
        self.state[video.channel_name].append(video.id)
        
        # 只保留最近100个视频ID
        self.state[video.channel_name] = self.state[video.channel_name][-100:]
        self._save_state()
    
    async def check_all_channels(self) -> List[VideoInfo]:
        """
        检查所有频道，返回符合过滤条件的新视频
        """
        new_videos = []
        
        for channel in self.channels:
            videos = await self.fetch_channel_videos(channel)
            
            for video in videos:
                # 检查是否为新视频
                if not self._is_new_video(video):
                    continue
                
                # 检查是否通过过滤
                if not self._passes_filter(video, channel.filter_rules):
                    self._mark_as_processed(video)  # 不符合条件的也标记，避免重复检查
                    continue
                
                new_videos.append(video)
                logger.info(f"发现新视频: {video.title} ({video.channel_name})")
        
        return new_videos


# 测试代码
if __name__ == "__main__":
    async def test():
        monitor = YouTubeMonitor("../config/config.yaml")
        videos = await monitor.check_all_channels()
        print(f"\n发现 {len(videos)} 个新视频:")
        for v in videos:
            print(f"- {v.title} ({v.duration}s)")
    
    asyncio.run(test())
