# -*- coding: utf-8 -*-
"""run_master.py —— 主表（真实采集数据）冒烟测试 + 断言电池
用法: python engine/run_master.py
断言覆盖：预算/油/能量带/蛋白/单食堂/现做≤1/售罄/忌口/辣度/减脂无油炸/
          套餐档位基数/米饭入账/称重克重带/同名菜≤1/双配额/Top3排他/确定性
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader
import core

MASTER = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '干饭决策机_数据采集_主表.xlsx'))

REQS = [
    ('R1 减脂 B=18 午12:30 忌猪', dict(scenario='减脂', B=18, period='午', asof='12:30', anchor='图书馆', spice_max=2, taboo={'猪'}, lazy=False)),
    ('R2 均衡 B=20 午12:30', dict(scenario='均衡', B=20, period='午', asof='12:30', anchor='图书馆', spice_max=2, taboo=set(), lazy=False)),
    ('R3 省钱 B=15 午12:00 教学楼', dict(scenario='省钱', B=15, period='午', asof='12:00', anchor='教学楼', spice_max=2, taboo=set(), lazy=False)),
    ('R4 夜宵21:00 B=40 宿舍区', dict(scenario='均衡', B=40, period='夜宵', asof='21:00', anchor='宿舍区', spice_max=2, taboo=set(), lazy=False)),
]

EPS = 1e-6


def dish_index(bundle):
    idx = {}
    for d in bundle['dishes']:
        idx[(d['name'], d['window'][2], d['pricing'])] = d
    return idx


def check_plan(idx, req, scen, p):
    """对单个方案跑硬断言，返回违规列表（空=全绿）。"""
    v = []
    relax = p.get('relax', {})
    r = lambda k: relax.get(k, 0.0)
    items = p['items']

    # C4 预算硬上界（任何情况下不得放宽）
    if p['PI'] > req['B'] + EPS:
        v.append(f"预算超支 {p['PI']}>{req['B']}")
    # C2 能量（放宽后）带内
    L, U = scen['E']
    elo = L * (1 - core.PRM['RBAR']['E_lo'] * r('热量下'))
    ehi = U * (1 + core.PRM['RBAR']['E_hi'] * r('热量上'))
    if not (elo - 0.11 <= p['E'] <= ehi + 0.11):
        v.append(f"能量出带 {p['E']}∉[{elo:.0f},{ehi:.0f}]")
    # C3 蛋白
    qmin = scen['Pmin'] * (1 - core.PRM['RBAR']['Q'] * r('蛋白'))
    if p['Q'] < qmin - 0.11:
        v.append(f"蛋白不足 {p['Q']}<{qmin:.1f}")
    # C5 油（公示级不计入，同引擎口径）
    omax = scen['Omax'] + core.PRM['RBAR']['oil'] * r('油')
    if p['O'] > omax + 0.011:
        v.append(f"油超上限 {p['O']}>{omax:.1f}")
    # C10 单食堂
    if len(p['cant']) != 1:
        v.append(f"跨食堂 {p['cant']}")

    names = []
    for it in items:
        d = idx[(it['name'], it['win'], it['pricing'])]
        names.append(it['name'])
        # C16 忌口 / 辣度 / 时段 / 售罄 永不放宽
        if d['taboo'] & req['taboo']:
            v.append(f"忌口命中 {it['name']}")
        if d['spice'] > req['spice_max']:
            v.append(f"辣度超限 {it['name']}")
        if req['period'] not in d['periods']:
            v.append(f"时段不符 {it['name']}")
        if d['soldout'] and core._t(req['asof']) >= core._t(d['soldout']):
            v.append(f"售罄窗口 {it['win']}")
        if scen['ban_fried'] and d['cook'] == '油炸':
            v.append(f"减脂含油炸 {it['name']}")
        # 称重克重 ∈ [0.5,1.5]×wref
        if it['pricing'] == '称重':
            if not (0.5 * d['wref'] - 1 <= it['grams'] <= 1.5 * d['wref'] + 1):
                v.append(f"称重克重出带 {it['name']} {it['grams']}g wref={d['wref']}")
            # ρ×总重 恒等
            if abs(it['price'] - round(d['rho'] * it['grams'], 2)) > 0.011:
                v.append(f"称重价不符 {it['name']}")
        elif abs(it['grams'] - d['gram']) > EPS:
            v.append(f"克重与主表不符 {it['name']}")
    # C7 现做≤1
    fresh = [it['name'] for it in items if idx[(it['name'], it['win'], it['pricing'])]['fresh']]
    if len(fresh) > 1:
        v.append(f"现做>1 {fresh}")
    # C13.5 同名菜≤1
    if len(names) != len(set(names)):
        v.append("同名菜重复")
    # C12 套餐档位基数 + C14 米饭入账
    if p.get('tier'):
        t = p['tier']
        nm = sum(1 for it in items if it['pricing'] == '套餐' and it['tier_slot'] == '荤')
        nv = sum(1 for it in items if it['pricing'] == '套餐' and it['tier_slot'] == '素')
        if nm != t['n_meat'] or nv != t['n_veg']:
            v.append(f"档位基数不符 {nm}荤{nv}素 ≠ {t['n_meat']}荤{t['n_veg']}素")
        if t['mode'] in ('含米饭', '米饭+1元'):
            if '米饭(套餐)' not in p['names']:
                v.append("米饭未入 names")
            e_items = sum(it['grams'] / 100 * idx[(it['name'], it['win'], it['pricing'])]['kcal100'] for it in items)
            expect = e_items + t['rice_g'] * core.PRM['RICE_KCAL100'] / 100
            if abs(expect - p['E']) > 0.15:
                v.append(f"米饭热量未入账 E={p['E']} 应={expect:.1f}")
            up = core.PRM['RICE_UP'] if t['mode'] == '米饭+1元' else 0.0
            if abs(p['PI'] - (t['price'] + up + sum(it['price'] for it in items if it['pricing'] != '套餐'))) > 0.011:
                v.append("套餐价未按档位入账")
    return v


def check_top3(req, res):
    """Top3 级断言：排他 + 双配额。
    含降级补位的场景（严格配额凑不满三套、显式放宽多样性）不再检查双配额。"""
    v = []
    tops = res['top3']
    sigs = [p['sig'] for p in tops]
    if len(sigs) != len(set(sigs)):
        v.append('Top3 签名重复')
    if any(p.get('degraded') for p in tops):
        return v
    for i, p in enumerate(tops):
        if sum(q['label'] == p['label'] for q in tops) > 2:
            v.append(f"内容通道>2 {p['label']}")
        if sum(1 for q in tops if set(q['wins']) & set(p['wins'])) > 2:
            v.append(f"同窗口>2 {p['wins']}")
    return v


def main():
    t0 = time.time()
    b = loader.load(MASTER)
    idx = dish_index(b)
    print(f"装载: {len(b['dishes'])}菜/{len(b['windows'])}窗/{len(b['std'])}标准名 "
          f"ρ={len(b['rho'])} 档位={sum(len(v) for v in b['tiers'].values())} | {time.time()-t0:.1f}s")
    passed = failed = 0
    for label, req in REQS:
        res = core.recommend(b, req)
        scen = core.resolve(req['scenario'], req.get('lazy', False))
        print(f'== {label} | 存活{res["alive"]} 相位{res.get("phase")} 池{len(res["pool"])} 耗时{res["elapsed"]}s')
        if res.get('error'):
            print('   [!]', res['error'])
            failed += 1
            continue
        for i, p in enumerate(res['top3'], 1):
            tag = f"【{p['status']}】C={p['C']:.3f} {p['label']}" if 'C' in p else f"【{p['status']}】"
            print(f"  Top{i} {tag} | {p['cant']} Π={p['PI']}元 E={p['E']}kcal Q={p['Q']}g 油={p['O']}g")
            for it in p['items']:
                print(f"     · {it['name']} @{it['win']} [{it['pricing']}] {it['grams']}g")
            if p.get('tier'):
                t = p['tier']
                print(f"     · 档位: {t['n_meat']}荤{t['n_veg']}素={t['price']}元")
            if p.get('relax'):
                print(f"     · 放宽披露: {p['relax']}")
            for msg in check_plan(idx, req, scen, p):
                print(f"     [FAIL Top{i}] {msg}")
                failed += 1
            passed += 1
        for msg in check_top3(req, res):
            print(f'   [FAIL Top3] {msg}')
            failed += 1
        # 确定性：同请求两次结果一致
        res2 = core.recommend(b, req)
        same = [p['sig'] for p in res['top3']] == [p['sig'] for p in res2['top3']] and \
               [p['sig'] for p in res['pool']] == [p['sig'] for p in res2['pool']]
        print(f'   确定性: {"一致 ✓" if same else "不一致 ✗"}')
        if not same:
            failed += 1
        passed += 1
    print(f'\n断言电池: {"全绿 ✓" if failed == 0 else f"{failed} 项失败 ✗"} | 总耗时 {time.time()-t0:.1f}s')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
