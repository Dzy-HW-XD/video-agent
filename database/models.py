#!/usr/bin/env python3
"""
数据库模型定义
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import yaml

Base = declarative_base()


class VideoStatus(str, Enum):
    """视频处理状态"""
    PENDING = "pending"           # 待处理
    DOWNLOADING = "downloading"   # 下载中
    DOWNLOADED = "downloaded"     # 已下载
    PROCESSING = "processing"     # 处理中
    PROCESSED = "processed"       # 已处理
    PUBLISHING = "publishing"     # 发布中
    PUBLISHED = "published"       # 已发布
    FAILED = "failed"             # 失败


class Video(Base):
    """视频记录表"""
    __tablename__ = 'videos'
    
    id = Column(String(50), primary_key=True)  # YouTube video ID
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # 来源信息
    channel_name = Column(String(200))
    channel_url = Column(String(500))
    original_url = Column(String(500))
    
    # 元数据
    duration = Column(Integer)  # 秒
    language = Column(String(10))
    category = Column(String(100))
    
    # 本地文件路径
    download_path = Column(String(500))
    output_path = Column(String(500))
    
    # 状态
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.PENDING)
    error_message = Column(Text)
    
    # 发布时间
    upload_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 发布信息
    published_urls = Column(Text)  # JSON: {"douyin": "url", "bilibili": "url"}


def init_database(config_path: str = "config/config.yaml"):
    """初始化数据库"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    
    if db_config['type'] == 'sqlite':
        db_path = db_config['sqlite']['path']
        engine = create_engine(f'sqlite:///{db_path}')
    else:
        pg = db_config['postgresql']
        engine = create_engine(
            f'postgresql://{pg["username"]}:{pg["password"]}@{pg["host"]}:{pg["port"]}/{pg["database"]}'
        )
    
    Base.metadata.create_all(engine)
    return engine


SessionLocal = None

def get_session():
    """获取数据库会话"""
    global SessionLocal
    if SessionLocal is None:
        engine = init_database()
        SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
