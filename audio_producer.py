# coding=utf-8
"""
模块二：audio_producer.py (音频生产模块) - B方案：本地时间戳生成
核心任务: 
1. 接收文稿，调用TTS API，生成一个纯音频文件。
2. 使用本地模型（Whisper）为音频和文稿生成精确的时间戳。
"""
import os
import base64
import json
import uuid
import requests
import logging
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

load_dotenv() 
# --- 初始化与配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 火山TTS API 配置 ---
APPID = os.getenv("VOLCANO_APPID", "YOUR_APPID_HERE")
ACCESS_TOKEN = os.getenv("VOLCANO_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
CLUSTER = "volcano_icl"
HOST = "openspeech.bytedance.com"
API_URL = f"https://{HOST}/api/v1/tts"
VOICE_TYPE = "S_DNgMQKiB1"

# --- 本地时间戳生成器 (Whisper) ---
# 使用一个全局变量来缓存模型，避免每次调用都重新加载
whisper_model = None

def _initialize_whisper():
    """惰性加载Whisper模型，只在第一次需要时加载。"""
    global whisper_model
    if whisper_model is None:
        logging.info("正在初始化Whisper模型（首次运行需要下载模型文件）...")
        try:
            # stable-ts 重新导出了 whisper，所以可以直接从它导入
            from stable_whisper import load_model
            # 'base' 模型在速度和精度之间取得了很好的平衡，且占用资源较少。
            # 如果需要更高精度，可以换成 'medium'。
            whisper_model = load_model('base') 
            logging.info("Whisper模型加载成功！")
        except ImportError:
            logging.error("无法导入 stable_whisper。请运行 'pip install stable-ts' 进行安装。")
            raise
        except Exception as e:
            logging.error(f"加载Whisper模型时出错: {e}")
            raise

def generate_audio_only(full_script: str, output_dir: str) -> Optional[str]:
    """
    【步骤一】仅调用TTS API生成音频文件。
    
    Args:
        full_script (str): 拼接好的完整旁白文稿。
        output_dir (str): 用于存放生成音频文件的目录。

    Returns:
        Optional[str]: 成功则返回生成的音频文件路径，否则返回None。
    """
    logging.info("开始调用TTS API生成音频...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    header = {"Authorization": f"Bearer;{ACCESS_TOKEN}"}
    request_json = {
        "app": {"appid": APPID, "token": "access_token", "cluster": CLUSTER},
        "user": {"uid": "388808087185088"},
        "audio": {
            "voice_type": VOICE_TYPE, "encoding": "mp3", "speed_ratio": 1.0,
            "volume_ratio": 1.0, "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()), "text": full_script, "text_type": "plain",
            "operation": "query"
            # 注意：我们不再需要请求时间戳，所以移除了 with_frontend 和 frontend_type
        }
    }

    try:
        resp = requests.post(API_URL, data=json.dumps(request_json), headers=header, timeout=60)
        resp.raise_for_status() # 检查HTTP错误
        resp_json = resp.json()

        if resp_json.get("code") != 3000:
            logging.error(f"TTS API返回业务错误: code={resp_json.get('code')}, message='{resp_json.get('message')}'")
            return None

        if "data" in resp_json:
            audio_bytes = base64.b64decode(resp_json["data"])
            audio_filename = f"{uuid.uuid4()}.mp3"
            audio_filepath = os.path.join(output_dir, audio_filename)
            
            with open(audio_filepath, "wb") as f:
                f.write(audio_bytes)
            logging.info(f"音频文件已成功保存到: {audio_filepath}")
            return audio_filepath
        else:
            logging.error("错误：TTS API响应中未找到 'data' 字段 (音频数据)。")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"TTS网络请求异常: {e}")
        return None
    except Exception as e:
        logging.error(f"生成音频时发生未知错误: {e}")
        return None

def generate_timestamps_from_audio(audio_path: str, original_script: str) -> List[Dict]:
    """
    【步骤二】使用本地Whisper模型为音频和文本生成词级别时间戳。

    Args:
        audio_path (str): 音频文件的路径。
        original_script (str): 用于生成音频的原始文稿。

    Returns:
        List[Dict]: 词级别时间戳列表，每个元素包含 'text', 'start', 'end'。
                    失败则返回空列表。
    """
    logging.info(f"开始使用Whisper为音频生成时间戳: {audio_path}")
    try:
        _initialize_whisper() # 确保模型已加载
        
        # 使用 stable-ts 的 align 方法进行强制对齐
        # language='zh' 明确指定语言为中文
        result = whisper_model.align(audio_path, original_script, language='zh')
        
        timestamps = []
        # result.segments 是一个生成器，包含所有词语的信息
        for segment in result.segments:
            for word in segment.words:
                timestamps.append({
                    "text": word.word.strip(),
                    # stable-ts 的时间单位是秒，我们需要转换为毫秒以匹配之前的格式
                    "start": int(word.start * 1000),
                    "end": int(word.end * 1000)
                })
        
        if not timestamps:
            logging.warning("Whisper未能从音频中提取任何时间戳。")
            return []
            
        logging.info(f"成功生成 {len(timestamps)} 条词级别时间戳。")
        return timestamps

    except Exception as e:
        logging.error(f"使用Whisper生成时间戳时发生错误: {e}", exc_info=True)
        return []

# --- 模块独立测试入口 ---
if __name__ == '__main__':
    print("\n--- audio_producer.py 模块测试 (方案B: 本地时间戳) ---")
    
    # 检查API凭证是否已配置
    if "YOUR_APPID_HERE" in APPID or "YOUR_ACCESS_TOKEN_HERE" in ACCESS_TOKEN:
        print("\n[警告] 请在脚本顶部或环境变量中配置您的火山引擎 APPID 和 ACCESS_TOKEN。")
        print("测试将跳过。")
    else:
        test_script = "今天A股市场整体表现有些低迷，三大指数齐齐下跌，不过科创50却像个不服输的少年，逆市上扬！"
        test_output_dir = "temp_audio_test"

        # 1. 测试音频生成
        print("\n--- 1. 测试音频生成 ---")
        audio_file = generate_audio_only(test_script, test_output_dir)

        if audio_file:
            print(f"\n[成功] 音频文件已生成: {audio_file}")

            # 2. 测试时间戳生成
            print("\n--- 2. 测试时间戳生成 ---")
            timestamp_data = generate_timestamps_from_audio(audio_file, test_script)

            if timestamp_data:
                print("\n[成功] 时间戳已生成:")
                for i, ts in enumerate(timestamp_data[:10]): # 显示前10个词
                    print(f"  - 词: '{ts['text']}', 开始: {ts['start']}ms, 结束: {ts['end']}ms")
                if len(timestamp_data) > 10:
                    print(f"  ... (共 {len(timestamp_data)} 个词)")
            else:
                print("\n[失败] 时间戳生成失败，请检查上面的错误日志。")
        else:
            print("\n[失败] 音频生成失败，请检查上面的错误日志。")



