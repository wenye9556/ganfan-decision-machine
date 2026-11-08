# -*- coding: utf-8 -*-
"""export_video_data.py —— 引擎数据导出给 Remotion：统计/三场景方案/示例周报
输出: video/public/data/{stats,plans,week}.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader
import cache as C

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'video', 'public', 'data')

b = loader.load(os.path.join(ROOT, '干饭决策机_数据采集_主表.xlsx'))
pc = C.PlanCache()
os.makedirs(OUT, exist_ok=True)

stats = dict(dishes=len(b['dishes']), windows=len(b['windows']), areas=6, std=len(b['std']),
             rho_windows=len(b['rho']), tiers=sum(len(v) for v in b['tiers'].values()))
json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

plans = {}
for label, req in [
    ('减脂', dict(scenario='减脂', B=18, period='午', asof='12:30', anchor='图书馆', spice_max=2, taboo={'猪'}, lazy=False)),
    ('均衡', dict(scenario='均衡', B=20, period='午', asof='12:30', anchor='图书馆', spice_max=2, taboo=set(), lazy=False)),
    ('省钱', dict(scenario='省钱', B=15, period='午', asof='12:00', anchor='教学楼', spice_max=2, taboo=set(), lazy=False)),
]:
    ent = pc.get(req)
    if not ent:
        res, reasons, _ = C.solve(b, req, cache=pc)
        ent = dict(res=res, reasons=reasons)
    plans[label] = dict(req=C.norm_req(req), top3=ent['res']['top3'], reasons=ent['reasons'])
json.dump(plans, open(os.path.join(OUT, 'plans.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 视频脚本锁定口径的示例周报（演示数据，非真实打卡）
week = dict(n=11, normal=9, cheat=2, cheat_left=1, rate=82, cost=168.5,
            days=[dict(weekday=w, n=n, kcal=k) for w, n, k in
                  zip('一二三四五六日', [2, 2, 1, 2, 2, 1, 1], [1350, 1420, 640, 1510, 1380, 720, 590])],
            demo=True)
json.dump(week, open(os.path.join(OUT, 'week.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('exported →', OUT, stats)
