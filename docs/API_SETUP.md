# 线上API方案 - 服务商注册指南

## 🎯 推荐配置组合

### 方案A: 性价比最高 (推荐)
| 功能 | 服务商 | 价格 | 注册地址 |
|------|--------|------|----------|
| 翻译 | DeepSeek | ¥1-2/M tokens | https://platform.deepseek.com |
| 语音识别 | OpenAI Whisper | $0.006/分钟 | https://platform.openai.com |
| 语音合成 | Azure TTS | $16/100万字 | https://azure.microsoft.com |

**预估成本**: 一个10分钟视频约 ¥2-3

---

### 方案B: 全中文生态
| 功能 | 服务商 | 价格 | 注册地址 |
|------|--------|------|----------|
| 翻译 | 智谱GLM-4-Flash | 免费 | https://open.bigmodel.cn |
| 语音识别 | 讯飞 | ¥1.5/小时 | https://www.xfyun.cn |
| 语音合成 | 讯飞 | ¥1.5/万字 | https://www.xfyun.cn |

**预估成本**: 一个10分钟视频约 ¥1-2

---

### 方案C: 阿里云全家桶
| 功能 | 服务商 | 价格 | 注册地址 |
|------|--------|------|----------|
| 翻译 | 通义千问 | ¥2-6/M | https://dashscope.aliyun.com |
| 语音识别 | 阿里云ASR | ¥1.8/小时 | https://www.aliyun.com/product/nls |
| 语音合成 | 阿里云TTS | ¥2/万字 | https://www.aliyun.com/product/nls |

**预估成本**: 一个10分钟视频约 ¥2-4

---

## 📋 快速接入步骤

### 1. 环境变量配置

创建 `.env` 文件：

```bash
# 大模型 (选一个)
export DEEPSEEK_API_KEY="sk-your-deepseek-key"
export ZHIPU_API_KEY="your-zhipu-key"
export MOONSHOT_API_KEY="sk-your-moonshot-key"

# 语音识别 (选一个)
export OPENAI_API_KEY="sk-your-openai-key"
export ALIYUN_ACCESS_KEY_ID="your-aliyun-id"
export ALIYUN_ACCESS_KEY_SECRET="your-aliyun-secret"
export ALIYUN_APP_KEY="your-app-key"

# 语音合成 (选一个)
export AZURE_TTS_KEY="your-azure-key"

# 其他
export WEBUI_PASSWORD="your-password"
```

### 2. 安装依赖

```bash
pip install azure-cognitiveservices-speech dashscope zhipuai httpx
```

### 3. 修改配置

编辑 `config/config.yaml`：

```yaml
# 启用你想用的服务
deepseek:
  enabled: true
  api_key: "${DEEPSEEK_API_KEY}"

asr:
  openai:
    enabled: true
    api_key: "${OPENAI_API_KEY}"

tts:
  azure:
    enabled: true
    subscription_key: "${AZURE_TTS_KEY}"
```

### 4. 运行测试

```bash
python tests/test_phase2.py
```

---

## 💰 成本计算器

### 10分钟英文视频处理成本

| 步骤 | 用量 | 单价 | 费用 |
|------|------|------|------|
| 语音识别 | 10分钟 | $0.006/分钟 | ¥0.4 |
| 翻译 | 3000 tokens | ¥1/1M tokens | ¥0.003 |
| 语音合成 | 3000字 | $16/100万字 | ¥0.3 |
| **总计** | | | **¥0.7** |

### 月成本预估 (每天处理5个视频)

| 方案 | 单日成本 | 月成本 |
|------|----------|--------|
| 方案A (DeepSeek+OpenAI+Azure) | ¥3.5 | ¥105 |
| 方案B (智谱免费+讯飞) | ¥2 | ¥60 |
| 方案C (阿里云) | ¥4 | ¥120 |

---

## 🔑 各平台注册步骤

### DeepSeek (最推荐)
1. 访问 https://platform.deepseek.com
2. 手机号注册
3. 充值 (支付宝/微信)
4. 创建 API Key
5. 复制到 `.env` 文件

### 智谱AI (免费版)
1. 访问 https://open.bigmodel.cn
2. 手机号注册
3. 个人认证
4. 获取 API Key
5. 使用 `glm-4-flash` 模型 (永久免费)

### 讯飞
1. 访问 https://www.xfyun.cn
2. 注册开发者账号
3. 创建应用
4. 开通 "语音听写" 和 "在线语音合成"
5. 获取 AppID/APIKey/APISecret

### Azure (TTS最自然)
1. 访问 https://azure.microsoft.com
2. 注册账号 (需信用卡，但TTS有免费额度)
3. 创建 Cognitive Services 资源
4. 获取 Key 和 Region

---

## ⚡ 快速启动命令

```bash
cd /root/video-agent

# 1. 设置环境变量
export DEEPSEEK_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
export AZURE_TTS_KEY="your-key"

# 2. 运行测试
python tests/test_phase2.py

# 3. 启动完整服务
python main.py schedule
```

---

## ❓ 常见问题

### Q: 为什么语音识别还要用OpenAI？国内没有替代吗？
A: 有！讯飞和阿里云都可以。但Whisper对英文识别最准确，如果你的视频主要是英文，建议用OpenAI。中文视频可以用讯飞。

### Q: 可以只用一家公司的全套服务吗？
A: 可以！阿里云和讯飞都提供翻译+语音识别+语音合成的全套服务。但各家的优势不同，混合使用效果更好。

### Q: 免费额度够用吗？
A: 智谱GLM-4-Flash完全免费。讯飞新用户送5小时语音识别。Azure TTS每月有50万字符免费额度。初期足够用。
