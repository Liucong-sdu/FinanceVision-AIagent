# video_assembler.py

import ffmpeg
import os
import logging
from typing import List, Dict

# 配置日志记录，方便调试
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def assemble_video(production_list: List[Dict], audio_filepath: str, output_filepath: str, fps: int = 24) -> bool:
    """
    使用 ffmpeg-python 将所有素材合成为最终视频。

    Args:
        production_list (List[Dict]): 包含所有场景图片路径和对应时长的制作清单。
        audio_filepath (str): 主音频文件的路径。
        output_filepath (str): 最终输出的MP4视频文件路径。
        fps (int): 视频的帧率，默认为24。

    Returns:
        bool: 如果视频合成成功，返回 True；如果发生任何错误，返回 False。
    """
    if not production_list:
        logging.error("制作清单 (production_list) 为空，无法创建视频。")
        return False

    try:
        # 1. 创建图片输入流列表
        image_streams = []
        logging.info("开始准备视频流...")
        for item in production_list:
            image_path = item['image_path']
            duration = item['duration']
            
            if not os.path.exists(image_path):
                logging.error(f"图片文件不存在: {image_path}")
                return False

            # 为每个图片创建一个输入流
            # loop=1: 让图片作为视频流持续存在
            # t=duration: 设置该图片流的持续时间
            # r=fps: 设置该流的帧率
            stream = ffmpeg.input(image_path, loop=1, t=duration, r=fps)
            image_streams.append(stream)
        
        logging.info(f"已成功创建 {len(image_streams)} 个图片输入流。")

        # 2. 拼接所有图片流为一个视频流
        # v=1, a=0 表示只拼接视频部分(video=1)，不处理音频(audio=0)
        concatenated_video = ffmpeg.concat(*image_streams, v=1, a=0)
        logging.info("视频流拼接完成。")

        # 3. 创建音频输入流
        if not os.path.exists(audio_filepath):
            logging.error(f"音频文件不存在: {audio_filepath}")
            return False
            
        audio_stream = ffmpeg.input(audio_filepath)
        logging.info(f"音频流加载完成: {audio_filepath}")

        # 4. 合并视频流和音频流，并设置输出参数
        logging.info(f"开始将视频和音频合并到输出文件: {output_filepath}")
        stream = ffmpeg.output(
            concatenated_video,          # 拼接好的视频流
            audio_stream,                # 音频流
            output_filepath,             # 输出文件路径
            vcodec='libx264',            # 使用H.264视频编码器
            acodec='aac',                # 使用AAC音频编码器
            pix_fmt='yuv420p',           # 关键：确保颜色在所有播放器上正常
            r=fps                        # 设置最终输出的视频帧率
        )

        # 5. 执行FFmpeg命令
        # .overwrite_output() 允许覆盖已存在的同名文件
        # .run(quiet=True) 执行命令，并抑制FFmpeg在控制台的冗长日志
        stream.overwrite_output().run(quiet=True)

        logging.info(f"视频合成成功！文件已保存至: {output_filepath}")
        return True

    except ffmpeg.Error as e:
        # 关键的错误处理
        logging.error("FFmpeg 在视频合成过程中发生错误。")
        # 打印FFmpeg的原始错误输出，这对于调试至关重要
        print("\n--- FFmpeg Stderr Output ---\n")
        print(e.stderr.decode('utf8'))
        print("\n--------------------------\n")
        return False
    except Exception as e:
        # 捕获其他可能的异常，如文件路径问题等
        logging.error(f"发生未知错误: {e}")
        return False

# --- 测试代码 ---
# 如果这个脚本被直接运行，而不是作为模块导入，那么以下代码将被执行。
if __name__ == '__main__':
    print("="*50)
    print("模块四：视频合成模块 (ffmpeg-python 版本) - 测试程序")
    print("="*50)
    print("本测试将自动创建临时图片和音频文件用于合成视频。")
    print("测试前请确保已安装所需库: pip install ffmpeg-python numpy Pillow pydub")

    # 准备测试所需库
    try:
        import numpy as np
        from PIL import Image
        from pydub import AudioSegment
        from pydub.generators import Sine
    except ImportError as e:
        print(f"\n[错误] 缺少测试所需的库: {e.name}")
        print("请运行: pip install numpy Pillow pydub")
        exit(1)

    # 1. 创建临时资源目录
    temp_dir = 'temp_test_assets_for_video'
    os.makedirs(temp_dir, exist_ok=True)
    print(f"\n[1/4] 已创建临时目录: {temp_dir}")

    # 2. 创建测试用的图片
    scene1_path = os.path.join(temp_dir, 'scene_01.png')
    scene2_path = os.path.join(temp_dir, 'scene_02.png')
    
    # 创建一张蓝色背景带白色文字的图片
    img1_arr = np.full((720, 1280, 3), (50, 100, 200), dtype=np.uint8)
    img1 = Image.fromarray(img1_arr)
    # (Pillow在某些系统上需要字体文件才能写中文，这里用英文代替以保证通用性)
    # from PIL import ImageDraw
    # draw = ImageDraw.Draw(img1)
    # draw.text((400, 350), "Scene 1: This is the first scene.", fill=(255,255,255))
    img1.save(scene1_path)

    # 创建一张绿色背景的图片
    img2_arr = np.full((720, 1280, 3), (50, 200, 100), dtype=np.uint8)
    img2 = Image.fromarray(img2_arr)
    img2.save(scene2_path)
    print(f"[2/4] 已创建两张测试图片:\n      - {scene1_path}\n      - {scene2_path}")

    # 3. 创建测试用的音频
    audio_path = os.path.join(temp_dir, 'final_audio.mp3')
    scene1_duration = 3.5  # 秒
    scene2_duration = 4.0  # 秒
    total_duration_ms = (scene1_duration + scene2_duration) * 1000

    # 生成一段正弦波作为音频
    sine_wave = Sine(440).to_audio_segment(duration=total_duration_ms, volume=-10)
    sine_wave.export(audio_path, format="mp3")
    print(f"[3/4] 已创建测试音频 (总时长 {total_duration_ms/1000}s): {audio_path}")

    # 4. 准备参数并调用函数
    test_production_list = [
        {'image_path': scene1_path, 'duration': scene1_duration},
        {'image_path': scene2_path, 'duration': scene2_duration}
    ]
    output_video_path = 'final_video_test.mp4'

    print(f"\n[4/4] 开始调用 assemble_video 函数...")
    print(f"      - 制作清单: {len(test_production_list)}个场景")
    print(f"      - 音频文件: {audio_path}")
    print(f"      - 输出文件: {output_video_path}")
    print(f"      - 帧率: 30 fps")
    
    success = assemble_video(
        production_list=test_production_list,
        audio_filepath=audio_path,
        output_filepath=output_video_path,
        fps=30
    )

    print("\n" + "="*50)
    if success and os.path.exists(output_video_path):
        print(f"✅ 测试成功！")
        print(f"最终视频已生成: {os.path.abspath(output_video_path)}")
        print("您可以播放此文件以验证结果。")
    else:
        print(f"❌ 测试失败。")
        print("请检查上面日志中的 FFmpeg 错误信息。")
        print("常见原因包括：")
        print("  - 未安装 FFmpeg 或未将其添加到系统环境变量 PATH。")
        print("  - 输入文件路径不正确或文件损坏。")
    print("="*50)

    # 提示：测试生成的临时文件和视频可以手动删除。
    # import shutil
    # shutil.rmtree(temp_dir)
    # os.remove(output_video_path)
