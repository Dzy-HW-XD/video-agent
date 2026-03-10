#!/usr/bin/env python3
"""
阿里云语音服务 HTTP API 封装（AccessKey 方式）
自动通过 AccessKey 生成 Token
"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Optional

import httpx


class AliyunTTS:
    """阿里云语音合成 HTTP API"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self.endpoint = "https://nls-gateway-cn-shanghai.aliyuncs.com"
        self._token = None
        self._token_expire_time = 0
    
    async def _get_token(self) -> str:
        """获取有效的 Token（带缓存）"""
        if self._token and time.time() < self._token_expire_time:
            return self._token
        
        url = 'https://nls-meta.cn-shanghai.aliyuncs.com'
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        signature_nonce = str(int(time.time() * 1000))
        
        params = {
            'AccessKeyId': self.access_key_id,
            'Action': 'CreateToken',
            'Version': '2019-02-28',
            'Timestamp': timestamp,
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'SignatureNonce': signature_nonce,
            'Format': 'JSON'
        }
        
        sorted_params = sorted(params.items())
        canonical_query = '&'.join([f'{k}={self._percent_encode(v)}' for k, v in sorted_params])
        string_to_sign = f'GET&%2F&{self._percent_encode(canonical_query)}'
        
        key = f'{self.access_key_secret}&'
        signature = hmac.new(
            key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        signature = base64.b64encode(signature).decode('utf-8')
        
        params['Signature'] = signature
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            result = response.json()
            
            if 'Token' in result and 'Id' in result['Token']:
                self._token = result['Token']['Id']
                expire_time = result['Token'].get('ExpireTime', int(time.time()) + 86400)
                self._token_expire_time = expire_time - 3600
                return self._token
            else:
                raise Exception(f"获取 Token 失败: {result}")
    
    def _percent_encode(self, s: str) -> str:
        import urllib.parse
        return urllib.parse.quote(s, safe='').replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    
    async def synthesize(self, text: str, voice: str = "zhimiao_emo", 
                        speech_rate: int = 0, pitch_rate: int = 0) -> bytes:
        """
        语音合成
        """
        url = f"{self.endpoint}/stream/v1/tts"
        token = await self._get_token()
        
        headers = {
            "Content-Type": "application/json",
            "X-NLS-Token": token
        }
        
        payload = {
            "appkey": self.app_key,
            "text": text,
            "token": token,
            "format": "mp3",
            "sample_rate": 16000,
            "voice": voice,
            "volume": 50,
            "speech_rate": speech_rate,
            "pitch_rate": pitch_rate
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=60.0)
            
            if response.status_code != 200:
                raise Exception(f"TTS 请求失败: {response.status_code} - {response.text}")
            
            return response.content


class AliyunASR:
    """阿里云语音识别 HTTP API"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, app_key: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.app_key = app_key
        self.endpoint = "https://nls-gateway-cn-shanghai.aliyuncs.com"
        self._token = None
        self._token_expire_time = 0
    
    async def _get_token(self) -> str:
        """获取有效的 Token（带缓存）"""
        if self._token and time.time() < self._token_expire_time:
            return self._token
        
        url = 'https://nls-meta.cn-shanghai.aliyuncs.com'
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        signature_nonce = str(int(time.time() * 1000))
        
        params = {
            'AccessKeyId': self.access_key_id,
            'Action': 'CreateToken',
            'Version': '2019-02-28',
            'Timestamp': timestamp,
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'SignatureNonce': signature_nonce,
            'Format': 'JSON'
        }
        
        sorted_params = sorted(params.items())
        canonical_query = '&'.join([f'{k}={self._percent_encode(v)}' for k, v in sorted_params])
        string_to_sign = f'GET&%2F&{self._percent_encode(canonical_query)}'
        
        key = f'{self.access_key_secret}&'
        signature = hmac.new(
            key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        signature = base64.b64encode(signature).decode('utf-8')
        
        params['Signature'] = signature
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            result = response.json()
            
            if 'Token' in result and 'Id' in result['Token']:
                self._token = result['Token']['Id']
                expire_time = result['Token'].get('ExpireTime', int(time.time()) + 86400)
                self._token_expire_time = expire_time - 3600
                return self._token
            else:
                raise Exception(f"获取 Token 失败: {result}")
    
    def _percent_encode(self, s: str) -> str:
        import urllib.parse
        return urllib.parse.quote(s, safe='').replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
    
    async def recognize(self, audio_data: bytes, format: str = "mp3", 
                       sample_rate: int = 16000) -> str:
        """
        语音识别（一句话识别）
        """
        url = f"{self.endpoint}/stream/v1/asr"
        token = await self._get_token()
        
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        url_with_params = f"{url}?appkey={self.app_key}"
        
        headers = {
            "Content-Type": "application/json",
            "X-NLS-Token": token
        }
        
        payload = {
            "format": format,
            "sample_rate": sample_rate,
            "enable_punctuation_prediction": True,
            "enable_inverse_text_normalization": True,
            "token": token,
            "audio": audio_base64
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url_with_params, json=payload, headers=headers, timeout=60.0)
            
            if response.status_code != 200:
                raise Exception(f"ASR 请求失败: {response.status_code} - {response.text}")
            
            result = response.json()
            
            if result.get("status") == 20000000:
                return result.get("result", "")
            else:
                raise Exception(f"ASR 识别失败: {result.get('message', 'Unknown error')}")
