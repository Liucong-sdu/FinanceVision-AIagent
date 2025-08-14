# -*- coding: utf-8 -*-
"""
模块三：image_processor.py (图像处理模块)
核心任务：接收图片生成指令，生成一张场景图片。
版本：v3.0 (极简版 - 移除文本绘制功能)
"""

import os
import io
import logging
import requests
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

# --- 初始化与配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

try:
    client = OpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=os.environ.get("ARK_API_KEY"),
    )
    if not client.api_key:
        logging.warning("环境变量 ARK_API_KEY 未设置或为空。API调用可能会失败。")
except Exception as e:
    logging.error(f"初始化 OpenAI 客户端失败: {e}")
    client = None

# --- 核心功能函数 ---
def create_scene_image(image_prompt: str, output_filepath: str) -> bool:
    """
    【简化版】仅根据提示词生成一张场景图片，不添加任何文字。

    Args:
        image_prompt (str): 用于调用图片生成API的提示词。
        output_filepath (str): 最终图片的保存路径。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    if not client:
        logging.error("OpenAI 客户端未初始化，无法生成图片。")
        return False

    try:
        # --- 1. 调用API生成图片 ---
        logging.info(f"开始生成图片，提示词: '{image_prompt[:50]}...'")
        response = client.images.generate(
            model="doubao-seedream-3-0-t2i-250415",
            prompt=image_prompt,
            size="1024x1024",
            response_format="url"
        )
        image_url = response.data[0].url
        logging.info("图片生成成功。")

        # --- 2. 下载图片数据 ---
        logging.info("正在下载生成的图片...")
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()
        image_data = image_response.content
        logging.info("图片下载完成。")

        # --- 3. 直接保存图片 ---
        # 确保输出目录存在
        output_dir = os.path.dirname(output_filepath)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # 使用 with open 确保文件正确关闭
        with open(output_filepath, 'wb') as f:
            f.write(image_data)
            
        logging.info(f"场景图片已成功保存到: {output_filepath}")
        return True

    except Exception as e:
        logging.error(f"处理图片时发生未知错误: {e}", exc_info=True)
        return False

# --- 模块独立测试入口 ---
if __name__ == '__main__':
    print("--- 开始执行 image_processor.py 模块测试 (简化版) ---")

    if not os.environ.get("ARK_API_KEY"):
        print("\n[警告] 环境变量 ARK_API_KEY 未设置。")
    else:
        test_prompt = "一只可爱的橙色虎斑猫，坐在书房的窗台上，窗外是宁静的午后阳光，超高清细节，摄影风格"
        test_output = "temp_assets/test_scene_no_text.png"

        print(f"\n测试参数:\n  - 提示词: {test_prompt}\n  - 输出路径: {test_output}")
        
        success = create_scene_image(
            image_prompt=test_prompt,
            output_filepath=test_output
        )

        if success:
            print(f"\n[成功] 测试完成！图片已保存至 '{os.path.abspath(test_output)}'")
        else:
            print("\n[失败] 测试未成功。请检查错误日志。")
            
    print("\n--- image_processor.py 模块测试结束 ---")
