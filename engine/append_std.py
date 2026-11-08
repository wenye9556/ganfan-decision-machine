# -*- coding: utf-8 -*-
"""append_std.py —— D区一层打标结果【追加】进标准菜名表（不清空既有行）+ 克重回填 + 覆盖校验
前置：engine/tag_in_d1.json + engine/tag_out_d1_{1,2,3}.json
用法: python engine/append_std.py
"""
import json
import os
import sys
import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_std import LIB, TABOO_SET, COOKS, ABSORB, CONFS, TASTES

MASTER = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '干饭决策机_数据采集_主表.xlsx'))
ENG = os.path.dirname(os.path.abspath(__file__))


def calc(recipe):
    kcal = prot = 0.0
    tot = sum(p for _, p in recipe)
    assert abs(tot - 100) <= 5, f'百分比合计异常 {tot}'
    for comp, p in recipe:
        if comp in LIB:
            k, pr = LIB[comp]
        elif comp.startswith('新组件:'):
            kv, pv = comp[4:].split(',')
            k, pr = float(kv), float(pv)
        else:
            raise ValueError(f'未知组件 {comp}')
        kcal += k * p / tot
        prot += pr * p / tot
    return round(kcal, 1), round(prot, 1)


def main():
    inp = json.load(open(os.path.join(ENG, 'tag_in_d1.json'), encoding='utf-8'))
    meta = {x['name']: (x['cat'], x['spice']) for x in inp}
    out = []
    for i in (1, 2, 3):
        out += json.load(open(os.path.join(ENG, f'tag_out_d1_{i}.json'), encoding='utf-8'))
    assert len(out) == len(inp), f'数量不一致 {len(out)} vs {len(inp)}'
    assert {x['name'] for x in out} == set(meta), '菜名集合与输入不一致'

    problems = []
    for x in out:
        n = x['name']
        assert x['cook'] in COOKS, f'{n} 烹饪越界'
        assert x['absorb'] in ABSORB, f'{n} 吸油越界'
        assert x['conf'] in CONFS, f'{n} 置信越界'
        assert x['taste'] in TASTES, f'{n} 口味越界'
        tb = str(x['taboo']).strip()
        if tb not in ('—', ''):
            bad = {t for t in tb.split(',') if t.strip()} - TABOO_SET
            assert not bad, f'{n} 忌口越界 {bad}'
        assert len(x['slots']) == 4 and all(s in (0, 1) for s in x['slots']), f'{n} 槽位非法'
        assert sum(x['slots']) <= 3, f'{n} 总槽>3'
        if x.get('kcal100_override') is not None:
            x['kcal100'] = float(x['kcal100_override'])
            x['prot100'] = float(x.get('prot100_override') or 0)
        else:
            x['kcal100'], x['prot100'] = calc(x['recipe'])
        if not (10 <= x['kcal100'] <= 900):
            problems.append(f'{n}: kcal100={x["kcal100"]} 钳制')
            x['kcal100'] = min(max(x['kcal100'], 12.0), 880.0)
        assert 20 <= x['est_gram'] <= 2000, f'{n} 克重越界'

    wb = openpyxl.load_workbook(MASTER)
    ws = wb['标准菜名表']
    assert ws.cell(row=4, column=2).value == '标准菜名'
    existing = set()
    last = 4
    for r in range(5, ws.max_row + 1):
        v = ws.cell(row=r, column=2).value
        if v:
            existing.add(str(v).strip())
            last = r
    r = last + 1
    added = 0
    for x in out:
        n = x['name']
        if n in existing:
            continue
        cat, spice = meta[n]
        recipe = ';'.join(f'{c} {p}%' for c, p in x['recipe'])
        vals = [n, '—', cat, x['slots'][0], x['slots'][1], x['slots'][2], x['slots'][3],
                spice, x['taboo'], x['cook'], x['absorb'], recipe, x['conf'],
                x['kcal100'], x['prot100'], x['taste']]
        for j, v in enumerate(vals):
            ws.cell(row=r, column=2 + j, value=v)
        r += 1
        added += 1
    print(f'标准菜名表: 追加 {added} 行 → 共 {len(existing) + added} 唯一名')

    grams = {x['name']: x['est_gram'] for x in out}
    filled = 0
    for sh in ['D区食堂一层', 'D区食堂二层', 'F区食堂一层', 'F区食堂二层', 'B区食堂', '校内饭店']:
        ws2 = wb[sh]
        for rr in range(5, ws2.max_row + 1):
            name = ws2.cell(row=rr, column=4).value
            if not name or ws2.cell(row=rr, column=3).value == '称重':
                continue
            if ws2.cell(row=rr, column=6).value is None and name in grams:
                ws2.cell(row=rr, column=6, value=grams[name])
                note = ws2.cell(row=rr, column=10).value or ''
                ws2.cell(row=rr, column=10, value=note + ('；' if note else '') + '克重AI估计待实测')
                filled += 1
    print(f'克重回填: {filled} 行')

    missing = set()
    for sh in ['D区食堂一层', 'D区食堂二层', 'F区食堂一层', 'F区食堂二层', 'B区食堂', '校内饭店']:
        ws2 = wb[sh]
        for rr in range(5, ws2.max_row + 1):
            name = ws2.cell(row=rr, column=4).value
            if name and str(name).strip() not in existing and str(name).strip() not in {x['name'] for x in out}:
                missing.add(f'{sh}:{name}')
    print('采集名未覆盖:', missing if missing else '无 ✓')
    for p in problems:
        print('  [!]', p)

    wb.save(MASTER)
    print('saved:', MASTER)


if __name__ == '__main__':
    main()
