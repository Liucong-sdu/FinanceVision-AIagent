

import os
import json
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()  # 自动读取当前目录下的 .env 文件
# --- 配置区域 ---
# 强烈建议使用环境变量来存储API密钥，而不是硬编码在代码中。
# 在终端中设置: export SILICONFLOW_API_KEY='your_actual_api_key'
API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
PROMPT_TEMPLATE_PATH = "prompt_template.txt"

def generate_content_plan(daily_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    接收每日财经数据，生成视频内容规划。

    Args:
        daily_data (Dict): 从爬虫JSON文件加载的完整数据字典。

    Returns:
        Dict[str, List[Dict]]: 一个字典，包含一个名为 "scenes" 的列表。
                               每个元素是一个场景字典。
                               如果生成失败，则返回一个空的字典 {}。
    """
    if not API_KEY:
        print("错误：未找到API密钥。请设置环境变量 'SILICONFLOW_API_KEY'。")
        return {}

    try:
        # 1. 读取预设的Prompt模板文件
        with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template = f.read()

        # 2. 将daily_data字典中的数据格式化并填充到模板中
        # 使用json.dumps确保数据格式正确，ensure_ascii=False以正确处理中文
        formatted_data = json.dumps(daily_data, indent=2, ensure_ascii=False)
        full_prompt = template.replace("{daily_data_placeholder}", formatted_data)

        # 3. 调用大语言模型API
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 构造请求体，要求LLM返回JSON对象
        payload = {
            "model": "deepseek-ai/DeepSeek-R1", # 使用更新的模型可能效果更好
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "max_tokens": 160000, # 增加max_tokens以容纳更复杂的JSON输出
            "temperature": 0.7,
            "top_p": 0.7,
            "response_format": {"type": "json_object"} # 关键：强制模型输出JSON格式
        }

        print("正在向LLM发送请求...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=120) # 设置超时
        response.raise_for_status()  # 如果HTTP状态码是4xx或5xx，则抛出异常

        # 4. 解析LLM返回的JSON字符串
        response_data = response.json()
        llm_output_str = response_data['choices'][0]['message']['content']
        
        print("成功接收LLM响应，正在解析...")
        # print("LLM原始输出:", llm_output_str) # 用于调试

        parsed_json = json.loads(llm_output_str)

        # 5. 验证结构是否符合要求
        if isinstance(parsed_json, dict) and "scenes" in parsed_json and isinstance(parsed_json["scenes"], list):
            print("内容规划生成成功！")
            return parsed_json
        else:
            print("错误：LLM返回的JSON结构不符合预期。")
            return {}

    except FileNotFoundError:
        print(f"错误：Prompt模板文件未找到，路径: '{PROMPT_TEMPLATE_PATH}'")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"错误：API请求失败 - {e}")
        return {}
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"错误：解析LLM响应失败或响应格式不正确 - {e}")
        print("请检查LLM的原始输出，可能不是有效的JSON或结构不完整。")
        return {}
    except Exception as e:
        print(f"发生未知错误: {e}")
        return {}

