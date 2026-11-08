# -*- coding: utf-8 -*-
"""pregen_cache.py —— 预生成代表性请求方案缓存（演示<0.1s命中）
用法: python engine/pregen_cache.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader
import cache as C

MASTER = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '干饭决策机_数据采集_主表.xlsx'))


def R(scenario, B, period='午', asof='12:30', anchor='图书馆', spice_max=2, taboo=(), lazy=False):
    return dict(scenario=scenario, B=B, period=period, asof=asof, anchor=anchor,
                spice_max=spice_max, taboo=set(taboo), lazy=lazy)


def build_reqs():
    reqs = []
    # 午餐主力矩阵（图书馆/教学楼）
    for B in (15, 18, 20):
        for tb in ((), ('猪',)):
            reqs.append(R('减脂', B, taboo=tb))
    for B in (15, 20, 25):
        for tb in ((), ('猪',)):
            reqs.append(R('均衡', B, taboo=tb))
    for B in (20, 25, 30):
        reqs.append(R('增肌', B))
    for B in (10, 12, 15):
        reqs.append(R('省钱', B))
    for B in (18, 20):
        reqs.append(R('均衡', B, anchor='教学楼'))
        reqs.append(R('省钱', B, anchor='宿舍区'))
    # 晚餐（宿舍区）
    reqs += [R('减脂', 18, '晚', '18:30', '宿舍区'), R('减脂', 18, '晚', '18:30', '宿舍区', taboo=('猪',)),
             R('增肌', 25, '晚', '18:30', '宿舍区'), R('均衡', 20, '晚', '18:30', '宿舍区'),
             R('省钱', 12, '晚', '18:30', '宿舍区'), R('均衡', 20, '晚', '18:30', '图书馆')]
    # 夜宵
    reqs += [R('均衡', 25, '夜宵', '21:30', '宿舍区'), R('均衡', 40, '夜宵', '21:30', '宿舍区'),
             R('省钱', 20, '夜宵', '21:30', '宿舍区'), R('增肌', 30, '夜宵', '21:30', '宿舍区')]
    # 早餐 / 下午
    reqs += [R('均衡', 10, '早', '08:00', '教学楼'), R('均衡', 15, '早', '08:00', '教学楼'),
             R('减脂', 12, '早', '08:00', '教学楼'), R('省钱', 8, '早', '08:00', '宿舍区'),
             R('均衡', 15, '下午', '15:00', '图书馆'), R('省钱', 10, '下午', '15:00', '图书馆')]
    # 懒人模式
    reqs += [R('均衡', 20, anchor='教学楼', lazy=True), R('减脂', 18, anchor='教学楼', lazy=True),
             R('增肌', 25, anchor='宿舍区', lazy=True), R('省钱', 15, anchor='教学楼', lazy=True)]
    # 辣度 / 忌口变体
    reqs += [R('减脂', 18, spice_max=0), R('省钱', 15, spice_max=1), R('均衡', 20, spice_max=0),
             R('均衡', 20, taboo=('海鲜',)), R('均衡', 20, taboo=('蛋',)), R('增肌', 25, taboo=('牛',)),
             R('减脂', 20, taboo=('海鲜', '香菜')), R('省钱', 12, taboo=('猪', '牛')),
             R('增肌', 25, '晚', '18:30', '图书馆', taboo=('海鲜', '香菜'), lazy=True)]
    # 去重
    seen, out = set(), []
    for r in reqs:
        k = C.req_key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def main():
    b = loader.load(MASTER)
    pc = C.PlanCache()
    reqs = build_reqs()
    print(f'预生成 {len(reqs)} 个代表性请求（已有缓存 {len(pc.store)}）', flush=True)
    t0 = time.time()
    for i, req in enumerate(reqs, 1):
        if pc.get(req):
            print(f'[{i}/{len(reqs)}] 已存在，跳过', flush=True)
            continue
        t1 = time.time()
        res, reasons, meta = C.solve(b, req, cache=pc, origin='pregen')
        n = len(res.get('top3', []))
        print(f'[{i}/{len(reqs)}] {req["scenario"]} B={req["B"]} {req["period"]} '
              f'lazy={req["lazy"]} → Top{n} | {time.time()-t1:.1f}s', flush=True)
    print(f'完成，缓存共 {len(pc.store)} 条 | 总耗时 {time.time()-t0:.0f}s → {pc.path}')


if __name__ == '__main__':
    main()
