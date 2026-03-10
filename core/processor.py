#!/usr/bin/env python3
"""
视频处理模块 - 全线上API方案
语音识别(ASR) + 翻译 + 语音合成(TTS) + 视频合成
"""
import asyncio
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import httpx
import yaml
from loguru import logger

# 阿里云语音 HTTP API (不依赖 SDK)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from aliyun_nls_http import AliyunTTS, AliyunASR


@dataclass
class Subtitle:
    """字幕条目"""
    start: float
    end: float
    text: str
    translation: str = ""


class VideoProcessor:
    """视频处理器 - 全线上API"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = f.read()
        
        # 替换环境变量占位符
        raw_config = self._replace_env_vars(raw_config)
        
        self.config = yaml.safe_load(raw_config)
        
        self.asr_config = self.config['asr']
        self.tts_config = self.config['tts']
        self.llm_config = self._get_active_llm_config()
        
        logger.info("视频处理器初始化完成 (全线上API方案)")
    
    def _replace_env_vars(self, content: str) -> str:
        """替换 ${VAR_NAME} 为环境变量值"""
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, content)
    
    def _get_active_llm_config(self) -> dict:
        """获取启用的大模型配置"""
        llm_providers = ['deepseek', 'zhipu', 'moonshot', 'dashscope', 'openai']
        for provider in llm_providers:
            if self.config.get(provider, {}).get('enabled'):
                return {'provider': provider, **self.config[provider]}
        raise ValueError("未启用任何大模型API")
    
    # ============================================
    # 1. 语音识别 (ASR) - 线上API
    # ============================================
    
    async def transcribe(self, video_path: Path) -> List[Subtitle]:
        """
        语音识别 - 调用线上API
        支持: OpenAI Whisper / 阿里云 / 讯飞
        """
        logger.info(f"开始语音识别: {video_path.name}")
        
        # 提取音频
        audio_path = await self._extract_audio(video_path)
        
        # 根据配置选择ASR服务
        if self.asr_config['openai'].get('enabled'):
            subtitles = await self._transcribe_openai(audio_path)
        elif self.asr_config['aliyun'].get('enabled'):
            subtitles = await self._transcribe_aliyun(audio_path)
        elif self.asr_config['xfyun'].get('enabled'):
            subtitles = await self._transcribe_xfyun(audio_path)
        else:
            raise ValueError("未启用任何ASR服务")
        
        # 清理临时文件
        audio_path.unlink(missing_ok=True)
        
        logger.success(f"语音识别完成: {len(subtitles)} 句")
        return subtitles
    
    async def _extract_audio(self, video_path: Path) -> Path:
        """从视频提取音频 (本地FFmpeg)"""
        audio_path = Path(tempfile.gettempdir()) / f"{video_path.stem}.mp3"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vn',  # 无视频
            '-acodec', 'libmp3lame',
            '-ar', '16000',  # 16kHz (ASR标准)
            '-ac', '1',      # 单声道
            '-b:a', '32k',   # 低码率即可
            str(audio_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        
        if not audio_path.exists():
            raise Exception("音频提取失败")
        
        return audio_path
    
    async def _transcribe_openai(self, audio_path: Path) -> List[Subtitle]:
        """OpenAI Whisper API"""
        logger.info("使用 OpenAI Whisper API 识别...")
        
        config = self.asr_config['openai']
        
        async with httpx.AsyncClient(timeout=300) as client:
            with open(audio_path, 'rb') as f:
                files = {'file': ('audio.mp3', f, 'audio/mpeg')}
                data = {
                    'model': config['model'],
                    'language': config.get('language', 'en'),
                    'response_format': config.get('response_format', 'srt'),
                    'timestamp_granularities': ['word']  # 获取精确时间戳
                }
                
                response = await client.post(
                    'https://api.openai.com/v1/audio/transcriptions',
                    headers={'Authorization': f'Bearer {config["api_key"]}'},
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    raise Exception(f"Whisper API 错误: {response.text}")
                
                # 解析SRT格式
                srt_content = response.text
                return self._parse_srt(srt_content)
    
    async def _transcribe_aliyun(self, audio_path: Path) -> List[Subtitle]:
        """阿里云语音识别 - HTTP API"""
        logger.info("使用阿里云 ASR 识别...")
        
        config = self.asr_config['aliyun']
        
        # 读取音频文件
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        # 使用 HTTP API (AccessKey 方式)
        asr = AliyunASR(
            config['access_key_id'],
            config['access_key_secret'],
            config['app_key']
        )
        
        text = await asr.recognize(audio_data)
        
        # 简单封装成字幕格式（单句）
        subtitles = [Subtitle(start=0.0, end=30.0, text=text)]
        
        return subtitles
    
    async def _transcribe_xfyun(self, audio_path: Path) -> List[Subtitle]:
        """讯飞语音识别"""
        logger.info("使用讯飞 ASR 识别...")
        
        config = self.asr_config['xfyun']
        
        # 讯飞长语音识别API
        from xfyun import LfasrClient
        
        client = LfasrClient(
            app_id=config['app_id'],
            secret_key=config['api_key']
        )
        
        # 上传音频
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.upload(audio_path)
        )
        
        # 解析SRT结果
        return self._parse_srt(result)
    
    def _parse_srt(self, srt_content: str) -> List[Subtitle]:
        """解析SRT格式字幕"""
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
    
    # ============================================
    # 2. 翻译 - 调用大模型API
    # ============================================
    
    async def translate(self, subtitles: List[Subtitle]) -> List[Subtitle]:
        """
        翻译字幕 - 使用大模型API
        """
        logger.info(f"开始翻译 {len(subtitles)} 句字幕...")
        
        # 批量翻译，每10句一组
        batch_size = 10
        for i in range(0, len(subtitles), batch_size):
            batch = subtitles[i:i+batch_size]
            await self._translate_batch(batch)
        
        translated_count = sum(1 for s in subtitles if s.translation)
        logger.success(f"翻译完成: {translated_count}/{len(subtitles)} 句")
        
        return subtitles
    
    async def _translate_batch(self, subtitles: List[Subtitle]):
        """批量翻译一组字幕"""
        texts = [s.text for s in subtitles]
        prompt = "将以下英文翻译成自然流畅的中文:\n" + "\n".join([f"{i+1}. {t}" for i, t in enumerate(texts)])
        
        try:
            translation = await self._call_llm(prompt)
            # 解析翻译结果
            lines = translation.strip().split('\n')
            for i, line in enumerate(lines):
                if i < len(subtitles):
                    # 去掉编号
                    translated = line.split('. ', 1)[-1] if '. ' in line else line
                    subtitles[i].translation = translated
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            # 保持原文
            for s in subtitles:
                s.translation = s.text
    
    async def _call_llm(self, prompt: str) -> str:
        """调用大模型API"""
        provider = self.llm_config['provider']
        
        if provider == 'deepseek':
            return await self._call_deepseek(prompt)
        elif provider == 'zhipu':
            return await self._call_zhipu(prompt)
        elif provider == 'moonshot':
            return await self._call_moonshot(prompt)
        elif provider == 'dashscope':
            return await self._call_dashscope(prompt)
        elif provider == 'openai':
            return await self._call_openai(prompt)
        else:
            raise ValueError(f"未知模型提供商: {provider}")
    
    async def _call_deepseek(self, prompt: str) -> str:
        """调用DeepSeek API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_config['api_key']}"},
                json={
                    "model": self.llm_config['model'],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
            )
            result = response.json()
            return result['choices'][0]['message']['content']
    
    async def _call_zhipu(self, prompt: str) -> str:
        """调用智谱API"""
        from zhipuai import ZhipuAI
        client = ZhipuAI(api_key=self.llm_config['api_key'])
        response = client.chat.completions.create(
            model=self.llm_config['model'],
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    async def _call_moonshot(self, prompt: str) -> str:
        """调用Moonshot API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm_config['api_key']}"},
                json={
                    "model": self.llm_config['model'],
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            result = response.json()
            if 'choices' not in result:
                logger.error(f"Kimi API 返回错误: {result}")
                raise Exception(f"Kimi API 错误: {result.get('error', result)}")
            return result['choices'][0]['message']['content']
    
    async def _call_dashscope(self, prompt: str) -> str:
        """调用阿里云通义千问"""
        import dashscope
        dashscope.api_key = self.llm_config['api_key']
        response = dashscope.Generation.call(
            model=self.llm_config['model'],
            messages=[{"role": "user", "content": prompt}]
        )
        return response.output.text
    
    async def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API"""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=self.llm_config['api_key'],
            base_url=self.llm_config.get('base_url')
        )
        response = await client.chat.completions.create(
            model=self.llm_config['model'],
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    # ============================================
    # 3. 语音合成 (TTS) - 线上API
    # ============================================
    
    async def generate_tts(self, subtitles: List[Subtitle], output_path: Path) -> Path:
        """
        生成配音 - 调用线上TTS API
        支持: Azure / 阿里云 / 讯飞
        """
        logger.info(f"开始生成配音: {len(subtitles)} 句")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 合并文本（简化处理）
        full_text = " ".join([s.translation for s in subtitles if s.translation])
        
        if self.tts_config['azure'].get('enabled'):
            await self._tts_azure(full_text, output_path)
        elif self.tts_config['aliyun'].get('enabled'):
            await self._tts_aliyun(full_text, output_path)
        elif self.tts_config['xfyun'].get('enabled'):
            await self._tts_xfyun(full_text, output_path)
        else:
            raise ValueError("未启用任何TTS服务")
        
        logger.success(f"配音生成完成: {output_path}")
        return output_path
    
    async def _tts_azure(self, text: str, output_path: Path):
        """Azure TTS"""
        logger.info("使用 Azure TTS...")
        
        config = self.tts_config['azure']
        
        import azure.cognitiveservices.speech as speechsdk
        
        speech_config = speechsdk.SpeechConfig(
            subscription=config['subscription_key'],
            region=config['region']
        )
        speech_config.speech_synthesis_voice_name = config['voice_name']
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3
        )
        
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: synthesizer.speak_text_async(text).get()
        )
        
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise Exception(f"Azure TTS 失败: {result.reason}")
    
    async def _tts_aliyun(self, text: str, output_path: Path):
        """阿里云TTS - HTTP API"""
        logger.info("使用阿里云 TTS...")
        
        config = self.tts_config['aliyun']
        
        # 使用 HTTP API (AccessKey 方式)
        tts = AliyunTTS(
            config['access_key_id'],
            config['access_key_secret'],
            config['app_key']
        )
        
        audio_data = await tts.synthesize(
            text=text,
            voice=config.get('voice', 'xiaoyun'),
            speech_rate=config.get('speech_rate', 0),
            pitch_rate=config.get('pitch_rate', 0)
        )
        
        with open(output_path, 'wb') as f:
            f.write(audio_data)
    
    async def _tts_xfyun(self, text: str, output_path: Path):
        """讯飞TTS"""
        logger.info("使用讯飞 TTS...")
        
        config = self.tts_config['xfyun']
        
        from xfyun import TTSClient
        
        client = TTSClient(
            app_id=config['app_id'],
            api_key=config['api_key'],
            api_secret=config['api_secret']
        )
        
        audio_data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.synthesize(text, voice=config['voice'])
        )
        
        with open(output_path, 'wb') as f:
            f.write(audio_data)
    
    # ============================================
    # 4. 视频合成 - 本地FFmpeg
    # ============================================
    
    async def compose_video(
        self,
        video_path: Path,
        audio_path: Path,
        subtitles: List[Subtitle],
        output_path: Path
    ) -> Path:
        """合成最终视频"""
        logger.info("开始合成视频...")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成字幕文件
        srt_path = output_path.with_suffix('.srt')
        self._write_srt(subtitles, srt_path)
        
        # FFmpeg 合成
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-i', str(audio_path),
            '-vf', f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000'",
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"视频合成失败: {stderr.decode()[:500]}")
        
        # 清理字幕文件
        srt_path.unlink(missing_ok=True)
        
        logger.success(f"视频合成完成: {output_path}")
        return output_path
    
    def _write_srt(self, subtitles: List[Subtitle], output_path: Path):
        """写入SRT字幕文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(f"{self._seconds_to_srt_time(sub.start)} --> {self._seconds_to_srt_time(sub.end)}\n")
                f.write(f"{sub.translation if sub.translation else sub.text}\n\n")
    
    # ============================================
    # 5. 字幕版视频处理（保留原声 + 字幕 + 片头）
    # ============================================
    
    async def process_with_subtitles(
        self,
        video_path: Path,
        output_dir: Path,
        intro_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        处理视频：保留原声 + 翻译字幕 + 可选片头
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            intro_path: 片头视频路径（可选）
        
        Returns:
            输出视频路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        video_name = video_path.stem
        
        # Step 1: 语音识别
        logger.info("步骤 1/4: 语音识别...")
        subtitles = await self.transcribe(video_path)
        
        # Step 2: 翻译
        logger.info("步骤 2/4: 翻译字幕...")
        subtitles = await self.translate(subtitles)
        
        # Step 3: 添加字幕（保留原声）
        logger.info("步骤 3/4: 添加字幕...")
        subtitled_path = output_dir / f"{video_name}_subtitled.mp4"
        await self.add_subtitles_only(video_path, subtitles, subtitled_path)
        
        # Step 4: 添加片头（如果提供）
        if intro_path and intro_path.exists():
            logger.info("步骤 4/4: 添加片头...")
            output_path = output_dir / f"{video_name}_final.mp4"
            await self.concat_with_intro(intro_path, subtitled_path, output_path)
            # 清理中间文件
            subtitled_path.unlink(missing_ok=True)
        else:
            logger.info("步骤 4/4: 跳过片头（未提供）")
            output_path = subtitled_path
        
        logger.success(f"处理完成: {output_path}")
        return output_path
    
    async def add_subtitles_only(
        self,
        video_path: Path,
        subtitles: List[Subtitle],
        output_path: Path
    ) -> Path:
        """
        给视频添加字幕（保留原声）
        """
        logger.info(f"添加字幕: {video_path.name}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成字幕文件
        srt_path = output_path.with_suffix('.srt')
        self._write_srt(subtitles, srt_path)
        
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
        
        # 清理字幕文件
        srt_path.unlink(missing_ok=True)
        
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
    
    # ============================================
    # 6. 完整处理流程（配音版，保留）
    # ============================================
    
    async def process_video(
        self,
        video_path: Path,
        output_dir: Path
    ) -> Optional[Path]:
        """完整的视频处理流程（配音版）"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        video_name = video_path.stem
        
        # Step 1: 语音识别
        subtitles = await self.transcribe(video_path)
        
        # Step 2: 翻译
        subtitles = await self.translate(subtitles)
        
        # Step 3: 生成配音
        audio_path = output_dir / f"{video_name}_dubbed.mp3"
        await self.generate_tts(subtitles, audio_path)
        
        # Step 4: 合成视频
        output_path = output_dir / f"{video_name}_final.mp4"
        result = await self.compose_video(video_path, audio_path, subtitles, output_path)
        
        return result


# 测试代码
if __name__ == "__main__":
    async def test():
        processor = VideoProcessor()
        print("视频处理器已初始化 (全线上API)")
        print(f"支持功能: ASR, 翻译, TTS, 字幕, 片头拼接")
    
    asyncio.run(test())
