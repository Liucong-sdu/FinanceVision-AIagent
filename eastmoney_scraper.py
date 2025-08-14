# -*- coding: utf-8 -*-
"""
Eastmoney Financial Data Scraper (Revised)

This script scrapes daily A-share market data from eastmoney.com.
It provides two main functions:
1. scrape_midday_data(): For scraping data after the morn# ==============================================================================
# 3. 任务调度与输出 (Task Orchestration & Output)
# ==============================================================================

def save_to_json_file(data: dict, data_type: str) -> str:ession closes.
2. scrape_eod_data(): For scraping complete data after the market closes for the day.

Author: AI Python Development Expert
Date: 2025-08-14
Revision: 1.2 - Upgraded APIs for market sentiment and sector rankings for stability. Fixed index codes.
"""

import requests
import json
import time
import random
import os
from datetime import datetime
import argparse

# ==============================================================================
# 1. 配置模块 (Configuration Module)
# ==============================================================================

CONFIG = {
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'http://data.eastmoney.com/',
        'Connection': 'keep-alive',
    },
    'api': {
        # 大盘核心指数
        'market_indices': 'http://push2.eastmoney.com/api/qt/ulist.np/get',
        # 【新】市场情绪概览 (涨跌家数等)
        'market_sentiment_summary': 'https://datacenter-web.eastmoney.com/api/data/v1/get',
        # 北向资金
        'northbound_flow': 'http://datacenter-web.eastmoney.com/api/data/v1/get',
        # 板块排行 (行业/概念)
        'sector_ranking': 'http://push2.eastmoney.com/api/qt/clist/get',
        # 个股龙虎榜
        'long_hu_bang': 'http://datacenter-web.eastmoney.com/api/data/v1/get',
    },
    'params': {
        'market_indices_fields': "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18",
        # 【修正】更新科创50指数代码
        'market_indices_codes': "1.000001,0.399001,0.399006,1.000688", # 上证, 深证, 创业, 科创50
        # 【新】市场情绪概览报告名称
        'market_sentiment_report_name': "RPT_A_STOCK_MARKET_SURVEY",
        'northbound_report_name': "RPT_MUTUAL_DEAL_STA",
        'sector_ranking_fields': "f2,f3,f12,f14,f62,f128,f136,f152",
        'long_hu_bang_report_name': "RPT_DAILYBILLBOARD_DETAILS",
    }
}

# ==============================================================================
# 2. 核心抓取函数 (Core Scraping Functions)
# ==============================================================================

def _make_request(url: str, params: dict, method: str = 'GET') -> dict | None:
    """通用网络请求函数"""
    try:
        time.sleep(random.uniform(1, 2))
        if method.upper() == 'GET':
            response = requests.get(url, headers=CONFIG['headers'], params=params, timeout=10)
        else:
            response = requests.post(url, headers=CONFIG['headers'], data=params, timeout=10)
        response.raise_for_status()
        text = response.text
        if '(' in text and ')' in text:
            text = text[text.find('(') + 1 : text.rfind(')')]
        return json.loads(text)
    except requests.exceptions.RequestException as e:
        print(f"[-] 网络请求失败: {url}, 错误: {e}")
    except json.JSONDecodeError as e:
        print(f"[-] JSON解析失败: {url}, 响应内容: {response.text[:100]}..., 错误: {e}")
    except Exception as e:
        print(f"[-] 发生未知错误: {e}")
    return None

def get_market_indices() -> list:
    """抓取四大核心指数数据"""
    print("[+] 正在抓取大盘核心指数...")
    params = {
        'pn': '1', 'pz': '10', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'secids': CONFIG['params']['market_indices_codes'],
        'fields': CONFIG['params']['market_indices_fields'],
        '_': str(int(time.time() * 1000))
    }
    data = _make_request(CONFIG['api']['market_indices'], params)
    if not data or not data.get('data') or not data['data'].get('diff'):
        print("[-] 未能获取大盘指数数据。")
        return []
    indices_list = []
    for item in data['data']['diff']:
        indices_list.append({
            "name": item.get('f14', '-'),
            "current_point": item.get('f2', 0),
            "change_amount": item.get('f4', 0),
            "change_percent": item.get('f3', 0),
            "turnover_value_cny_billion": round(item.get('f6', 0) / 100000000, 2),
            "turnover_volume_hand": round(item.get('f5', 0) / 100),
            "open_point": item.get('f17', 0),
            "high_point": item.get('f15', 0),
            "low_point": item.get('f16', 0)
        })
    return indices_list

def get_market_sentiment() -> dict:
    """【已重构】抓取市场情绪数据，包括涨跌家数、北向资金等"""
    print("[+] 正在抓取市场情绪概览...")
    sentiment_data = {}
    trade_date = datetime.now().strftime('%Y-%m-%d')

    # 1. 【新API】获取涨跌家数、涨跌停等
    params_summary = {
        'columns': 'ALL',
        'filter': f"(TRADE_DATE='{trade_date}')",
        'reportName': CONFIG['params']['market_sentiment_report_name'],
        'source': 'WEB',
        '_': str(int(time.time() * 1000))
    }
    summary_data = _make_request(CONFIG['api']['market_sentiment_summary'], params_summary)
    if summary_data and summary_data.get('result') and summary_data['result'].get('data'):
        market_info = summary_data['result']['data'][0]
        sentiment_data.update({
            "rising_count": market_info.get('UP_COUNT', 0),
            "falling_count": market_info.get('DOWN_COUNT', 0),
            "flat_count": market_info.get('FLAT_COUNT', 0),
            "limit_up_count": market_info.get('LIMIT_UP_COUNT', 0),
            "limit_down_count": market_info.get('LIMIT_DOWN_COUNT', 0),
            "yesterday_limit_up_performance": f"{market_info.get('ZT_YESTERDAY_PERFORMANCE', 0)}%"
        })
    else:
        print("[-] 未能获取涨跌家数数据（可能是非交易日）。")

    # 2. 获取北向资金
    params_north = {
        'columns': 'ALL',
        'filter': f"(TRADE_DATE='{trade_date}')",
        'pageNumber': '1', 'pageSize': '1',
        'reportName': CONFIG['params']['northbound_report_name'],
        'sortColumns': 'TRADE_DATE', 'sortTypes': '-1',
        'source': 'WEB',
        '_': str(int(time.time() * 1000))
    }
    north_data = _make_request(CONFIG['api']['northbound_flow'], params_north)
    if north_data and north_data.get('result') and north_data['result'].get('data'):
        flow_info = north_data['result']['data'][0]
        sentiment_data["northbound_net_inflow_cny_billion"] = flow_info.get('NET_AMT', 0)
    else:
        print("[!] 未能获取北向资金数据（可能是非交易日或数据未更新）。")
        sentiment_data["northbound_net_inflow_cny_billion"] = "N/A"

    return sentiment_data

def get_sector_rankings() -> dict:
    """【已重构】抓取行业板块和概念板块涨幅榜Top 10"""
    print("[+] 正在抓取板块排行...")
    rankings = {"industry_top_10": [], "concept_top_10": []}

    def _fetch_top_sectors(board_type: str, fs_param: str) -> list:
        print(f"  - 正在获取 {board_type} Top 10...")
        params = {
            'pn': '1', 'pz': '10', 'po': '1', 'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2', 'invt': '2', 'fid': 'f3',
            'fs': fs_param, # 【修正】使用从官网分析出的最新稳定参数
            'fields': CONFIG['params']['sector_ranking_fields'],
            '_': str(int(time.time() * 1000))
        }
        data = _make_request(CONFIG['api']['sector_ranking'], params)
        sector_list = []
        if not data or not data.get('data') or not data['data'].get('diff'):
            print(f"[-] 未能获取{board_type}板块数据。")
            return []
        for item in data['data']['diff']:
            sector_list.append({
                "sector_name": item.get('f14', '-'),
                "change_percent": item.get('f3', 0),
                "leader_stock": {
                    "name": item.get('f128', '-'),
                    "change_percent": item.get('f136', 0)
                }
            })
        return sector_list

    # 【修正】使用最新的fs参数
    rankings["industry_top_10"] = _fetch_top_sectors("行业板块", "m:90+t:2+f:!50")
    rankings["concept_top_10"] = _fetch_top_sectors("概念板块", "m:90+t:3+f:!50")
    
    return rankings

def get_long_hu_bang() -> list:
    """抓取个股龙虎榜数据 (仅盘后)"""
    print("[+] 正在抓取个股龙虎榜...")
    params = {
        'columns': 'ALL',
        'filter': "(TRADE_DATE=^" + datetime.now().strftime('%Y-%m-%d') + "^)",
        'pageNumber': '1', 'pageSize': '200',
        'reportName': CONFIG['params']['long_hu_bang_report_name'],
        'sortColumns': 'TOTAL_BUY', 'sortTypes': '-1',
        'source': 'WEB',
        '_': str(int(time.time() * 1000))
    }
    data = _make_request(CONFIG['api']['long_hu_bang'], params)
    if not data or not data.get('result') or not data['result'].get('data'):
        print("[-] 未能获取龙虎榜数据（可能是非交易日或当日无股票上榜）。")
        return []
    lhb_list = []
    processed_codes = set()
    for item in data['result']['data']:
        stock_code = item.get('SECURITY_CODE')
        if stock_code in processed_codes: continue
        buyers, sellers = [], []
        for i in range(1, 6):
            if item.get(f'OPERATEDEPT_NAME_{i}'):
                buyers.append({"name": item.get(f'OPERATEDEPT_NAME_{i}'), "net_buy_cny_wan": round(item.get(f'BUY_{i}', 0) / 10000, 2)})
            if item.get(f'OPERATEDEPT_NAME_{i+5}'):
                 sellers.append({"name": item.get(f'OPERATEDEPT_NAME_{i+5}'), "net_sell_cny_wan": round(item.get(f'SELL_{i+5}', 0) / 10000, 2)})
        lhb_list.append({
            "stock_code": stock_code, "stock_name": item.get('SECURITY_NAME'),
            "reason": item.get('EXPLANATION'),
            "top_5_buyers": buyers, "top_5_sellers": sellers
        })
        processed_codes.add(stock_code)
    return lhb_list

# ==============================================================================
# 3. 任务调度与输出 (Task Orchestration & Output)
# ==============================================================================

def _save_to_json_file(data: dict, data_type: str) -> str:
    """
    将数据保存到按日期分类的JSON文件中
    
    Args:
        data: 要保存的数据字典
        data_type: 数据类型，'MIDDAY_DATA' 或 'EOD_DATA'
    
    Returns:
        str: 保存的文件路径
    """
    # 获取当前日期
    current_date = datetime.now()
    date_str = current_date.strftime('%Y-%m-%d')
    
    # 创建日期文件夹
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data', date_str)
    os.makedirs(data_dir, exist_ok=True)
    
    # 确定文件名
    time_period = "morning" if data_type == "MIDDAY_DATA" else "afternoon"
    timestamp = current_date.strftime('%H%M%S')
    filename = f"{date_str}_{time_period}_{timestamp}.json"
    filepath = os.path.join(data_dir, filename)
    
    # 保存文件
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n[✔] 数据已保存到: {filepath}")
        return filepath
    except Exception as e:
        print(f"\n[✘] 保存文件失败: {e}")
        return ""

def build_base_json(data_type: str) -> dict:
    """构建JSON输出的基础结构"""
    return {
        "crawl_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_type": data_type, "market_indices": [], "market_sentiment": {},
        "sector_rankings": {}, "long_hu_bang": []
    }

def scrape_midday_data() -> dict:
    """执行午间数据抓取任务"""
    print("\n" + "="*30 + "\n🚀 开始执行 [午间数据] 抓取任务...\n" + "="*30)
    output_json = build_base_json("MIDDAY_DATA")
    output_json["market_indices"] = get_market_indices()
    output_json["market_sentiment"] = get_market_sentiment()
    output_json["sector_rankings"] = get_sector_rankings()
    del output_json["long_hu_bang"]
    
    # 自动保存为JSON文件
    _save_to_json_file(output_json, "MIDDAY_DATA")
    
    print("\n✅ [午间数据] 抓取任务完成！")
    return output_json

def scrape_eod_data() -> dict:
    """执行每日盘后数据抓取任务"""
    print("\n" + "="*30 + "\n🚀 开始执行 [盘后数据] 抓取任务...\n" + "="*30)
    output_json = build_base_json("EOD_DATA")
    output_json["market_indices"] = get_market_indices()
    output_json["market_sentiment"] = get_market_sentiment()
    output_json["sector_rankings"] = get_sector_rankings()
    output_json["long_hu_bang"] = get_long_hu_bang()
    
    # 自动保存为JSON文件
    _save_to_json_file(output_json, "EOD_DATA")
    
    print("\n✅ [盘后数据] 抓取任务完成！")
    return output_json

# ==============================================================================
# 4. 主程序入口 (Main Execution Block)
# ==============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="东方财富网财经数据爬虫 (版本 1.2)")
    parser.add_argument('task', type=str, choices=['midday', 'eod'], help="选择任务: 'midday' (午间) 或 'eod' (盘后)")
    parser.add_argument('--output', type=str, default='', help="指定输出JSON文件的路径 (可选)")
    args = parser.parse_args()
    
    result_data = None
    if args.task == 'midday':
        result_data = scrape_midday_data()
    elif args.task == 'eod':
        result_data = scrape_eod_data()
    
    if result_data:
        json_output = json.dumps(result_data, ensure_ascii=False, indent=2)
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                print(f"\n[✔] 结果已成功保存到文件: {args.output}")
            except IOError as e:
                print(f"\n[✘] 保存文件失败: {e}")
        else:
            print("\n--- JSON 输出结果 ---\n" + json_output + "\n---------------------\n")

    # 新增：自动生成内容规划
   
