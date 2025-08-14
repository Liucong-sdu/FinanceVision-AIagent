# 财经视频自动化生## 🎥 效果演示

### 📺 项目演示视频
展示从数据采集到视频生成的完整流程：


https://github.com/user-attachments/assets/bdc5b0a2-8de0-46f5-98e0-00d4b5c3fdf7

## 系统要求
## 项目概述
这是一个自动化财经视频生成项目，能够：
1. 爬取东方财富网的财经数据
2. 使用AI生成视频内容脚本
3. 合成语音旁白
4. 生成配套图像
5. 自动剪辑成完整视频



## 系统要求
- Python 3.8+
- FFmpeg (必须安装并添加到系统PATH)
- 网络连接 (用于API调用)

## 安装步骤

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd caijing
```

### 2. 安装Python依赖
```bash
# 方式1：使用详细版requirements文件
pip install -r requirements.txt

# 方式2：使用简洁版requirements文件  
pip install -r requirements-simple.txt

# 方式3：手动安装核心依赖
pip install requests python-dotenv openai stable-ts Pillow ffmpeg-python pydub numpy
```

### 3. 安装FFmpeg
#### Windows:
1. 从 https://ffmpeg.org/download.html 下载FFmpeg
2. 解压到任意目录（如 C:\ffmpeg）
3. 将 C:\ffmpeg\bin 添加到系统环境变量PATH中
4. 在命令行运行 `ffmpeg -version` 验证安装

#### macOS:
```bash
brew install ffmpeg
```

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

### 4. 配置API密钥
1. 复制环境变量模板：
   ```bash
   cp .env.template .env
   ```

2. 编辑 `.env` 文件，填入您的API密钥：
   ```
   SILICONFLOW_API_KEY=your_actual_key
   VOLCANO_APPID=your_actual_appid
   VOLCANO_ACCESS_TOKEN=your_actual_token
   ARK_API_KEY=your_actual_ark_key
   ```

## 使用方法

### 1. 数据采集
```bash
# 午间数据采集
python eastmoney_scraper.py midday

# 盘后完整数据采集
python eastmoney_scraper.py eod
```

### 2. 生成视频
```bash
# 使用采集的数据生成视频
python main.py data/2025-08-15/2025-08-15_afternoon_004146.json --output_dir weekly_videos/
```

## API服务提供商

### SiliconFlow API
- 用途：AI内容生成
- 获取：https://cloud.siliconflow.cn/
- 模型：DeepSeek-R1

### 火山引擎 TTS API  
- 用途：语音合成
- 获取：https://console.volcengine.com/speech
- 声音类型：S_DNgMQKiB1

### 字节跳动 ARK API
- 用途：图像生成
- 获取：https://console.volcengine.com/ark
- 模型：doubao-seedream-3-0-t2i

## 故障排除

### 常见问题
1. **"FFmpeg not found"**
   - 确保FFmpeg已安装并添加到PATH环境变量

2. **"API key not found"**
   - 检查 `.env` 文件是否存在且配置正确

3. **"stable-ts安装失败"**
   - 可能需要先安装torch：`pip install torch`

4. **网络超时**
   - 检查网络连接和防火墙设置

### 性能优化
- 首次运行会下载Whisper模型（约500MB）
- 建议在SSD硬盘上运行以提高处理速度
- 可根据需要调整视频分辨率和帧率

## 项目结构
```
caijing/
├── main.py                 # 主调度脚本
├── content_generator.py    # 内容生成模块
├── audio_producer.py       # 音频生成模块  
├── image_processor.py      # 图像处理模块
├── video_assembler.py      # 视频合成模块
├── eastmoney_scraper.py    # 数据爬取模块
├── requirements.txt        # 详细依赖清单
├── requirements-simple.txt # 简洁依赖清单
├── .env.template          # 环境变量模板
├── prompt_template.txt    # AI提示词模板
└── data/                  # 数据存储目录
```

## 许可证
[您的许可证信息]

## 贡献
欢迎提交Issue和Pull Request！
