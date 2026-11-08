# -*- coding: utf-8 -*-
"""loader.py —— 按列名读取 seed/真实采集表 → Bundle；含完整性断言（§1.3 子集）。
只读原件；枚举真相源=数据字典口径（此处内置闭集常量，正式版应从字典 sheet 生成）。"""
import openpyxl, statistics

ENUM = {
    '计价方式': {'单品','按份','称重','套餐','套餐SKU'},
    '品类': {'主食','荤菜','半荤','素菜','汤','饮品'},
    '辣度': {'不辣','微辣','辣'},
    '烹饪方式': {'清蒸水煮','凉拌','少油炒','正常炒','爆炒过油','干煸','油炸'},
    '吸油等级': {'弱','中','强'},
    '置信级': {'公示级','计算级','估算级'},
    '主食模式': {'含米饭','米饭+1元','不含主食',''},
}
SPICE = {'不辣': 0, '微辣': 1, '辣': 2}
UNIT_G = {'元/50g': 50, '元/100g': 100, '元/斤': 500}
DISH_HEAD = ['窗口名称','计价方式','菜名','价格(元)','每份克重(g)','品类','辣度','是否招牌','备注']


def _rows(ws, header_row=4):
    """按表头名读成 dict 列表；返回 (rows, headers)。表头逐列严格校验由调用方做。"""
    hdr = {}
    for c in range(2, ws.max_column + 1):
        v = ws.cell(row=header_row, column=c).value
        if v: hdr[str(v).strip()] = c
    out = []
    for r in range(header_row + 1, ws.max_row + 1):
        row = {k: ws.cell(row=r, column=c).value for k, c in hdr.items()}
        if not any(row.values()): continue
        row['_r'] = r
        out.append(row)
    return out, hdr


def _f(v, what, r=''):
    if v is None or str(v).strip() in ('', '—'): return None
    try: return float(v)
    except Exception: raise ValueError(f'{what} 非数值: {v!r} (行{r})')


def load(path):
    wb = openpyxl.load_workbook(path, read_only=False)
    issues = []

    # ---- 标准菜名表 ----
    std_rows, std_hdr = _rows(wb['标准菜名表'])
    std = {}
    for r in std_rows:
        n = str(r['标准菜名']).strip()
        assert n not in std, f'标准菜名重复: {n}'
        cook = str(r['烹饪方式']).strip(); absorb = str(r['吸油等级']).strip()
        assert cook in ENUM['烹饪方式'], f'烹饪方式枚举越界 {cook}'
        assert absorb in ENUM['吸油等级']
        conf = str(r['置信级']).strip(); assert conf in ENUM['置信级']
        taboo = set() if str(r['忌口/过敏原']).strip() in ('', '—') else \
                {x.strip() for x in str(r['忌口/过敏原']).split(',') if x.strip()}
        std[n] = dict(
            slots=(int(r['槽位·主食']), int(r['槽位·荤蛋白']), int(r['槽位·素']), int(r['槽位·汤饮'])),
            spice=SPICE[str(r['辣度']).strip()], taboo=taboo, cook=cook, absorb=absorb,
            kcal100=_f(r['每100g热量(kcal)'], 'kcal100', r['_r']),
            prot100=_f(r['每100g蛋白(g)'], 'prot100', r['_r']),
            conf=conf, tag=str(r.get('口味标签') or '').strip())
        if conf == '公示级':
            assert sum(std[n]['slots']) >= 2, f'公示级SKU须多槽: {n}'
        assert 10 <= std[n]['kcal100'] <= 900, f'kcal100 值域: {n}'

    # ---- 油克系数表 / 品类克重表 ----
    oil = {}
    oil_rows, _ = _rows(wb['油克系数表'])
    for r in oil_rows:
        ck = str(r['烹饪方式']).strip()
        oil[(ck, '弱')] = _f(r['吸油·弱(g/100g)'], 'oil')
        oil[(ck, '中')] = _f(r['吸油·中(g/100g)'], 'oil')
        oil[(ck, '强')] = _f(r['吸油·强(g/100g)'], 'oil')
    wref = {}
    for r in _rows(wb['品类克重表'])[0]:
        wref[str(r['品类']).strip()] = (_f(r['标准份wref(g)'], 'wref'),
                                        _f(r['最小一勺(g)'], 'wmin'), _f(r['单菜上限(g)'], 'wmax'))

    # ---- 窗口观察表 ----
    win = {}
    for r in _rows(wb['窗口观察表'])[0]:
        key = (str(r['食堂/区域']).strip(), str(r['楼层']).strip(), str(r['窗口名称']).strip())
        soldout = r['一般售罄时点']; soldout = str(soldout).strip() if soldout else None
        win[key] = dict(canteen=key[0], floor=key[1], name=key[2],
                        fresh=str(r['出餐方式']).strip() == '现做',
                        make_min=int(_f(r['现做制作分钟'], '制作分钟', r['_r']) or 0),
                        soldout=soldout,
                        periods={p.strip() for p in str(r['供应时段']).split(',') if p.strip()},
                        photo=str(r['照片编号']).strip())
    assert len({w['photo'] for w in win.values()}) == len(win), '照片编号不唯一'

    # ---- 计价规则表 ----
    rho, tiers = {}, {}
    for r in _rows(wb['计价规则表'])[0]:
        key = (str(r['食堂/区域']).strip(), str(r['楼层']).strip(), str(r['窗口名称']).strip())
        kind = str(r['规则类型']).strip()
        price = _f(r['单价或档位价(元)'], '价格', r['_r'])
        if kind == '称重单价':
            unit = str(r['计价单位']).strip()
            assert unit in UNIT_G, f'称重行单位非法: {unit}'
            assert price and price > 0, '称重单价须>0'
            assert key not in rho, f'称重窗口重复登记: {key}'
            rho[key] = price / UNIT_G[unit]          # 元/g
        elif kind == '套餐档位':
            nm, nv = int(_f(r['荤数'], '荤数', r['_r'])), int(_f(r['素数'], '素数', r['_r']))
            mode = str(r['主食模式'] or '').strip(); rg = _f(r['主食克重(g)'], '主食克重', r['_r'])
            assert nm <= 2 and nv <= 2, f'档位基数>2 不支持: {key} {nm}荤{nv}素'
            assert mode in ENUM['主食模式'] and rg, f'档位四要素不全: {key} 行{r["_r"]}'
            assert price and price > 0
            tiers.setdefault(key, []).append(dict(n_meat=nm, n_veg=nv, price=price,
                                                   mode=mode, rice_g=rg))

    # ---- 拥挤观察表 → 等待中位数 ----
    bucket = {}
    for r in _rows(wb['拥挤观察表'])[0]:
        k = (str(r['食堂']).strip(), str(r['时段']).strip())
        v = _f(r['实测等待分钟'], '等待分钟', r['_r'])
        if v is not None: bucket.setdefault(k, []).append(v)
    wait = {k: statistics.median(v) for k, v in bucket.items()}
    slots = sorted({k[1] for k in wait})

    # ---- 步行矩阵 ----
    walk_rows, walk_hdr = _rows(wb['步行矩阵'])
    walk = {}
    for r in walk_rows:
        a = str(r['锚点']).strip()
        walk[a] = {h: _f(r[h], '步行') for h in walk_hdr if h != '锚点'}

    # ---- 菜品表 ----
    dishes = []
    sheet_dishes = [s for s in wb.sheetnames if s not in
                    ('数据字典','计价规则表','窗口观察表','标准菜名表','拥挤观察表','步行矩阵','油克系数表','品类克重表')]
    for sh in sheet_dishes:
        floor = '1层' if '一层' in sh else ('2层' if '二层' in sh else '—')
        canteen = sh.replace('一层', '').replace('二层', '')
        rows, hdr = _rows(wb[sh])
        if list(hdr.keys())[:len(DISH_HEAD)] != DISH_HEAD:
            issues.append(f'{sh} 表头与模板不一致')
        rows = [r for r in rows if r.get('菜名')]          # 跳过底部备注行
        for r in rows:
            name = str(r['菜名']).strip(); pricing = str(r['计价方式']).strip()
            assert pricing in ENUM['计价方式'], f'计价方式越界 {pricing}'
            assert name in std, f'菜名未命中标准表: {name}'
            key = (canteen, floor, str(r['窗口名称']).strip())
            assert key in win, f'窗口键未命中观察表: {key}'
            price = _f(r['价格(元)'], '价格', r['_r']); gram = _f(r['每份克重(g)'], '克重', r['_r'])
            if pricing in ('称重', '套餐'):
                assert price is None, f'{pricing}行价格必须为空: {name}'
            else:
                assert price and 0.1 <= price <= 200, f'价格非法: {name}'
            if pricing == '称重':
                assert gram is None, f'称重行克重必须为空: {name}'
            else:
                assert gram and 20 <= gram <= 2000, f'克重非法: {name}'
            if pricing == '称重': assert key in rho, f'称重窗口缺ρ: {key}'
            if pricing == '套餐': assert key in tiers, f'套餐窗口缺档位: {key}'
            if pricing == '套餐SKU':
                assert std[name]['conf'] == '公示级', f'SKU行须公示级: {name}'
            s = std[name]
            dishes.append(dict(
                rid=len(dishes), name=name, window=key, canteen=canteen, floor=floor,
                pricing=pricing, price=price, gram=gram,
                cat=str(r['品类']).strip(), sign=str(r['是否招牌']).strip() == '是',
                tier_slot=('荤' if str(r['品类']).strip() in ('荤菜','半荤') else '素') if pricing == '套餐' else None,
                slots=s['slots'], spice=s['spice'], taboo=s['taboo'], cook=s['cook'],
                kcal100=s['kcal100'], prot100=s['prot100'],
                oil100=None if s['conf'] == '公示级' else oil.get((s['cook'], s['absorb']), 20.0),
                conf=s['conf'], tag=s['tag'],
                rho=rho.get(key), tiers=tiers.get(key),
                fresh=win[key]['fresh'], make_min=win[key]['make_min'],
                periods=win[key]['periods'], soldout=win[key]['soldout'],
                wref=wref[str(r['品类']).strip()][0], wmax=wref[str(r['品类']).strip()][2]))

    # 熟重口径抽查：米饭必须 ≈116
    if '米饭' in std:
        assert 100 <= std['米饭']['kcal100'] <= 135, '米饭 kcal 异常，疑似生重口径(≈346)'

    return dict(std=std, dishes=dishes, windows=win, rho=rho, tiers=tiers, wait=wait,
                slots=slots, walk=walk, wref=wref, oil=oil, issues=issues,
                wb_sheets=wb.sheetnames)


def wait_at(bundle, canteen, asof_hhmm):
    """asof → 该食堂当前 30min 桶的实测中位；无实测（饭店/夜宵）→ 0/默认。"""
    if canteen == '校内饭店': return 0.0
    h, m = map(int, asof_hhmm.split(':')); t = h * 60 + m
    for s in bundle['slots']:
        a, b = s.split('-'); a1, a2 = map(int, a.split(':')); b1, b2 = map(int, b.split(':'))
        if a1 * 60 + a2 <= t < b1 * 60 + b2:
            return bundle['wait'].get((canteen, s))
    return None


def walk_to(bundle, anchor, canteen):
    """食堂级步行 = 该食堂各楼层列的最小值（楼层差由 INTRA_FLOOR 参数补）。"""
    row = bundle['walk'].get(anchor)
    if not row: return None
    pref = {'D区食堂': 'D区', 'F区食堂': 'F区', 'B区食堂': 'B区'}.get(canteen, canteen)
    cols = [v for k, v in row.items() if k.startswith(pref) and v is not None]
    return min(cols) if cols else row.get('校内饭店', 0)
