# -*- coding: utf-8 -*-
"""core.py —— 《模型与算法 v1.2》最小可运行实现：
硬过滤 → 三维打分(中心化) → 双通道 MILP(五档份量/档位z/两段式松弛) → 权重扫描
→ 签名去重/内容标签 → TOPSIS(γ=0 纯场景权重) → 排他+配额选Top3 → 松弛改标。
数值参数一律住 engine/params.yaml（带 calibrated/source），启动时 PyYAML 读入。"""
import os
import time
import math
import pulp as P
from concurrent.futures import ThreadPoolExecutor
from loader import walk_to, wait_at

# ---------------- 参数装载（params.yaml = 唯一数值存放处，SSOT §第四部分） ----------------
_PARAMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'params.yaml')


def _load_params(path=_PARAMS_PATH):
    """读 params.yaml → (PRM, SCEN, BASE_SWEEP)。逐项带 value/source/calibrated。"""
    try:
        import yaml
    except ImportError as e:
        raise ImportError('缺少 PyYAML（pip install pyyaml>=6），无法装载引擎参数 params.yaml') from e
    try:
        raw = yaml.safe_load(open(path, encoding='utf-8'))
    except FileNotFoundError as e:
        raise FileNotFoundError(f'引擎参数文件缺失: {path}') from e
    prm = {}
    for k, spec in raw['PRM'].items():
        v = spec['value']
        if isinstance(v, dict) and k not in ('PI', 'RBAR', 'RANDOM'):
            raise ValueError(f'params.yaml PRM.{k} 结构异常')
        prm[k] = v
    scen = {}
    for name, spec in raw['SCEN'].items():
        v = dict(spec['value'])
        v['E'] = tuple(v['E'])
        v['w'] = tuple(v['w'])
        v['ab'] = tuple(v['ab'])
        v['tags'] = set(v['tags'])
        scen[name] = v
    sweep = [tuple(w) for w in raw['BASE_SWEEP']['value']]
    return prm, scen, sweep


PRM, SCEN, BASE_SWEEP = _load_params()


def solve_m(mdl):
    """进程内原生 CBC。
    注意①：不传 threads——本机随 PuLP 捆绑的 CBC 在 -threads 参数上会死锁（已实测），
    CBC 默认即单线程，确定性不受影响（并行=多进程、每进程单线程 CBC，§3.2）。
    注意②：异常返回 'Not Solved' 走降级链，演示绝不弹崩栈。"""
    try:
        mdl['prob'].solve(P.PULP_CBC_CMD(msg=False, timeLimit=PRM['CBC_TIME_LIMIT'],
                                         gapRel=PRM['GAP']))
        return P.LpStatus[mdl['prob'].status]
    except P.PulpSolverError:
        return 'Not Solved'


def _t(hhmm):
    h, m = map(int, hhmm.split(':'))
    return h * 60 + m


def resolve(scenario, lazy):
    s = dict(SCEN[scenario])
    if lazy: s['Tmax'] = PRM['T_LAZY']
    return s


def _walk(bundle, anchor, canteen):
    v = walk_to(bundle, anchor, canteen)
    return v if v is not None else PRM['WALK_FALLBACK']


def _wait(bundle, canteen, asof):
    v = wait_at(bundle, canteen, asof)
    return v if v is not None else PRM['WAIT_DEFAULT']


def prefilter(bundle, req, scen):
    alive = []
    for d in bundle['dishes']:
        if req['period'] not in d['periods']: continue
        if d['spice'] > req['spice_max']: continue
        if d['taboo'] & req['taboo']: continue
        if d['soldout'] and _t(req['asof']) >= _t(d['soldout']): continue        # 整窗通常售罄（A15）
        if scen['ban_fried'] and d['cook'] == '油炸': continue
        if d['pricing'] in ('单品', '按份', '套餐SKU') and d['price'] > req['B']: continue
        if d['pricing'] == '称重' and d['rho'] * 0.5 * d['wref'] > req['B']: continue
        if scen['Tmax'] is not None:                                             # 懒人菜级耗时过滤
            if _walk(bundle, req['anchor'], d['canteen']) + _wait(bundle, d['canteen'], req['asof']) \
               + d['make_min'] > scen['Tmax']:
                continue
        alive.append(d)
    return alive


def prefilter_trace(bundle, req, scen):
    """只读计数（决策小票「做了什么筛选」用）：按产品口径逐步统计硬过滤后还剩几道菜。
    不改 prefilter 的行为与签名——各步谓词与 prefilter 逐条同义，只是换成讲故事的顺序
    逐步计数（各条件是「且」关系，顺序不影响最终集合）。最终数直接取 len(prefilter(...))；
    万一将来两边谓词漂移，差额如实记为「其他条件」一步，小票上的数永远对得上账。
    返回 dict(total=全部菜数, steps=[dict(key, label, left, cut, note)], alive=最终可选数)。"""
    req = dict(req, taboo=set(req.get('taboo') or ()))
    t_now = _t(req['asof'])
    lazy_on = scen['Tmax'] is not None
    rows = list(bundle['dishes'])
    steps = []

    def _step(key, label, keep, shown=True, note=''):
        nonlocal rows
        before = len(rows)
        rows = [d for d in rows if keep(d)]
        if shown or len(rows) != before:
            steps.append(dict(key=key, label=label, left=len(rows), cut=before - len(rows), note=note))

    in_period = [d for d in rows if req['period'] in d['periods']]
    n_sold = sum(1 for d in in_period if d['soldout'] and t_now >= _t(d['soldout']))
    _step('period', '该时段在售',
          lambda d: req['period'] in d['periods'] and not (d['soldout'] and t_now >= _t(d['soldout'])),
          note=(f'其中 {n_sold} 道已过一般售罄时点' if n_sold else ''))
    _step('taboo', '去忌口', lambda d: not (d['taboo'] & req['taboo']))
    _step('spice', '去超辣', lambda d: d['spice'] <= req['spice_max'], shown=req['spice_max'] < 2)
    _step('budget', '去超预算',
          lambda d: not ((d['pricing'] in ('单品', '按份', '套餐SKU') and d['price'] > req['B'])
                         or (d['pricing'] == '称重' and d['rho'] * 0.5 * d['wref'] > req['B'])))
    _step('fried', '减脂不吃油炸', lambda d: not (scen['ban_fried'] and d['cook'] == '油炸'),
          shown=bool(scen['ban_fried']))
    _step('lazy', '懒人限时',
          lambda d: not lazy_on or (_walk(bundle, req['anchor'], d['canteen'])
                                    + _wait(bundle, d['canteen'], req['asof']) + d['make_min'] <= scen['Tmax']),
          shown=lazy_on)
    alive = len(prefilter(bundle, req, scen))
    if alive != len(rows):
        steps.append(dict(key='other', label='其他条件', left=alive, cut=len(rows) - alive, note=''))
    return dict(total=len(bundle['dishes']), steps=steps, alive=alive)


def _mm(vals):
    lo, hi = min(vals), max(vals)
    if hi - lo < PRM['EPS_DIM']: return [0.5] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]


def score(alive, scen):
    a, b = scen['ab']
    prox = []
    for d in alive:
        if d['pricing'] == '称重': prox.append(d['rho'] * d['wref'])
        elif d['pricing'] == '套餐': prox.append(min(t['price'] / (t['n_meat'] + t['n_veg']) for t in d['tiers']))
        else: prox.append(d['price'])
    pd_ = _mm([d['prot100'] / d['kcal100'] for d in alive])
    ed = _mm([d['kcal100'] for d in alive])
    pr = _mm([-p for p in prox])
    oil_raw = {d['rid']: d['oil100'] for d in alive}                 # 公示级 oil100=None（官方全口径）
    nn_keys = [k for k, v in oil_raw.items() if v is not None]
    nn_mm = dict(zip(nn_keys, _mm([oil_raw[k] for k in nn_keys]))) if nn_keys else {}
    ol = {rid: nn_mm.get(rid, 0.5) for rid in oil_raw}
    dims = {}
    for i, d in enumerate(alive):
        n1 = PRM['SIGN_BONUS'] * d['sign'] + PRM['TAG_MATCH'] * (1.0 if d['tag'] in scen['tags'] else PRM['TAG_MISS'])
        n2 = a * pd_[i] + b * (1 - ed[i]) + (1 - a - b) * (1 - ol[d['rid']])
        dims[d['rid']] = (n1, n2, pr[i])
    w = list(scen['w'])
    for i in range(3):
        col = [dims[d['rid']][i] for d in alive]
        if max(col) - min(col) < PRM['EPS_DIM']: w[i] = 0.0                      # 零方差 → 权重让渡
    tot = sum(w) or 1
    w = [x / tot for x in w]
    s = {d['rid']: sum(w[i] * dims[d['rid']][i] for i in range(3)) for d in alive}
    sbar = sum(s.values()) / len(s)
    return dict(s=s, sbar=sbar, dims=dims, w=w)


def build(bundle, req, scen, alive, sc, wv, channel, phase, excl=(), ctx=None,
          force_weigh=False, ban_win_names=()):
    rows = [d for d in alive if not (channel == 'A' and d['pricing'] == '称重')]
    prob = P.LpProblem('meal', P.LpMaximize)
    M = PRM['PORTION_MULTS']
    x = {d['rid']: P.LpVariable(f'x{d["rid"]}', cat='Binary') for d in rows}
    b = {}
    for d in rows:
        if d['pricing'] == '称重':
            for mi in range(len(M)):
                b[(d['rid'], mi)] = P.LpVariable(f'b{d["rid"]}_{mi}', cat='Binary')

    wins = {}
    for d in rows: wins.setdefault(d['window'], []).append(d)
    y = {w: P.LpVariable(f'y{i}', cat='Binary') for i, w in enumerate(wins)}
    cants = sorted({w[0] for w in wins})
    zf = {f: P.LpVariable(f'f{i}', cat='Binary') for i, f in enumerate(cants)}

    z, tiers_ok = {}, {}
    for i, (w, dws) in enumerate(wins.items()):
        tlist = dws[0]['tiers']
        if not tlist: continue
        pool_m = [d for d in dws if d['pricing'] == '套餐' and d['tier_slot'] == '荤']
        pool_v = [d for d in dws if d['pricing'] == '套餐' and d['tier_slot'] == '素']
        ok = [ti for ti, t in enumerate(tlist)
              if len(pool_m) >= t['n_meat'] and len(pool_v) >= t['n_veg']
              and t['n_meat'] <= 2 and t['n_veg'] <= 2]                            # tier_precheck
        if ok: tiers_ok[w] = (ok, pool_m, pool_v)
        for ti in ok: z[(w, ti)] = P.LpVariable(f'z{i}_{ti}', cat='Binary')

    ub = 1.0 if phase == 2 else 0.0
    r_g = {g: P.LpVariable(f'rg{i}', 0, ub) for i, g in enumerate('主荤素')}
    rElo = P.LpVariable('rElo', 0, ub); rEhi = P.LpVariable('rEhi', 0, ub)
    rQ = P.LpVariable('rQ', 0, ub); rO = P.LpVariable('rO', 0, ub)
    rV = P.LpVariable('rV', 0, ub); rT = P.LpVariable('rT', 0, ub)

    E = P.lpSum(0); Q = P.lpSum(0); O = P.lpSum(0); PI = P.lpSum(0); G = P.lpSum(0)
    N = [P.lpSum(0) for _ in range(4)]; Wv = P.lpSum(0); TM = P.lpSum(0)
    for d in rows:
        if d['pricing'] == '称重':
            for mi, m in enumerate(M):
                g = d['wref'] * m
                E += (d['kcal100'] / 100 * g) * b[(d['rid'], mi)]
                Q += (d['prot100'] / 100 * g) * b[(d['rid'], mi)]
                O += (d['oil100'] / 100 * g) * b[(d['rid'], mi)]
                PI += (d['rho'] * g) * b[(d['rid'], mi)]
                G += g * b[(d['rid'], mi)]
                if d['slots'][2]: Wv += g * b[(d['rid'], mi)]
            prob += P.lpSum(b[(d['rid'], mi)] for mi in range(len(M))) == x[d['rid']]   # C13 多选一
        else:
            E += (d['gram'] / 100 * d['kcal100']) * x[d['rid']]
            Q += (d['gram'] / 100 * d['prot100']) * x[d['rid']]
            if d['oil100'] is not None:                       # 公示级官方全口径，不入油预算
                O += (d['gram'] / 100 * d['oil100']) * x[d['rid']]
            G += d['gram'] * x[d['rid']]
            PI += (d['price'] if d['pricing'] != '套餐' else 0.0) * x[d['rid']]
            if d['slots'][2]: Wv += d['gram'] * x[d['rid']]
        for gi in range(4): N[gi] += d['slots'][gi] * x[d['rid']]
        if d['fresh']: TM += d['make_min'] * x[d['rid']]

    for (w, ti), zv in z.items():                                                 # 档位价 + 米饭（含饭∪加价饭）
        t = tiers_of(rows, w)[ti]
        PI += (t['price'] + (PRM['RICE_UP'] if t['mode'] == '米饭+1元' else 0.0)) * zv
        if t['mode'] in ('含米饭', '米饭+1元'):
            E += (t['rice_g'] * PRM['RICE_KCAL100'] / 100) * zv
            Q += (t['rice_g'] * PRM['RICE_PROT100'] / 100) * zv
            N[0] += zv; G += t['rice_g'] * zv

    L, U = scen['E']
    for gi, g in enumerate('主荤素'):
        prob += N[gi] >= 1 - r_g[g]; prob += N[gi] <= 2
    prob += N[3] <= 1
    prob += E >= L * (1 - PRM['RBAR']['E_lo'] * rElo)
    prob += E <= U * (1 + PRM['RBAR']['E_hi'] * rEhi)
    prob += Q >= scen['Pmin'] * (1 - PRM['RBAR']['Q'] * rQ)
    prob += PI <= req['B']                                                         # C4 仅上界（无下限）
    prob += O <= scen['Omax'] + PRM['RBAR']['oil'] * rO
    prob += Wv >= scen['Vmin'] * (1 - PRM['RBAR']['veg'] * rV)
    prob += G <= PRM['TRAY_CAP']
    prob += P.lpSum(x[d['rid']] for d in rows if d['fresh']) <= 1                  # C7
    if scen['Tmax'] is not None and ctx:                                           # C8
        Tex = P.lpSum((ctx['walk'][f] + ctx['wait'][f]) * v for f, v in zf.items()) \
            + PRM['INTRA_FLOOR'] * P.lpSum(v for k, v in y.items() if k[1] == '2层') \
            + PRM['WAIT_EXTRA'] * (P.lpSum(y.values()) - 1) + TM
        prob += Tex <= scen['Tmax'] + PRM['RBAR']['T'] * rT
    for w, dws in wins.items(): prob += P.lpSum(x[d['rid']] for d in dws) <= len(dws) * y[w]
    byname = {}
    for d in rows: byname.setdefault(d['name'], []).append(d['rid'])
    for n, ids in byname.items():                              # 同名菜一餐至多一行（防"套餐鱼+称重鱼"）
        if len(ids) > 1: prob += P.lpSum(x[i] for i in ids) <= 1
    for w, yv in y.items(): prob += yv <= zf[w[0]]                                 # C10 一餐一食堂
    prob += P.lpSum(zf.values()) == 1
    prob += P.lpSum(y.values()) <= PRM['K_MAX']
    for w, (ok, pool_m, pool_v) in tiers_ok.items():                               # C12（∀w）
        tl = tiers_of(rows, w)
        prob += P.lpSum(z[(w, ti)] for ti in ok) <= y[w]
        prob += P.lpSum(x[d['rid']] for d in pool_m) == P.lpSum(tl[ti]['n_meat'] * z[(w, ti)] for ti in ok)
        prob += P.lpSum(x[d['rid']] for d in pool_v) == P.lpSum(tl[ti]['n_veg'] * z[(w, ti)] for ti in ok)
    if z: prob += P.lpSum(z.values()) <= 1
    for S in excl:                                                                 # C15 排他（floor 0）
        prob += P.lpSum(x[d['rid']] for d in rows if d['name'] in set(S)) <= max(len(S) - 2, 0)
    if force_weigh:                                                                # 定向补解：B通道至少一道称重
        weigh = [d for d in rows if d['pricing'] == '称重']
        if weigh: prob += P.lpSum(x[d['rid']] for d in weigh) >= 1
    for w in wins:                                                                 # 定向补解：去主导窗口
        if w[2] in ban_win_names: prob += y[w] == 0

    tie = P.lpSum(0)
    for d in rows:
        if d['pricing'] == '称重':
            tie += P.lpSum((1 - abs(m - 1)) * b[(d['rid'], mi)] for mi, m in enumerate(M))
    wq = P.lpSum(0)
    wvals = {d['rid']: sum(wv[i] * sc['dims'][d['rid']][i] for i in range(3)) for d in rows}
    if wvals:
        wbar = sum(wvals.values()) / len(wvals)                                  # 居中，保 CBC 数值稳定
        wq = P.lpSum((wvals[d['rid']] - wbar) * x[d['rid']] for d in rows)       # 扫描权重真正进目标
    prob += (wq
             + PRM['PORTION_EPS'] * tie
             - (PRM['PI']['slot'] * P.lpSum(r_g.values()) + PRM['PI']['E'] * (rElo + rEhi)
                + PRM['PI']['Q'] * rQ + PRM['PI']['oil'] * rO + PRM['PI']['veg'] * rV + PRM['PI']['T'] * rT))
    return dict(prob=prob, rows=rows, x=x, b=b, y=y, z=z, zf=zf, M=M, E=E, Q=Q, O=O, PI=PI,
                r=dict(**{f'槽_{g}': r_g[g] for g in '主荤素'}, 热量下=rElo, 热量上=rEhi,
                         蛋白=rQ, 油=rO, 素量=rV, 耗时=rT))


def tiers_of(rows, w):
    for d in rows:
        if d['window'] == w and d['tiers']: return d['tiers']
    return []


def _sel(mdl, var): return var.value() is not None and var.value() > 0.5


def extract(mdl, req, scen, ctx, channel):
    M = mdl['M']; items = []
    rowmap = {(d['name'], d['window'][2], d['pricing']): d for d in mdl['rows']}
    for d in mdl['rows']:
        if not _sel(mdl, mdl['x'][d['rid']]): continue
        if d['pricing'] == '称重':
            m = sum(m * mdl['b'][(d['rid'], mi)].value() for mi, m in enumerate(M))
            g = round(d['wref'] * m)
            items.append(dict(name=d['name'], win=d['window'][2], pricing='称重', grams=g,
                              price=round(d['rho'] * g, 2), cat=d['cat'], tier_slot=None))
        else:
            items.append(dict(name=d['name'], win=d['window'][2], pricing=d['pricing'],
                              grams=d['gram'], price=d['price'], cat=d['cat'], tier_slot=d['tier_slot']))
    tier = None
    for (w, ti), zv in mdl['z'].items():
        if _sel(mdl, zv):
            t = tiers_of(mdl['rows'], w)[ti]
            tier = dict(win=w[2], n_meat=t['n_meat'], n_veg=t['n_veg'], price=t['price'],
                        mode=t['mode'], rice_g=t['rice_g'])
    # —— 报告口径单一真相：总量从 items 重算 ——
    E = Q = O = PI = G = 0.0; names = set()
    for it in items:
        d = rowmap[(it['name'], it['win'], it['pricing'])]
        E += it['grams'] / 100 * d['kcal100']; Q += it['grams'] / 100 * d['prot100']
        if d['oil100'] is not None: O += it['grams'] / 100 * d['oil100']
        G += it['grams']; names.add(it['name'])
    if tier:
        for it in items:
            if it['pricing'] == '套餐': it['price'] = 0.0                            # 池行价格=档位价
        up = PRM['RICE_UP'] if tier['mode'] == '米饭+1元' else 0.0
        PI = sum(it['price'] or 0 for it in items) + tier['price'] + up
        if tier['mode'] in ('含米饭', '米饭+1元'):
            E += tier['rice_g'] * PRM['RICE_KCAL100'] / 100
            Q += tier['rice_g'] * PRM['RICE_PROT100'] / 100
            G += tier['rice_g']; names.add('米饭(套餐)')
    else:
        PI = sum(it['price'] or 0 for it in items)
    dims = [0.0, 0.0, 0.0]
    for it in items:
        d = rowmap[(it['name'], it['win'], it['pricing'])]
        dd = mdl['sc_dims'][d['rid']]
        dims = [dims[i] + dd[i] for i in range(3)]
    if items: dims = [round(v / len(items), 3) for v in dims]
    relax = {k: round(v.value() or 0, 3) for k, v in mdl['r'].items() if (v.value() or 0) > 1e-6}
    max_r = max(relax.values()) if relax else 0.0
    status = '建议' if max_r > PRM['RELAX_HARD'] else ('放宽版' if max_r > PRM['RELAX_SOFT'] else '推荐')
    cants = {rowmap[(it['name'], it['win'], it['pricing'])]['canteen'] for it in items}
    label = '自选' if any(it['pricing'] == '称重' for it in items) else '普通'
    sig = (tuple(sorted(names)), tuple((it['name'], it['grams']) for it in items if it['pricing'] == '称重'),
           tier['price'] if tier else None)
    return dict(items=items, tier=tier, names=names, E=round(E, 1), Q=round(Q, 1), O=round(O, 2),
                PI=round(PI, 2), G=round(G), relax=relax, dims=dims, sig=sig, label=label,
                status=status, wins=sorted({it['win'] for it in items}), cant=sorted(cants),
                channel=channel, phi=round(P.value(mdl['prob'].objective), 4))


def topsis(plans, w_fin, B):
    if not plans: return plans
    cols = [[p['dims'][0] for p in plans], [p['dims'][1] for p in plans],
            [1 - p['PI'] / B for p in plans]]
    norm = []
    for c in cols:
        l2 = math.sqrt(sum(v * v for v in c)) or 1e-9
        norm.append([v / l2 for v in c])
    ideal = [max(norm[i]) for i in range(3)]; anti = [min(norm[i]) for i in range(3)]
    for idx, p in enumerate(plans):
        dp = math.sqrt(sum(w_fin[i] * (norm[i][idx] - ideal[i]) ** 2 for i in range(3)))
        dm = math.sqrt(sum(w_fin[i] * (norm[i][idx] - anti[i]) ** 2 for i in range(3)))
        p['C'] = round(dm / (dp + dm) if (dp + dm) > 1e-9 else 0.5, 4)
    plans.sort(key=lambda p: (-p['C'], str(p['sig'])))
    return plans


def recommend(bundle, req, avoid=()):
    """avoid: 菜名集合的列表（如 [{'清蒸南瓜','酸菜鱼'}]）——'换着吃'降权：
    以 C15 排他形式注入（至少换2道），仅正常模式由 UI 调用，默认空不改变行为。

    提速工程（结果与串行版逐位一致，R1–R4 签名即证）：
    ① 相位探针/权重扫描/补解轮中互相独立的 CBC 调用用线程池并发——CBC 以子进程运行，
       线程只在等子进程，每个 CBC 进程依旧单线程（§3.2"并行=多进程、每进程单线程CBC"）；
       产物按键（通道,向量序）回插，合并顺序与串行版完全一致，确定性不变。
    ② A 通道（删称重）仅当存活池含称重菜时才跑——无称重菜时 A/B 模型逐位相同，跑 B 即可。
    ③ 相位1且探针最优时，复用探针解作为扫描向量[6]（同一模型同一目标，串行版会解出同解）。"""
    base_excl = [set(s) for s in avoid]
    t0 = time.time()
    scen = resolve(req['scenario'], req.get('lazy', False))
    alive = prefilter(bundle, req, scen)
    if not alive: return dict(top3=[], pool=[], error='过滤后无菜', alive=0, elapsed=0)
    cants = {d['canteen'] for d in alive}
    ctx = dict(walk={f: _walk(bundle, req['anchor'], f) for f in cants},
               wait={f: _wait(bundle, f, req['asof']) for f in cants})
    sc = score(alive, scen)
    dom = (round(max(PRM['SWEEP_FLOOR'], scen['w'][0] - PRM['DOM_SHIFT']), 3),
           round(min(PRM['DOM_CAP'], scen['w'][1] + PRM['DOM_BOOST']), 3),
           round(max(PRM['SWEEP_FLOOR'], scen['w'][2] - PRM['DOM_SHIFT']), 3))
    sweep = BASE_SWEEP + [dom]
    i_probe = len(BASE_SWEEP) - 1                     # 探针向量=基础扫描表末位（出厂配置=均匀向量）
    channels = ('B', 'A') if any(d['pricing'] == '称重' for d in alive) else ('B',)
    workers = max(1, int(PRM['SWEEP_WORKERS']))

    def _run(args):
        """独立子任务：建模型+求解+抽取（线程内自建自解，无共享可变状态）。"""
        key, ch, wv, phase, excl, kw = args
        mdl = build(bundle, req, scen, alive, sc, wv, ch, phase, excl=excl, ctx=ctx, **kw)
        st = solve_m(mdl)
        if st not in ('Optimal', 'Integer Feasible'):
            return key, None
        mdl['sc_dims'] = sc['dims']
        return key, extract(mdl, req, scen, ctx, ch)

    def _run_parallel(tasks):
        """并发跑独立子任务；结果按键排序回插 → 与串行顺序完全一致（确定性）。"""
        if len(tasks) <= 1:
            return [_run(t) for t in tasks]
        try:
            with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as ex:
                return sorted(ex.map(_run, tasks), key=lambda r: r[0])
        except Exception:                                   # 线程池异常兜底：退回串行
            return [_run(t) for t in tasks]

    # —— 两段判定（每通道一次，§3.1）；探针模型=基础扫描表末位向量，解可复用 ——
    plans, phase_info = [], {}
    probe_plan = {}
    tasks = [(ch, ch, sweep[i_probe], 1, base_excl, {}) for ch in channels]
    for ch, p in _run_parallel(tasks):
        phase_info[ch] = 1 if p is not None else 2          # 探针最优⇔r≡0 可行 ⇒ 相位1
        probe_plan[ch] = p
    # —— 权重扫描（两通道×全部向量并发）；产物按（通道,向量序）原顺序回插：
    # 相位1的探针向量与探针是同一模型同一目标，直接复用探针解（③），解值与串行重解一致。 ——
    tasks = [((ci * 100 + wi), ch, wv, phase_info[ch], base_excl, {})
             for ci, ch in enumerate(channels) for wi, wv in enumerate(sweep)]
    results = dict(_run_parallel(tasks))
    for ci, ch in enumerate(channels):
        for wi in range(len(sweep)):
            p = probe_plan[ch] if (phase_info[ch] == 1 and wi == i_probe) \
                else results.get(ci * 100 + wi)
            if p is not None:
                plans.append(p)
    uniq = {}
    for p in plans:
        if not p['items']: continue                                              # 空选菜集不是方案
        uniq.setdefault(p['sig'], p)
    # 定向补解①：B通道从未选出称重菜时，强制一次自选方案（双通道设计的本意）
    def _solve_extra(**kw):
        mdl = build(bundle, req, scen, alive, sc, dom, 'B', phase_info['B'],
                    excl=base_excl + list(kw.pop('excl', [])), ctx=ctx, **kw)
        if solve_m(mdl) in ('Optimal', 'Integer Feasible'):
            mdl['sc_dims'] = sc['dims']
            plans.append(extract(mdl, req, scen, ctx, 'B'))

    def _reuniq():
        u = {}
        for p in plans:
            if not p['items']: continue
            u.setdefault(p['sig'], p)
        return u

    if any(d['pricing'] == '称重' for d in alive) and not any(p['label'] == '自选' for p in uniq.values()):
        _solve_extra(force_weigh=True)
        uniq = _reuniq()
    # 定向补解②：候选被单一窗口垄断时，去主导窗口求解一次，逼出其他窗口的整餐
    if uniq:
        from collections import Counter
        cnt = Counter(w for p in uniq.values() for w in p['wins'])
        w_dom = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        if cnt[w_dom] == len(uniq):
            _solve_extra(ban_win_names={w_dom})
            uniq = _reuniq()
    # C15 迭代排他补解：权重扫描易收敛到同一签名（同质主导）。逐轮把【全部已有方案】
    # 的名字集作为排他约束（每条=至少换2道）重解——只排单个种子会在共享3菜的方案间
    # 互收敛而死锁。前沿富化到 ≥ENRICH_TARGET 个唯一方案，Top3 配额与 TOPSIS 才有意义。
    rounds = 0
    while len(uniq) < PRM['ENRICH_TARGET'] and rounds < PRM['ENRICH_ROUNDS']:
        rounds += 1
        before = len(uniq)
        excl_all = [set(p['names']) for p in sorted(uniq.values(), key=lambda p: (-p['phi'], str(p['sig'])))]
        tasks = [((ci, ), ch, dom, phase_info[ch], base_excl + excl_all, {})
                 for ci, ch in enumerate(channels)]
        for _, p in _run_parallel(tasks):
            if p is not None:
                plans.append(p)
        uniq = {}
        for p in plans:
            if not p['items']: continue
            uniq.setdefault(p['sig'], p)
        if len(uniq) == before:
            break
    merged = topsis(list(uniq.values()), sc['w'], req['B'])
    sel = []
    for swap in range(PRM['DIVERSITY_SWAP'], -1, -1):
        for p in merged:
            if len(sel) >= 3: break
            if any(q['sig'] == p['sig'] for q in sel): continue
            if sum(q['label'] == p['label'] for q in sel) >= PRM['QUOTA_LABEL']: continue   # 内容通道配额
            if sum(1 for q in sel if set(q['wins']) & set(p['wins'])) >= PRM['QUOTA_WIN']: continue  # 同窗口配额
            if all(len(p['names'] & q['names']) <= max(min(len(p['names']), len(q['names'])) - swap, 0)
                   for q in sel):
                sel.append(p)
        if len(sel) >= 3: break
    sel.sort(key=lambda p: -p['C'])
    if len(sel) < 3:                                   # 严格配额凑不满 → 降级补位（菜品不重复即可）
        for p in merged:
            if len(sel) >= 3: break
            if any(q['sig'] == p['sig'] for q in sel): continue
            if any(q['names'] == p['names'] for q in sel): continue
            p = dict(p)
            p['degraded'] = True                       # 标记：为凑满三套放宽了多样性配额
            sel.append(p)
        sel.sort(key=lambda p: -p['C'])
    sel_sigs = {p['sig'] for p in sel}
    pool = [p for p in merged if p['sig'] not in sel_sigs]
    _decorate(sel + pool, sc)
    return dict(top3=sel, pool=pool, alive=len(alive), phase=phase_info, sweep=len(sweep),
                elapsed=round(time.time() - t0, 2), scen=scen, w_used=sc['w'])


def _decorate(plans, sc):
    """给方案补三维绝对条形（0-100，按全体存活候选的维度范围归一化）与一句话标签。
    三维：口味（招牌/标签匹配）、营养（蛋白/热量/油）、性价比（越低越省）。
    条形跨请求口径一致（同一菜池归一化），随机配/换一批的方案也能算、可横向对比。"""
    if not plans:
        return
    cols = list(sc['dims'].values())
    if not cols:
        return
    lo = [min(c[i] for c in cols) for i in range(3)]
    hi = [max(c[i] for c in cols) for i in range(3)]
    labels = ['口味招牌', '营养能打', '性价比高']
    for p in plans:
        dims = p.get('dims') or lo
        bars = []
        for i in range(3):
            span = hi[i] - lo[i]
            v = dims[i]
            bars.append(max(0, min(100, round(100 * (v - lo[i]) / span))) if span > 1e-9 else 50)
        p['bars'] = bars
        p['tag'] = labels[bars.index(max(bars))]


def random_recommend(bundle, req, n=3, seed=None, exclude=()):
    """随机配：随机化偏好权重（口味/营养/价格主轴）多次求解，从解空间抽样 n 套方案。
    硬约束（预算/忌口/营养带/售罄/耗时）与主流程完全一致，只随机化目标权重。
    exclude：上一轮展示过的方案（菜名集合列表）——重叠判定拒收：与任一 exclude 方案
    共享菜品数 ≥ ceil(本方案菜品数/2) 即视为"同一类餐"跳过，保证每次点都换新。
    总时限熔断（RANDOM_TIME_BUDGET≈6s）：到点即停返回已抽到的方案，绝不让演示干等；
    同 seed 时抽样序列确定（熔断仅在机器过慢时截断，正常不触发）。"""
    import random as _random
    rng = _random.Random(seed)
    t0 = time.time()
    deadline = t0 + PRM['RANDOM_TIME_BUDGET']
    RC = PRM['RANDOM']
    scen = resolve(req['scenario'], req.get('lazy', False))
    alive = prefilter(bundle, req, scen)
    if not alive:
        return dict(top3=[], pool=[], error='过滤后无菜', alive=0, elapsed=0, scen=scen)
    cants = {d['canteen'] for d in alive}
    ctx = dict(walk={f: _walk(bundle, req['anchor'], f) for f in cants},
               wait={f: _wait(bundle, f, req['asof']) for f in cants})
    sc = score(alive, scen)
    # 相位探测：严格可解才用「不放宽」阶段，否则直接走放宽阶梯（与主流程同规则）
    probe = build(bundle, req, scen, alive, sc, tuple(scen['w']), 'B', 1, ctx=ctx)
    phase = 1 if solve_m(probe) == 'Optimal' else 2
    plans, seen = [], set()
    excl_names = [set(s) for s in exclude]

    def _done():
        _decorate(plans, sc)
        return dict(top3=plans[:n], pool=[], alive=len(alive),
                    elapsed=round(time.time() - t0, 2), scen=scen)

    for rnd in range(min(n * RC['ROUNDS_PER_N'], RC['ROUNDS_CAP'])):
        if time.time() > deadline:
            break                                             # 总时限熔断：到点即停
        # 主轴定向采样 + 随机子集：极点权重决定"偏好方向"，随机剔除 15–40% 的菜
        # 决定"今天先不看这些"——每次子问题不同，才能从大解空间里真正抽到不同的餐。
        main = rnd if rnd < 3 else rng.randint(0, 2)
        w = [rng.uniform(*RC['SIDE_W']) for _ in range(3)]
        w[main] = rng.uniform(*RC['MAIN_W'])
        tot = sum(w) or 1.0
        w = tuple(round(v / tot, 3) for v in w)
        cut = rng.uniform(*RC['CUT'])
        sub = [d for d in alive if rng.random() > cut]
        ch = 'B' if rnd % RC['A_EVERY'] else 'A'            # 每 A_EVERY 次尝试给一席自选通道
        mdl = build(bundle, req, scen, sub, sc, w, ch, phase, ctx=ctx)
        if solve_m(mdl) not in ('Optimal', 'Integer Feasible'):
            continue
        mdl['sc_dims'] = sc['dims']
        p = extract(mdl, req, scen, ctx, ch)
        if not p['items'] or p['sig'] in seen:
            continue
        half = math.ceil(len(p['names']) / 2)                 # 重叠判定：共享 ≥ 半数菜品即拒收
        if any(len(p['names'] & s) >= half for s in excl_names):
            continue
        seen.add(p['sig']); plans.append(p)
        if len(plans) >= n:
            break
    return _done()
