import json
from content_generator import generate_content_plan

def main():
    """
    测试 generate_content_plan 函数的主函数。
    """
    # 1. 准备一份模拟的 daily_data
    # 在实际应用中，这部分数据会从爬虫的JSON文件中读取
    mock_daily_data = {
        "date": "2025-08-14",
        "market_summary": {
            "a_share": {
                "shanghai_composite": {"value": "3050.12", "change": "+0.5%"},
                "shenzhen_component": {"value": "9500.45", "change": "-0.2%"},
                "chiNext": {"value": "1850.78", "change": "+1.1%"}
            },
            "us_stock": {
                "dow_jones": {"value": "39000.88", "change": "+0.8%"},
                "nasdaq": {"value": "17500.21", "change": "+1.5%"}
            }
        },
        "hot_sectors": [
            {"name": "新能源汽车", "reason": "政策利好，销量数据超预期", "leading_stock": "未来汽车"},
            {"name": "人工智能", "reason": "某科技巨头发布新一代AI芯片", "leading_stock": "智慧科技"},
            {"name": "半导体", "reason": "国产替代进程加速", "leading_stock": "核心制造"}
        ],
        "major_news": [
            "央行宣布维持基准利率不变，释放稳定信号。",
            "美国发布最新非农就业数据，好于市场预期，美联储加息压力增大。"
        ],
        "expert_opinion": "分析师认为，市场短期内将维持震荡格局，结构性机会依然存在于科技和消费领域。"
    }

    print("--- 开始生成视频内容规划 ---")
    
    # 2. 调用核心函数
    content_plan = generate_content_plan(mock_daily_data)

    print("\n--- 生成结果 ---")
    if content_plan:
        # 使用json.dumps进行格式化打印，使输出更美观
        print(json.dumps(content_plan, indent=4, ensure_ascii=False))
    else:
        print("生成失败，返回空字典 {}。请检查控制台输出的错误信息。")

if __name__ == "__main__":
    main()
