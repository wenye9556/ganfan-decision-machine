# -*- coding: utf-8 -*-
"""gap_scan.py —— 食堂视角 · 菜单缺口雷达（离线扫描；App「🏫 食堂视角」页只读结果，不实时扫）

条件网格：场景 4 × 预算 6 档 × 时段 4 × 常见忌口 5 = 480 种点餐条件。
固定：位置=图书馆、辣度=能吃辣（辣度不成为缺口原因）、懒人=关；钟点取 App 听到
「早饭/午饭/晚饭/夜宵」时默认的钟点（nl_agent.PERIODS，与配饭页同一口径）。

① 快筛：逐条件跑 core.prefilter（与配饭页同一套硬过滤，不解整餐模型），记可选菜数与在售窗口；
   可选 0 道 / 不足 5 道的条件直接标缺口。
② 实算：只挑可疑条件各跑一次 core.recommend（≤ MAX_RUNS 次），判「配不满 3 套达标」——
   达标＝方案状态「推荐」。可选名单逐道相同（场景/预算/时段也相同）的条件结果必然一致，直接复用。
③ 归因：只放开一个条件（时段 / 售罄 / 预算 / 忌口）能多救回最多菜的，记为主因。
④ 冷门菜＝在 480 种条件里进得了可选名单的次数最少（以出现次数作代理）；
   主力窗口＝在最多种条件下都有菜可选（可配次数）。
输出 data/gap_report.json（页面文案在此生成，产品语言、零算法词）。
用法: python engine/gap_scan.py
"""
import itertools
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import loader      # noqa: E402
import core        # noqa: E402
from nl_agent import PERIODS   # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, '..'))
MASTER = os.path.join(ROOT, '干饭决策机_数据采集_主表.xlsx')
OUT = os.path.join(ROOT, 'data', 'gap_report.json')

SCENARIOS = ['均衡', '减脂', '增肌', '省钱']
BUDGETS = [8, 10, 12, 15, 18, 25]
PERIOD_KEYS = ['早', '午', '晚', '夜宵']
ASOF = {p: a for p, _, a in PERIODS}                 # 早 08:00 / 午 12:30 / 晚 18:30 / 夜宵 21:30
TABOOS = [(), ('猪',), ('香菜',), ('海鲜',), ('奶',)]
FIXED = dict(anchor='图书馆', spice_max=2, lazy=False)
THIN = 5                 # 可选菜不足 5 道：直接标缺口
MAX_RUNS = 60            # 实算次数上限（总时长远低于 10 分钟）
THIN_WINDOWS = 2         # 在售窗口 ≤2 个的时段算「供给薄」，实算优先查
REASONS = ['时段', '售罄', '预算', '忌口']           # 主因并列时按此顺序取
KIND_RANK = {'none': 0, 'thin': 1, 'short': 2, 'weak': 3, 'partial': 4}
GENEROUS = {s: i for i, s in enumerate(['均衡', '省钱', '减脂', '增肌'])}   # 代表条件挑选次序
PERIOD_CN = {'早': '早饭', '午': '午饭', '晚': '晚饭', '夜宵': '夜宵'}
PERIOD_AT = {'早': '早上', '午': '中午', '晚': '晚上', '夜宵': '夜宵'}
NOON_END = '14:00'       # 售罄时点早于此＝记的是午市
TOP_N = 5


def make_req(s, B, p, tb):
    return dict(scenario=s, B=B, period=p, asof=ASOF[p], taboo=set(tb), **FIXED)


def alive_of(bundle, req):
    return core.prefilter(bundle, req, core.resolve(req['scenario'], req['lazy']))


def win_label(w):
    return w[2]


def cond_label(c):
    s = f"{PERIOD_CN[c['period']]}·{c['B']}元内·{c['scenario']}"
    return s + ('·忌' + '/'.join(c['taboo']) if c['taboo'] else '')


def result_phrase(c):
    if c['alive'] == 0 or c.get('plans') == 0:
        return '0 套'
    if c.get('plans') is None:
        return f"只剩 {c['alive']} 道可选"
    if c['plans'] < 3:
        return f"只配得出 {c['plans']} 套"
    if c['good'] == 0:
        return '3 套都不达标'
    return f"3 套里只有 {c['good']} 套达标"


def unit_price(d):
    """单道最低花费（与 prefilter 预算口径一致）；套餐池菜价格在档位上，返回 None。"""
    if d['pricing'] in ('单品', '按份', '套餐SKU'):
        return d['price']
    if d['pricing'] == '称重':
        return round(d['rho'] * 0.5 * d['wref'], 2)
    return None


def main():
    t_all = time.time()
    b = loader.load(MASTER)
    dishes = b['dishes']
    by_rid = {d['rid']: d for d in dishes}

    # 「时段放开」反事实用：假设所有窗口这个时段都开（售罄时点照旧）
    open_bundle = {p: dict(b, dishes=[dict(d, periods=set(d['periods']) | {p}) for d in dishes])
                   for p in PERIOD_KEYS}

    # 各时段供给：供应该时段的窗口 / 该钟点仍在售的窗口（不限预算、不忌口）
    supply = {}
    for p in PERIOD_KEYS:
        t = core._t(ASOF[p])
        serve = sorted({d['window'] for d in dishes if p in d['periods']})
        onsale = sorted({d['window'] for d in dishes if p in d['periods']
                         and not (d['soldout'] and t >= core._t(d['soldout']))})
        sold = [w for w in serve if w not in onsale]
        noon = all(b['windows'][w]['soldout'] and b['windows'][w]['soldout'] < NOON_END for w in sold)
        supply[p] = dict(serve=serve, onsale=onsale, sold=sold, sold_noon=bool(sold) and noon)

    # ---------------- ① 快筛：480 种条件逐个过硬过滤 ----------------
    t0 = time.time()
    combos, pools = [], []
    freq, win_hit, win_dish = Counter(), Counter(), Counter()
    win_periods = defaultdict(set)
    for s, B, p, tb in itertools.product(SCENARIOS, BUDGETS, PERIOD_KEYS, TABOOS):
        req = make_req(s, B, p, tb)
        alive = alive_of(b, req)
        rids = frozenset(d['rid'] for d in alive)
        wins = {d['window'] for d in alive}
        for d in alive:
            freq[d['rid']] += 1
            win_dish[d['window']] += 1
        for w in wins:
            win_hit[w] += 1
            win_periods[w].add(p)
        # 归因：只放开一个条件，能多救回几道菜
        gain = {
            '时段': len(alive_of(open_bundle[p], req)) - len(alive),
            '售罄': len(alive_of(b, dict(req, asof='00:00'))) - len(alive),   # 不看懒人时，钟点只影响售罄
            '预算': len(alive_of(b, dict(req, B=10 ** 6))) - len(alive),
            '忌口': len(alive_of(b, dict(req, taboo=set()))) - len(alive),
        }
        combos.append(dict(scenario=s, B=B, period=p, asof=ASOF[p], taboo=list(tb),
                           alive=len(alive), windows=len(wins), gain=gain))
        pools.append((s, B, p, rids))
    t_pre = time.time() - t0

    # ---------------- ② 实算：挑可疑条件跑一次整餐搭配 ----------------
    thin_p = [p for p in PERIOD_KEYS if 0 < len(supply[p]['onsale']) <= THIN_WINDOWS]
    rich_p = [p for p in PERIOD_KEYS if len(supply[p]['onsale']) > THIN_WINDOWS]
    order = []
    for p in thin_p:                      # 供给薄的时段：四场景 × 六档预算 × 不忌口（预算阶梯全覆盖）
        order += [(s, B, p, ()) for s in SCENARIOS for B in BUDGETS]
    for p in rich_p:                      # 供给足的时段：最低预算档 × 四场景 × {不忌口, 忌猪}
        order += [(s, BUDGETS[0], p, tb) for tb in ((), ('猪',)) for s in SCENARIOS]
    for p in thin_p:                      # 供给薄的时段：最高预算档 × 均衡 × {忌猪, 忌奶}
        order += [('均衡', BUDGETS[-1], p, tb) for tb in (('猪',), ('奶',))]
    for p in thin_p:                      # 后备（前面有复用省下名额时才用到）
        order += [(s, BUDGETS[-1], p, tb) for s in SCENARIOS for tb in (('猪',), ('海鲜',), ('奶',))]
    index = {(c['scenario'], c['B'], c['period'], tuple(c['taboo'])): i for i, c in enumerate(combos)}
    results, runs = {}, []
    t1 = time.time()
    for key in order:
        if len(runs) >= MAX_RUNS:
            break
        i = index[key]
        if combos[i]['alive'] == 0 or pools[i] in results:
            continue
        req = make_req(*key)
        tr = time.time()
        res = core.recommend(b, req)
        st = [x['status'] for x in res['top3']]
        results[pools[i]] = dict(plans=len(st), good=st.count('推荐'), status=st,
                                 price=[x['PI'] for x in res['top3']], src=i)
        runs.append(dict(cond=cond_label(combos[i]), plans=len(st), good=st.count('推荐'),
                         sec=round(time.time() - tr, 2)))
        print(f"[{len(runs):2d}/{MAX_RUNS}] {cond_label(combos[i])} 可选 {combos[i]['alive']} 道 → "
              f"{len(st)} 套（达标 {st.count('推荐')}）{time.time() - tr:.2f}s", flush=True)
    t_chk = time.time() - t1
    for i, c in enumerate(combos):       # 可选名单逐道相同 → 结果完全一致，直接复用
        r = results.get(pools[i])
        if r:
            c.update(plans=r['plans'], good=r['good'], status=r['status'], price=r['price'],
                     checked='实算' if r['src'] == i else '同名单复用')

    # ---------------- ③ 缺口判定 + 归因 ----------------
    for c in combos:
        if c['alive'] == 0 or c.get('plans') == 0:
            kind = 'none'
        elif c.get('plans') is not None:
            kind = ('short' if c['plans'] < 3 else 'weak' if c['good'] == 0
                    else 'partial' if c['good'] < 3 else None)
        else:
            kind = 'thin' if c['alive'] < THIN else None
        c['gap'] = kind
        if kind:
            g = c['gain']
            top = max(REASONS, key=lambda r: (g[r], -REASONS.index(r)))
            c['reason'] = top if g[top] > 0 else '场景'

    def why(c):
        """（括号里的）一句话原因 + 下方小字细节。"""
        p, sp = c['period'], supply[c['period']]
        names = '、'.join(win_label(w) for w in sp['serve'])
        r = c['reason']
        if r == '时段':
            return (f"{PERIOD_AT[p]}只有 {len(sp['serve'])} 个窗口开",
                    f"{PERIOD_CN[p]}只有{names}在卖")
        if r == '售罄':
            if not sp['onsale']:
                return ('这个时段没菜在卖', f"{PERIOD_CN[p]}只有{names}卖，到 {c['asof']} 都已收")
            left = '、'.join(win_label(w) for w in sp['onsale'])
            basis = '按午市售罄时点算' if sp['sold_noon'] else '过了一般售罄时点'
            return (f"{c['asof']} 只剩 {len(sp['onsale'])} 个窗口在卖",
                    f"只剩{left}；另 {len(sp['sold'])} 个窗口{basis}已收")
        if r == '预算':
            return (f"{c['B']} 元内只剩 {c['alive']} 道买得起", f"放开预算能多出 {c['gain']['预算']} 道")
        if r == '忌口':
            return (f"忌{'/'.join(c['taboo'])}一下少了 {c['gain']['忌口']} 道", '')
        return ('营养标准凑不齐', '')

    groups = defaultdict(list)
    for i, c in enumerate(combos):
        if c['gap']:
            groups[(c['period'], c['reason'], c['gap'])].append(i)
    gap_groups = []
    for (p, r, k), idx in groups.items():
        rep = min(idx, key=lambda i: (-combos[i]['B'], len(combos[i]['taboo']),
                                      GENEROUS[combos[i]['scenario']], combos[i]['taboo']))
        c = combos[rep]
        short, detail = why(c)
        gap_groups.append(dict(
            reason=r, kind=k, period=p, count=len(idx), cond=cond_label(c), result=result_phrase(c),
            why=short, detail=detail, alive=c['alive'], plans=c.get('plans'), good=c.get('good'),
            label=f"{cond_label(c)} → {result_phrase(c)}（{short}）"))
    gap_groups.sort(key=lambda g: (KIND_RANK[g['kind']], -g['count'], PERIOD_KEYS.index(g['period'])))

    # ---------------- ④ 冷门菜 / 主力窗口 ----------------
    n = len(combos)
    grid_taboo = [t for tb in TABOOS for t in tb]          # 猪 / 香菜 / 海鲜 / 奶

    def cold_why(d):
        parts = []
        up = unit_price(d)
        if up is not None:
            reach = [B for B in BUDGETS if up <= B]
            if not reach:
                parts.append(f'单价 ¥{up:g}，超过 {BUDGETS[-1]} 元档')
            elif reach[0] > BUDGETS[0]:
                parts.append(f'¥{up:g}，{reach[0]} 元档起才够得着')
        hit = [t for t in grid_taboo if t in d['taboo']]
        if hit:
            parts.append('含' + '/'.join(hit))
        if d['cook'] == '油炸':
            parts.append('油炸（减脂不选）')
        return '、'.join(parts) or '各条件下都排在后面'

    cold = sorted(dishes, key=lambda d: (freq[d['rid']], -(unit_price(d) or 0), d['window'][2], d['name']))
    cold_dishes = [dict(name=d['name'], window=d['window'][2], canteen=d['canteen'], price=unit_price(d),
                        hits=freq[d['rid']], of=n, why=cold_why(d)) for d in cold[:40]]
    cold_top, seen_w = [], set()
    for d in cold:                         # 页面 Top：每个窗口只取最冷的一道，避免一家刷屏
        if d['window'] in seen_w:
            continue
        seen_w.add(d['window'])
        cold_top.append(dict(name=d['name'], window=d['window'][2], canteen=d['canteen'],
                             price=unit_price(d), hits=freq[d['rid']], of=n, why=cold_why(d)))
        if len(cold_top) >= TOP_N:
            break

    wins_all = sorted(b['windows'], key=lambda w: (-win_hit[w], -win_dish[w], w[2]))
    windows = [dict(window=w[2], canteen=w[0], floor=w[1], combos=win_hit[w], of=n,
                    avg_dishes=round(win_dish[w] / win_hit[w], 1) if win_hit[w] else 0,
                    periods=[PERIOD_CN[p] for p in PERIOD_KEYS if p in win_periods[w]])
               for w in wins_all]
    main_top = windows[:TOP_N]

    # ---------------- 汇总 + 落盘 ----------------
    gaps = [c for c in combos if c['gap']]
    summary = dict(
        n_combos=n, n_zero=sum(1 for c in combos if c['alive'] == 0),
        n_thin=sum(1 for c in combos if 0 < c['alive'] < THIN),
        n_runs=len(runs), n_checked=sum(1 for c in combos if c.get('plans') is not None),
        n_gap=len(gaps), by_kind=dict(Counter(c['gap'] for c in gaps)),
        by_reason={r: sum(1 for c in gaps if c['reason'] == r) for r in REASONS + ['场景']},
        by_period={PERIOD_CN[p]: sum(1 for c in gaps if c['period'] == p) for p in PERIOD_KEYS},
        supply={PERIOD_CN[p]: dict(asof=ASOF[p], serve=len(supply[p]['serve']),
                                   onsale=len(supply[p]['onsale'])) for p in PERIOD_KEYS})
    elapsed = dict(prefilter_s=round(t_pre, 2), recommend_s=round(t_chk, 1), total_s=round(time.time() - t_all, 1))
    report = dict(
        version=1, generated_at=datetime.now().isoformat(timespec='seconds'), elapsed=elapsed,
        grid=dict(scenarios=SCENARIOS, budgets=BUDGETS,
                  periods=[dict(period=p, label=PERIOD_CN[p], asof=ASOF[p]) for p in PERIOD_KEYS],
                  taboos=[list(t) for t in TABOOS], fixed=FIXED, n_combos=n),
        method=dict(
            prefilter='480 种条件逐个过 core.prefilter（与配饭页同一套硬过滤，不解整餐模型）；可选 0 道或 <5 道直接标缺口',
            recommend=(f'可疑条件各跑一次 core.recommend，共 {len(runs)} 次（上限 {MAX_RUNS}）：供给薄时段（在售窗口≤{THIN_WINDOWS}）'
                       '四场景×六档预算×不忌口；供给足时段最低预算档×四场景×{不忌口,忌猪}；供给薄时段最高预算档×均衡×{忌猪,忌奶}；'
                       '可选名单逐道相同的条件直接复用结果'),
            gap='缺口＝可选 0 道 / 可选 <5 道 / 实算配不满 3 套 / 3 套里达标（方案状态「推荐」）不足 3 套',
            reason='主因＝只放开一个条件（时段/售罄/预算/忌口）能多救回最多可选菜的那一个',
            cold='冷门菜＝480 种条件里进可选名单次数最少（出现次数代理）；页面每窗口取最冷一道',
            main='主力窗口＝在多少种条件下有菜可选（可配次数），并列看平均可选道数'),
        notes=[
            '钟点按 App 听到「早饭/午饭/晚饭/夜宵」时的默认钟点：早 08:00 / 午 12:30 / 晚 18:30 / 夜宵 21:30。',
            '售罄与配饭页同口径（按当天钟点）：主表售罄时点多记的是午市（12:50–13:30），晚饭钟点会把这些窗口一并判为已收'
            '（CHANGELOG 七-6 已知限制，暂不修）——晚饭缺口里有这部分放大，补采晚市售罄时点后需重扫。',
            '忌香菜：主表没有任何菜标注香菜，可选名单与不忌口完全相同。',
            '条件模拟，不代表真实需求量；上线后换成真实查询日志。营养与等待参数为估算级。'],
        summary=summary, gaps_top=gap_groups[:TOP_N], cold_top=cold_top, main_top=main_top,
        gap_groups=gap_groups, cold_dishes=cold_dishes, windows=windows, runs=runs,
        combos=[{k: v for k, v in c.items() if k != 'gain' or c['gap']} for c in combos])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print(f"\n扫描 {n} 种条件：快筛 {elapsed['prefilter_s']}s，实算 {len(runs)} 次 {elapsed['recommend_s']}s，"
          f"总耗时 {elapsed['total_s']}s → {OUT}")
    print(f"缺口 {summary['n_gap']} 种 {summary['by_kind']} · 主因 {summary['by_reason']}")
    for g in gap_groups[:TOP_N]:
        print(f"  [{g['reason']}] {g['label']} · 同类 {g['count']} 种 · {g['detail']}")
    for d in cold_top:
        print(f"  冷门 {d['name']}（{d['window']}）{d['hits']}/{n} · {d['why']}")
    for w in main_top:
        print(f"  主力 {w['window']}（{w['canteen']}）可配 {w['combos']}/{n} · 平均 {w['avg_dishes']} 道 · {'/'.join(w['periods'])}")


if __name__ == '__main__':
    main()
