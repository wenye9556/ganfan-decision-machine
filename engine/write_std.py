# -*- coding: utf-8 -*-
"""打标结果落表：标准菜名表写入 + 克重回填 + 采集名↔标准名全覆盖校验"""
import json
import openpyxl
from openpyxl.styles import Font
from merge_std import main as merge_main, hotpot_std, HOTPOT

MASTER = '干饭决策机_数据采集_主表.xlsx'

tagged, problems = merge_main()

# name → 品类/辣度（来自采集表输入）
meta = {}
for i in range(1, 6):
    for x in json.load(open(f'engine/tag_in_{i}.json', encoding='utf-8')):
        meta.setdefault(x['name'], (x['cat'], x['spice']))
for n, x in hotpot_std().items():
    meta.setdefault(n, (x['cat'], '不辣'))

wb = openpyxl.load_workbook(MASTER)

# ---------- 标准菜名表：清示例行后写入 ----------
ws = wb['标准菜名表']
assert ws.cell(row=4, column=2).value == '标准菜名'
for r in range(5, ws.max_row + 2):
    for c in range(2, 18):
        ws.cell(row=r, column=c).value = None
r = 5
for name, x in tagged.items():
    cat, spice = meta.get(name, ('主食', '不辣'))
    recipe = ';'.join(f'{c} {p}%' for c, p in x['recipe'])
    vals = [name, '—', cat, x['slots'][0], x['slots'][1], x['slots'][2], x['slots'][3],
            spice, x['taboo'], x['cook'], x['absorb'], recipe, x['conf'],
            x['kcal100'], x['prot100'], x['taste']]
    for j, v in enumerate(vals):
        ws.cell(row=r, column=2 + j, value=v)
    r += 1
n_std = r - 5
print(f'标准菜名表: 写入 {n_std} 行')

# ---------- 克重回填（非称重行） ----------
grams = {n: x['est_gram'] for n, x in tagged.items()}
filled = 0
for sh in ['D区食堂一层', 'D区食堂二层', 'F区食堂一层', 'F区食堂二层', 'B区食堂', '校内饭店']:
    ws = wb[sh]
    for rr in range(5, ws.max_row + 1):
        name = ws.cell(row=rr, column=4).value
        if not name or ws.cell(row=rr, column=3).value == '称重':
            continue
        if ws.cell(row=rr, column=6).value is None and name in grams:
            ws.cell(row=rr, column=6, value=grams[name])
            note = ws.cell(row=rr, column=10).value or ''
            ws.cell(row=rr, column=10, value=note + ('；' if note else '') + '克重AI估计待实测')
            filled += 1
print(f'克重回填: {filled} 行')

# ---------- 覆盖校验：采集菜名 ⊆ 标准菜名 ----------
missing = set()
for sh in ['D区食堂一层', 'D区食堂二层', 'F区食堂一层', 'F区食堂二层', 'B区食堂', '校内饭店']:
    ws = wb[sh]
    for rr in range(5, ws.max_row + 1):
        name = ws.cell(row=rr, column=4).value
        if name and name not in tagged:
            missing.add(f'{sh}:{name}')
print('采集名未覆盖:', missing if missing else '无 ✓')

wb.save(MASTER)
print('saved:', MASTER)
