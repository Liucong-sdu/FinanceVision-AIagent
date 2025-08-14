# -*- coding: utf-8 -*-
"""
模块三：image_processor.py (图像处理模块)
核心任务：接收图片生成指令和叠加文本，生成一张带有数据图文的最终场景图片。
"""

import os
import io
import logging
import requests
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# --- 初始化与配置 ---

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 加载 .env 文件中的环境变量 (例如 ARK_API_KEY)
load_dotenv()

# 初始化Ark客户端
# 建议将客户端初始化放在模块级别，以避免在每次函数调用时重复创建。
try:
    client = OpenAI(
        # 此为默认路径，您可根据业务所在地域进行配置
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        # 从环境变量中获取您的 API Key
        api_key=os.environ.get("ARK_API_KEY"),
    )
    # 检查 API Key 是否成功加载
    if not client.api_key:
        logging.warning("环境变量 ARK_API_KEY 未设置或为空。API调用可能会失败。")

except Exception as e:
    logging.error(f"初始化 OpenAI 客户端失败: {e}")
    client = None

# --- 核心功能函数 ---

def create_scene_image(image_prompt: str, overlay_text: str, output_filepath: str, font_path: str = "fonts/default.ttf") -> bool:
    """
    生成一张场景图片并添加数据文字。

    此函数会执行以下步骤：
    1. 调用火山方舟（或其他兼容OpenAI接口的）图像生成API，根据提示词创建图片。
    2. 下载生成的图片。
    3. 使用Pillow库在图片上绘制指定的文本。
    4. 将最终合成的图片保存到指定路径。

    Args:
        image_prompt (str): 用于调用图片生成API的提示词。
        overlay_text (str): 需要绘制在图片上的文字。
        output_filepath (str): 最终处理好的图片的保存路径。
        font_path (str): 使用的字体文件路径。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    if not client:
        logging.error("OpenAI 客户端未初始化，无法生成图片。")
        return False

    try:
        # --- 1. 调用图片生成API，获取图片URL ---
        logging.info(f"开始生成图片，提示词: '{image_prompt[:50]}...'")
        response = client.images.generate(
            # 指定您创建的方舟推理接入点 ID
            model="doubao-seedream-3-0-t2i-250415",
            prompt=image_prompt,
            size="1024x1024",
            response_format="url"
        )

        if not response.data or not response.data[0].url:
            logging.error("API 未返回有效的图片数据。")
            return False

        image_url = response.data[0].url
        logging.info(f"图片生成成功，URL: {image_url}")

        # --- 2. 使用requests下载图片数据 ---
        logging.info("正在下载生成的图片...")
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()  # 如果请求失败（如404），则抛出HTTPError
        image_data = image_response.content
        logging.info("图片下载完成。")

        # --- 3. 使用Pillow库加载图片 ---
        image = Image.open(io.BytesIO(image_data)).convert("RGBA")

        # --- 4. 定义文字样式和位置，并将文字绘制到图片上 ---
        draw = ImageDraw.Draw(image)

        # a. 字体设置 (动态计算字体大小)
        # 字体大小设为图片高度的 1/20 左右，可以根据需要调整
        font_size = int(image.height / 20)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            logging.error(f"字体文件未找到或无法加载: {font_path}。将使用默认字体。")
            font = ImageFont.load_default()

        # b. 文字颜色和描边
        text_color = (255, 255, 255, 230)  # 白色，略带透明
        stroke_color = (0, 0, 0, 180)      # 黑色，半透明描边
        stroke_width = 2                   # 描边宽度

        # c. 【代码修改】计算文字位置 (居中)
        # 直接将目标位置设置为图片的中心点
        position = (image.width // 2, image.height // 2)

        # d. 【代码修改】绘制带描边的文字
        logging.info(f"在图片上绘制文本: '{overlay_text}'")
        # 使用 anchor='mm' 来确保文本的中心点与 position 对齐
        # 使用 align='center' 来处理多行文本的内部居中对齐
        draw.text(
            position,
            overlay_text,
            font=font,
            fill=text_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color,
            anchor="mm",
            align="center"
        )

        # --- 5. 保存最终图片 ---
        # 确保输出目录存在
        output_dir = os.path.dirname(output_filepath)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 保存为PNG格式以支持透明度
        image.save(output_filepath, "PNG")
        logging.info(f"最终场景图片已成功保存到: {output_filepath}")

        return True

    except requests.exceptions.RequestException as e:
        logging.error(f"下载图片时发生网络错误: {e}", exc_info=True)
        return False
    except IOError as e:
        logging.error(f"文件读写或Pillow处理时发生错误: {e}", exc_info=True)
        return False
    except Exception as e:
        # 捕获所有其他潜在异常，例如API调用失败、绘图失败等
        logging.error(f"处理图片时发生未知错误: {e}", exc_info=True)
        return False


# --- 模块独立测试入口 ---
if __name__ == '__main__':
    print("--- 开始执行 image_processor.py 模块测试 ---")

    # --- 准备测试环境 ---
    # 1. 创建临时资源目录
    if not os.path.exists("temp_assets"):
        os.makedirs("temp_assets")
    if not os.path.exists("fonts"):
        os.makedirs("fonts")

    # 2. 检查字体文件
    # 注意：请确保您在 'fonts' 目录下放置了一个中文字体文件。
    test_font_path = "fonts/SourceHanSansSC-Normal.otf" # 推荐使用思源黑体
    if not os.path.exists(test_font_path):
        print(f"\n[警告] 测试需要字体文件: '{test_font_path}'。")
        print("请下载一个中文字体 (如思源黑体) 并放置在 'fonts' 目录下。")
        print("测试将跳过。")
    # 3. 检查API Key
    elif not os.environ.get("ARK_API_KEY"):
        print("\n[警告] 环境变量 ARK_API_KEY 未设置。")
        print("请在项目根目录下创建一个 .env 文件，并写入 ARK_API_KEY='您的密钥'。")
        print("测试将跳过。")
    else:
        # --- 定义测试参数 ---
        test_prompt = "一只可爱的橙色虎斑猫，坐在书房的窗台上，窗外是宁静的午后阳光，超高清细节，摄影风格"
        test_text = "场景一：午后的邂逅\n数据来源：模拟数据"
        test_output = "temp_assets/test_scene_output_centered.png" # 修改输出文件名以作区分

        print(f"\n测试参数:")
        print(f"  - 提示词: {test_prompt}")
        print(f"  - 叠加文字: {test_text.replace(chr(10), ' ')}") # 打印时将换行符替换为空格
        print(f"  - 输出路径: {test_output}")
        print(f"  - 字体路径: {test_font_path}")
        
        print("\n正在调用 create_scene_image 函数...")
        
        # --- 执行核心函数 ---
        success = create_scene_image(
            image_prompt=test_prompt,
            overlay_text=test_text,
            output_filepath=test_output,
            font_path=test_font_path
        )

        # --- 输出测试结果 ---
        if success:
            print(f"\n[成功] 测试完成！最终图片已保存至 '{os.path.abspath(test_output)}'")
        else:
            print("\n[失败] 测试未成功。请检查上面的错误日志以了解详情。")
            
    print("\n--- image_processor.py 模块测试结束 ---")
