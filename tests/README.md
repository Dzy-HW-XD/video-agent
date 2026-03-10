# Video Agent 测试文档

## 🎯 测试策略

采用**分阶段测试**策略，确保每个环节独立验证：

```
Phase 1: 抓取能力 ──────▶ Phase 2: 处理能力
   │                         │
   ▼                         ▼
YouTube监控              语音识别
视频下载                 翻译
   │                    TTS配音
   ▼                         │
验证下载文件               视频合成
   │                         │
   └──────────▶ 最终验证 ◀───┘
                完整流程
```

---

## 📋 测试用例汇总

### Phase 1: 抓取能力测试

| 用例ID | 名称 | 目的 | 前置条件 | 预期输出 |
|--------|------|------|----------|----------|
| TC-001 | YouTube频道监控 | 验证能检测新视频 | 配置好频道 | 数据库新增记录 |
| TC-002 | 视频下载 | 验证能下载到本地 | TC-001通过 | downloads/有mp4文件 |

### Phase 2: 处理能力测试

| 用例ID | 名称 | 目的 | 前置条件 | 预期输出 |
|--------|------|------|----------|----------|
| TC-003 | Whisper语音识别 | 语音转文字 | 有本地视频 | 字幕列表(>0句) |
| TC-004 | 字幕翻译 | 英文转中文 | TC-003通过 | 中文字幕(>80%) |
| TC-005 | Edge TTS配音 | 生成中文语音 | TC-004通过 | 音频文件(.mp3) |
| TC-006 | 视频合成 | 画面+配音+字幕 | TC-005通过 | 最终视频(.mp4) |

---

## 🚀 快速开始

### 运行全部测试

```bash
cd /root/video-agent
./tests/run_tests.sh all
```

### 仅运行 Phase 1

```bash
./tests/run_tests.sh phase1
```

### 仅运行 Phase 2

```bash
# 确保 Phase 1 已通过，有下载的视频
./tests/run_tests.sh phase2
```

### 单独运行 Python 测试

```bash
# Phase 1
cd tests
python3 test_phase1.py

# Phase 2
python3 test_phase2.py
```

---

## ✅ 测试通过标准

### Phase 1 通过标准

| 检查项 | 通过条件 |
|--------|----------|
| 监控功能 | 能检测到频道视频 |
| 数据持久化 | 数据库有记录 |
| 下载功能 | downloads/ 有 .mp4 文件 |
| 文件完整性 | 视频可播放，大小>10MB |

### Phase 2 通过标准

| 检查项 | 通过条件 |
|--------|----------|
| 语音识别 | 识别出>10句字幕 |
| 翻译质量 | 翻译率>80% |
| 配音生成 | 生成有效音频文件 |
| 视频合成 | 输出文件包含字幕和配音 |

---

## 🔧 故障排查

### Phase 1 常见问题

#### ❌ "未发现新视频"

**原因**: 频道视频已被处理过，或频道无新视频

**解决**:
```bash
# 清空数据库重新测试
rm database/video_agent.db
python3 -c "from database.models import init_database; init_database()"
```

#### ❌ "下载失败"

**原因**: 网络问题或 yt-dlp 需要更新

**解决**:
```bash
# 更新 yt-dlp
yt-dlp -U

# 测试网络连通性
curl -I https://www.youtube.com
```

#### ❌ "数据库错误"

**解决**:
```bash
# 初始化数据库
python main.py init
```

### Phase 2 常见问题

#### ❌ "Whisper 模型下载慢"

**解决**:
```bash
# 使用镜像源或手动下载
export WHISPER_MODEL_DIR=/path/to/models

# 或修改 config.yaml 使用更小模型
whisper:
  model: "tiny"  # 改为 tiny 加速测试
```

#### ❌ "翻译失败"

**原因**: Google 翻译 API 限制

**解决**:
```bash
# 改用 DeepL (配置 api key)
# 或降低测试字幕数量
```

#### ❌ "FFmpeg 未找到"

**解决**:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# 验证
ffmpeg -version
```

---

## 📊 测试报告示例

### Phase 1 成功报告

```
==================================================
📊 Phase 1 测试报告
==================================================
✅ TC-001: PASS - 发现 3 个新视频
✅ TC-002: PASS - 下载成功，45.2MB
--------------------------------------------------
总计: 2 通过, 0 失败, 0 警告

🎉 Phase 1 测试通过! 可以进行 Phase 2 测试
```

### Phase 2 成功报告

```
==================================================
📊 Phase 2 测试报告
==================================================
✅ TC-003: PASS - 识别 156 句
✅ TC-004: PASS - 翻译 148 句
✅ TC-005: PASS - 生成 245KB 音频
✅ TC-006: PASS - 生成 12.5MB 视频
--------------------------------------------------
总计: 4 通过, 0 失败, 0 警告, 0 跳过

🎉 Phase 2 测试通过! 系统可以正常处理视频
```

---

## 🔄 回归测试

修改代码后，运行回归测试确保功能正常：

```bash
# 快速回归测试 (只测试核心功能)
./tests/run_tests.sh phase1
./tests/run_tests.sh phase2

# 完整回归测试 (清理数据后)
rm -rf database/ downloads/* outputs/*
./tests/run_tests.sh all
```

---

## 📝 扩展测试

如需添加新的测试用例：

1. 在 `tests/` 目录创建新测试文件
2. 继承测试基类或参考现有测试
3. 更新 `run_tests.sh` 添加选项

示例测试文件结构：
```python
# tests/test_new_feature.py
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_new_feature():
    print("🧪 测试新功能...")
    # 测试代码
    assert condition, "测试失败"
    print("✅ 测试通过")

if __name__ == "__main__":
    asyncio.run(test_new_feature())
```
