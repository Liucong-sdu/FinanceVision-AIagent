# main.py
# 项目角色：自动化视频流水线总指挥 (Pipeline Orchestrator)
# 版本：最终集成版 (包含本地Whisper时间戳方案)

import argparse
import json
import os
import sys
import logging
import shutil
from pathlib import Path
from typing import List, Dict

# 导入所有依赖模块
try:
    import content_generator
    import audio_producer
    import image_processor
    import video_assembler
except ImportError as e:
    logging.error(f"错误：无法导入必要的模块。请确保所有 .py 文件都在同一目录下。错误详情: {e}")
    sys.exit(1)

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def calculate_scene_durations(scenes: List[Dict], word_timestamps: List[Dict]) -> List[Dict]:
    """
    【升级版】根据场景旁白和词级别时间戳，智能计算每个场景的精确时长。
    该函数通过滑动匹配的方式，处理Whisper可能产生的词语切分不一致问题。

    Args:
        scenes (List[Dict]): 包含'narration'的场景列表。
        word_timestamps (List[Dict]): Whisper生成的词级别时间戳列表。

    Returns:
        List[Dict]: 更新了'duration'键的场景列表。
    """
    logging.info("开始使用智能算法计算场景时长...")
    
    timestamp_cursor = 0  # 指向当前时间戳列表位置的指针

    for i, scene in enumerate(scenes):
        narration = scene.get('narration', '').strip()
        
        # 清理旁白文本，使其与Whisper的输出更接近。
        # Whisper的输出通常不包含标点，并且是连续的词语。
        # 我们将旁白处理成一个纯字符列表以进行匹配。
        clean_narration_chars = list("".join(filter(str.isalnum, narration)))

        if not clean_narration_chars:
            scene['duration'] = 2.0  # 为无旁白场景设置默认时长
            logging.warning(f"场景 {i+1} 无旁白，设置默认时长2秒。")
            continue

        scene_start_time = -1
        scene_end_time = -1
        start_found = False
        words_matched_in_scene = 0

        # 从指针当前位置开始，遍历时间戳列表
        for j in range(timestamp_cursor, len(word_timestamps)):
            current_word_info = word_timestamps[j]
            # 清理时间戳中的词语，逻辑与处理旁白时相同
            clean_word_text_chars = list("".join(filter(str.isalnum, current_word_info['text'])))

            if not clean_word_text_chars:
                continue # 跳过空的或纯标点的时间戳

            # 检查旁白剩余部分是否以当前时间戳词语开头
            if ''.join(clean_narration_chars).startswith(''.join(clean_word_text_chars)):
                if not start_found:
                    # 找到了场景的第一个匹配词
                    scene_start_time = current_word_info['start']
                    start_found = True
                
                # 无论是否是第一个词，都更新结束时间
                scene_end_time = current_word_info['end']
                words_matched_in_scene += 1
                
                # “消耗”掉已匹配的旁白字符
                del clean_narration_chars[:len(clean_word_text_chars)]
                
                # 如果当前场景的旁白已全部匹配完
                if not clean_narration_chars:
                    timestamp_cursor = j + 1 # 更新主指针，下次从下一个词开始
                    break
            else:
                # 如果已经开始匹配但突然中断，说明匹配结束
                if start_found:
                    logging.warning(f"场景 {i+1} 的旁白部分匹配完成。剩余未匹配部分: '{''.join(clean_narration_chars)}'")
                    timestamp_cursor = j # 下一个场景从当前词重新开始检查
                    break
    
        if start_found:
            # 计算时长（单位：秒），并增加0.3秒的缓冲区，让画面切换更从容
            duration_ms = scene_end_time - scene_start_time
            scene['duration'] = (duration_ms / 1000.0) + 0.3
            logging.info(f"场景 {i+1} 时长计算成功: {scene['duration']:.2f}秒 (匹配了 {words_matched_in_scene} 个时间戳词语)")
        else:
            # 如果遍历完所有时间戳都找不到匹配，给予一个警告和默认时长
            scene['duration'] = 5.0 # 给一个较长的默认值，方便排查问题
            logging.error(f"严重错误：无法为场景 {i+1} 的旁白 '{narration}' 找到匹配的时间戳。请检查文案和音频是否对应。")

    return scenes


def main():
    """
    主调度函数，执行整个视频生成流水线。
    """
    parser = argparse.ArgumentParser(description="自动化视频流水线主调度脚本")
    parser.add_argument("input_json", type=str, help="数据源JSON文件的完整路径")
    parser.add_argument("--output_dir", type=str, default="output/", help="指定输出视频的存放目录")
    args = parser.parse_args()

    logging.info("--- 自动化视频生成流程启动 ---")
    
    input_path = Path(args.input_json)
    if not input_path.is_file():
        logging.error(f"输入文件不存在: {args.input_json}")
        sys.exit(1)

    try:
        date_str = input_path.parent.name
        task_type = input_path.stem.split('_')[1] if len(input_path.stem.split('_')) > 1 else input_path.stem
        logging.info(f"成功解析任务信息: 日期={date_str}, 类型={task_type}")
    except IndexError:
        logging.error(f"无法从路径 {args.input_json} 中提取日期和任务类型。")
        sys.exit(1)

    temp_assets_dir = Path(f"temp_assets_{date_str}_{task_type}")
    temp_assets_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"创建临时素材目录: {temp_assets_dir}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # --- 步骤 1/5: 调度内容生成模块 ---
        logging.info("步骤 1/5: 调度内容生成模块...")
        with open(input_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        content_plan = content_generator.generate_content_plan(source_data)
        if not content_plan or 'scenes' not in content_plan or not content_plan['scenes']:
            logging.error("内容生成失败，未返回有效的场景列表。流程终止。")
            sys.exit(1)
        logging.info(f"内容生成成功，共 {len(content_plan['scenes'])} 个场景。")

        # --- 步骤 2/5: 调度音频生成与时间戳对齐 ---
        logging.info("步骤 2/5: 调度音频生成与时间戳对齐...")
        full_narration = " ".join([scene.get('narration', '') for scene in content_plan['scenes']]).strip()
        
        if not full_narration:
            logging.error("所有场景均无旁白文案，无法生成音频。流程终止。")
            sys.exit(1)

        # 步骤 2a: 生成纯音频
        audio_path = audio_producer.generate_audio_only(
            full_script=full_narration, 
            output_dir=str(temp_assets_dir)
        )
        if not audio_path:
            logging.error("音频文件生成失败。流程终止。")
            sys.exit(1)
        logging.info(f"音频文件生成成功，位于: {audio_path}")

        # 步骤 2b: 使用本地模型生成时间戳
        word_timestamps = audio_producer.generate_timestamps_from_audio(
            audio_path=audio_path,
            original_script=full_narration
        )
        if not word_timestamps:
            logging.error("本地时间戳生成失败。流程终止。")
            sys.exit(1)
        logging.info(f"获取到 {len(word_timestamps)} 个词语的时间戳。")

        # --- 步骤 3/5: 数据对齐 - 计算每个场景的精确时长 ---
        logging.info("步骤 3/5: 数据对齐 - 计算每个场景的精确时长...")
        scenes_with_duration = calculate_scene_durations(content_plan['scenes'], word_timestamps)
        
        # --- 步骤 4/5: 循环生成所有场景图片 ---
        logging.info("步骤 4/5: 循环生成所有场景图片...")
        production_list = []
        for i, scene in enumerate(scenes_with_duration):
            scene_number = i + 1
            logging.info(f"  - 正在处理场景 {scene_number}/{len(scenes_with_duration)}...")
            
            image_output_path = temp_assets_dir / f"scene_{scene_number}.png"
            
            success = image_processor.create_scene_image(
                image_prompt=scene.get('visual_prompt', 'Abstract background, calm colors, minimalist style'),
            
                output_filepath=str(image_output_path)
            )

            if not success:
                logging.error(f"场景 {scene_number} 的图片生成失败。流程终止。")
                sys.exit(1)

            production_list.append({
                'image_path': str(image_output_path),
                'duration': scene.get('duration', 2.0)
            })
        logging.info("所有场景图片已成功生成。")

        # --- 步骤 5/5: 调度视频合成模块 ---
        logging.info("步骤 5/5: 调度视频合成模块...")
        final_video_path = output_dir / f"{date_str}_{task_type}_report.mp4"
        
        success = video_assembler.assemble_video(
            production_list=production_list, 
            audio_filepath=str(audio_path), 
            output_filepath=str(final_video_path)
        )
        
        if not success:
            logging.error("最终视频合成失败。流程终止。")
            sys.exit(1)

        logging.info("--- 自动化视频生成流程成功 ---")
        logging.info(f"✅ 成品视频已生成: {final_video_path.resolve()}")

    except Exception as e:
        logging.error(f"流程执行过程中发生未预料的错误: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        if temp_assets_dir.exists():
            logging.info(f"正在清理临时文件目录: {temp_assets_dir}")
            try:
                shutil.rmtree(temp_assets_dir)
                logging.info("临时文件已清理。")
            except OSError as e:
                logging.error(f"清理临时目录失败: {e}")

if __name__ == "__main__":
    main()
