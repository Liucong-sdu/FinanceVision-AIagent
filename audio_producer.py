# coding=utf-8

'''
模块二：audio_producer.py (音频生产模块)
核心任务: 接收完整的文稿，调用TTS API，生成一个音频文件和对应的句子时间戳数据。
'''

# requires Python 3.6 or later
# pip install requests
import os
import base64
import json
import uuid
import requests
from typing import Dict, List, Tuple

# --- API 配置 ---
# 建议将这些敏感信息存储在环境变量或配置文件中，而不是硬编码在代码里。
# 为了演示，我们遵循示例将其放在此处。
APPID = "7243436737"
ACCESS_TOKEN = "r72NGzrgibnXbuOTIdl2RaVIDiUMcQwo"
CLUSTER = "volcano_icl"
HOST = "openspeech.bytedance.com"
API_URL = f"https://{HOST}/api/v1/tts"
# 选择一个音色，S_DNgMQKiB1 是一个不错的通用女声
VOICE_TYPE = "S_DNgMQKiB1"


def generate_audio_and_timestamps(full_script: str, output_dir: str = "temp_assets") -> Tuple[str | None, List[Dict]]:
    """
    根据文稿生成音频文件和时间戳。

    Args:
        full_script (str): 拼接好的完整旁白文稿。
        output_dir (str): 用于存放生成音频文件的目录。

    Returns:
        Tuple[str | None, List[Dict]]: 一个元组。
                                第一个元素是生成的音频文件路径 (str)。
                                第二个元素是时间戳列表 (List[Dict])。
                                如果失败，则返回 (None, [])。
    """
    print("开始生成音频和时间戳...")
    
    # 1. 确保输出目录存在
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(f"创建目录失败: {output_dir}, 错误: {e}")
        return None, []

    # 2. 准备请求头和请求体
    header = {"Authorization": f"Bearer;{ACCESS_TOKEN}"}

    request_json = {
        "app": {
            "appid": APPID,
            "token": "access_token",
            "cluster": CLUSTER
        },
        "user": {
            "uid": "388808087185088"
        },
        "audio": {
            "voice_type": VOICE_TYPE,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": full_script,
            "text_type": "plain",
            "operation": "query",
            "with_frontend": 1,
            "frontend_type": "unitTson"
        }
    }

    try:
        # 3. 发送POST请求
        resp = requests.post(API_URL, data=json.dumps(request_json), headers=header)
        
        # 4. 检查HTTP响应状态
        if resp.status_code != 200:
            print(f"请求失败，HTTP状态码: {resp.status_code}, 响应: {resp.text}")
            return None, []

        resp_json = resp.json()

        # 5. 检查业务层面的错误码
        # <--- 修改点 (MODIFICATION) ---
        # 根据火山引擎文档，query操作的成功码是3000，而不是常见的0。
        if resp_json.get("code") != 3000:
            print(f"API返回业务错误: code={resp_json.get('code')}, message='{resp_json.get('message')}'")
            return None, []

        # 6. 解析音频数据并保存
        if "data" in resp_json:
            audio_base64 = resp_json["data"]
            audio_bytes = base64.b64decode(audio_base64)
            
            audio_filename = f"{uuid.uuid4()}.mp3"
            audio_filepath = os.path.join(output_dir, audio_filename)
            
            with open(audio_filepath, "wb") as f:
                f.write(audio_bytes)
            print(f"音频文件已成功保存到: {audio_filepath}")
        else:
            print("错误：API响应中未找到 'data' 字段 (音频数据)。")
            return None, []

        # 7. 解析时间戳数据
        timestamps = []
        if "addition" in resp_json and "frontend" in resp_json["addition"] and "unitTson" in resp_json["addition"]["frontend"]:
            raw_timestamps = resp_json["addition"]["frontend"]["unitTson"]
            for item in raw_timestamps:
                timestamps.append({
                    "text": item.get("text"),
                    "start": item.get("start_time"),
                    "end": item.get("end_time")
                })
            print(f"成功解析了 {len(timestamps)} 条时间戳。")
        else:
            print("警告：API响应中未找到 'addition.frontend.unitTson' 字段 (时间戳数据)。")
            return None, []

        return audio_filepath, timestamps

    except requests.exceptions.RequestException as e:
        print(f"网络请求异常: {e}")
        return None, []
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"解析API响应时出错: {e}")
        return None, []
    except Exception as e:
        print(f"发生未知错误: {e}")
        return None, []


# --- 测试代码 ---
if __name__ == '__main__':
    sample_script = "10亿用户App转向AI原生应用，大船如何掉头？高德最近打了个样，用AI重构底层技术栈，建立主-从Agent架构，将千问大模型与空间智能结合，展现出了新范式的强大威力，给用户带去了极大便利。一条最快的通勤路线，一份详细的全家旅游攻略……过去需要一系列操作，全网到处搜索需求，现在动动嘴，一句话就搞定了。出行和生活，有AI Agent加持以后，原来可以这么简单。"
    
    audio_file, timestamp_data = generate_audio_and_timestamps(sample_script, output_dir="generated_output")

    if audio_file and timestamp_data:
        print("\n--- 函数调用成功 ---")
        print(f"生成的音频文件路径: {audio_file}")
        print("生成的时间戳数据:")
        for i, ts in enumerate(timestamp_data[:5]):
            print(f"  {i+1}: Text='{ts['text']}', Start={ts['start']}ms, End={ts['end']}ms")
        if len(timestamp_data) > 5:
            print(f"  ... (共 {len(timestamp_data)} 条)")
    else:
        print("\n--- 函数调用失败 ---")

