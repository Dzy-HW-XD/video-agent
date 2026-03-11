#!/usr/bin/env python3
"""
YouTube 字幕下载和翻译模块
直接从 YouTube 下载原文字幕，然后翻译成中文
"""
import asyncio
import os
import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import httpx
import subprocess
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class Subtitle:
    """字幕条目"""
    start: float
    end: float
    text: str
    translation: str = ""


class YouTubeSubtitleProcessor:
    """YouTube 字幕处理器"""
    
    def __init__(self, llm_config: dict):
        self.llm_config = llm_config
    
    async def download_subtitles(self, video_url: str, lang: str = "en") -> List[Subtitle]:
        """
        从 YouTube 下载字幕
        """
        logger.info(f"下载 YouTube 字幕: {video_url}, 语言: {lang}")
        
        # 使用 yt-dlp 下载字幕
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-subs',
            '--write-auto-subs',
            '--sub-langs', lang,
            '--convert-subs', 'srt',
            '--sub-format', 'srt',
            '-o', 'temp/%(id)s',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"字幕下载失败: {result.stderr}")
            return []
        
        # 提取视频 ID
        video_id = self._extract_video_id(video_url)
        srt_path = f"temp/{video_id}.{lang}.srt"
        
        # 如果没有找到指定语言，尝试自动字幕
        if not Path(srt_path).exists():
            srt_path = f"temp/{video_id}.{lang}.srt"
        
        # 查找下载的字幕文件
        temp_dir = Path('temp')
        srt_files = list(temp_dir.glob(f"{video_id}*.srt"))
        
        if not srt_files:
            logger.error("未找到下载的字幕文件")
            return []
        
        srt_path = srt_files[0]
        logger.info(f"字幕文件: {srt_path}")
        
        # 解析 SRT 文件
        subtitles = self._parse_srt(srt_path.read_text(encoding='utf-8'))
        logger.success(f"下载完成: {len(subtitles)} 句字幕")
        
        return subtitles
    
    def _extract_video_id(self, url: str) -> str:
        """提取 YouTube 视频 ID"""
        patterns = [
            r'v=([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return "unknown"
    
    def _parse_srt(self, srt_content: str) -> List[Subtitle]:
        """解析 SRT 格式字幕"""
        subtitles = []
        blocks = srt_content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # 时间行: 00:00:01,000 --> 00:00:05,000
                time_line = lines[1]
                text = '\n'.join(lines[2:])
                
                start_str, end_str = time_line.split(' --> ')
                start = self._srt_time_to_seconds(start_str)
                end = self._srt_time_to_seconds(end_str)
                
                subtitles.append(Subtitle(start=start, end=end, text=text))
        
        return subtitles
    
    def _srt_time_to_seconds(self, time_str: str) -> float:
        """SRT时间转秒"""
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """秒转SRT时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    async def translate(self, subtitles: List[Subtitle]) -> List[Subtitle]:
        """
        翻译字幕
        """
        logger.info(f"开始翻译 {len(subtitles)} 句字幕...")
        
        # 批量翻译，每20句一组
        batch_size = 20
        for i in range(0, len(subtitles), batch_size):
            batch = subtitles[i:i+batch_size]
            await self._translate_batch(batch)
            logger.info(f"翻译进度: {min(i+batch_size, len(subtitles))}/{len(subtitles)}")
        
        translated_count = sum(1 for s in subtitles if s.translation)
        logger.success(f"翻译完成: {translated_count}/{len(subtitles)} 句")
        
        return subtitles
    
    async def _translate_batch(self, subtitles: List[Subtitle]):
        """批量翻译一组字幕"""
        texts = [s.text for s in subtitles]
        
        # 构建提示词
        prompt = """请将以下英文翻译成自然流畅的中文，保持原意和语气：

"""
        for i, text in enumerate(texts, 1):
            prompt += f"{i}. {text}\n"
        
        prompt += """
请按以下格式返回翻译结果：
1. [中文翻译]
2. [中文翻译]
..."""
        
        try:
            translation = await self._call_llm(prompt)
            # 解析翻译结果
            lines = translation.strip().split('\n')
            for i, line in enumerate(lines):
                if i < len(subtitles):
                    # 去掉编号
                    translated = line.strip()
                    if '. ' in translated:
                        translated = translated.split('. ', 1)[-1]
                    elif '。' in translated[:10]:
                        translated = translated.split('。', 1)[-1]
                    subtitles[i].translation = translated.strip()
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            # 保持原文
            for s in subtitles:
                s.translation = s.text
    
    async def _call_llm(self, prompt: str) -> str:
        """调用大模型API"""
        provider = self.llm_config['provider']
        
        if provider == 'moonshot':
            return await self._call_moonshot(prompt)
        elif provider == 'deepseek':
            return await self._call_deepseek(prompt)
        else:
            raise ValueError(f"未知模型提供商: {provider}")
    
    async def _call_moonshot(self, prompt: str) -> str:
        """调用 Moonshot API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_config['api_key']}"},
                json={
                    "model": self.llm_config['model'],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                },
                timeout=60
            )
            result = response.json()
            if 'choices' not in result:
                raise Exception(f"API 错误: {result}")
            return result['choices'][0]['message']['content']
    
    async def _call_deepseek(self, prompt: str) -> str:
        """调用 DeepSeek API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_config['api_key']}"},
                json={
                    "model": self.llm_config['model'],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                },
                timeout=60
            )
            result = response.json()
            return result['choices'][0]['message']['content']
    
    def write_srt(self, subtitles: List[Subtitle], output_path: Path, use_translation: bool = True):
        """写入 SRT 字幕文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                text = sub.translation if use_translation and sub.translation else sub.text
                f.write(f"{i}\n")
                f.write(f"{self._seconds_to_srt_time(sub.start)} --> {self._seconds_to_srt_time(sub.end)}\n")
                f.write(f"{text}\n\n")
        
        logger.info(f"字幕文件已保存: {output_path}")


async def process_video_with_youtube_subtitles(
    video_url: str,
    video_path: Path,
    output_dir: Path,
    llm_config: dict,
    intro_path: Optional[Path] = None
) -> Optional[Path]:
    """
    使用 YouTube 字幕处理视频的完整流程
    """
    logger.info("=== 使用 YouTube 字幕处理视频 ===")
    
    processor = YouTubeSubtitleProcessor(llm_config)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: 下载字幕
    logger.info("\n📥 步骤 1/3: 下载 YouTube 字幕...")
    subtitles = await processor.download_subtitles(video_url, lang="en")
    
    if not subtitles:
        logger.error("未获取到字幕，尝试下载自动字幕...")
        subtitles = await processor.download_subtitles(video_url, lang="en-US")
    
    if not subtitles:
        logger.error("无法获取字幕")
        return None
    
    logger.info(f"获取到 {len(subtitles)} 句字幕")
    for i, sub in enumerate(subtitles[:3]):
        text = sub.text[:60] if len(sub.text) > 60 else sub.text
        logger.info(f"  {i+1}. [{sub.start:.1f}s] {text}")
    
    # Step 2: 翻译
    logger.info("\n🌐 步骤 2/3: 翻译字幕...")
    subtitles = await processor.translate(subtitles)
    
    logger.info("翻译示例:")
    for i, sub in enumerate(subtitles[:3]):
        orig = sub.text[:50] if len(sub.text) > 50 else sub.text
        trans = sub.translation[:50] if sub.translation and len(sub.translation) > 50 else sub.translation
        logger.info(f"  原文: {orig}")
        logger.info(f"  译文: {trans}\n")
    
    # Step 3: 生成字幕版视频
    logger.info("\n🎬 步骤 3/3: 生成字幕版视频...")
    
    video_name = video_path.stem
    srt_path = output_dir / f"{video_name}_zh.srt"
    processor.write_srt(subtitles, srt_path)
    
    # 使用 FFmpeg 合成视频
    output_path = output_dir / f"{video_name}_subtitled.mp4"
    
    cmd = [
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-vf', f"subtitles={srt_path}:force_style='FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=50'",
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'copy',
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
        logger.error(f"视频合成失败: {stderr.decode()[:500]}")
        return None
    
    logger.success(f"✅ 字幕版视频生成完成: {output_path}")
    logger.info(f"   文件大小: {output_path.stat().st_size / (1024*1024):.1f} MB")
    
    # 清理临时字幕文件
    srt_path.unlink(missing_ok=True)
    
    return output_path


if __name__ == "__main__":
    # 测试
    import yaml
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    llm_config = {
        'provider': 'moonshot',
        'api_key': os.getenv('MOONSHOT_API_KEY'),
        'base_url': 'https://api.moonshot.cn/v1',
        'model': 'moonshot-v1-8k'
    }
    
    async def test():
        result = await process_video_with_youtube_subtitles(
            video_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            video_path=Path('./downloads/test_video_dQw4w9WgXcQ.mp4'),
            output_dir=Path('./outputs'),
            llm_config=llm_config
        )
        print(f"\n输出文件: {result}")
    
    asyncio.run(test())
