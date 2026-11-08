# -*- coding: utf-8 -*-
"""run_nl.py —— NL Agent 链路验收：3句典型口语 → 结构化JSON → Top3 → 一句解释
用法: python engine/run_nl.py  （可选 --parse-only 只验证解析）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader
import core
import nl_agent

MASTER = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '干饭决策机_数据采集_主表.xlsx'))

SAMPLES = [
    '减脂，18块，不吃猪',
    '中午在图书馆，想吃点便宜的，15块以内，不要太辣',
    '晚上懒得走，均衡点，20块，不吃牛和蛋',   # 懒人+晚+双忌口（裸词"牛"），稳定出3套
]


def main():
    only_parse = '--parse-only' in sys.argv
    b = None if only_parse else loader.load(MASTER)
    for text in SAMPLES:
        req, meta = nl_agent.parse(text)
        print(f'\n>>> "{text}"')
        print('  解析:', json.dumps(dict(req, taboo=sorted(req['taboo'])), ensure_ascii=False), f'[{meta["parser"]}]')
        if only_parse:
            continue
        res = core.recommend(b, req)
        reasons = nl_agent.explain(req, res)
        for i, p in enumerate(res['top3'], 1):
            print(f"  Top{i} 【{p['status']}】{p['label']} Π={p['PI']} E={p['E']} Q={p['Q']} 油={p['O']} {p['wins']}")
            print('     💬', reasons[i - 1])
        if not res['top3']:
            print('  [!] 无解/降级:', res.get('error', '候选不足'))


if __name__ == '__main__':
    main()
