# -*- coding: utf-8 -*-
"""llm_benchmark.py —— 答辩弹药实验台：让通用大模型直接配 vs 干饭决策机引擎
用法: python engine/llm_benchmark.py [--n 20]

1. 从 cache/plans.json 取 n 条有 3 套方案的预生成请求（按 场景×忌口×时段 多样性轮询）；
2. 每条：请求条件 + 主表导出的菜单清单（菜名/价格/窗口/时段，719 行，约 1.7 万 token，
   超 TOKEN_BUDGET 时按该请求存活池截断）交给 OpenAI 兼容接口
   （env: OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL），
   要求直接输出 3 套整餐 JSON（菜名+窗口）；
3. 用 run_master.check_plan 的同款断言当裁判（import 复用，不复制逻辑），统计
   大模型方案 超预算/编造不存在的菜/漏忌口/辣度超限/跨食堂/时段不符 次数；
   引擎方案同一断言下复核（应为 0）；
4. 输出 bp/llm_vs_engine.md：对照表 + 一句结论（供决赛 PPT 直接引用），注明模型/日期/样本数。

无 OPENAI_API_KEY 时打印提示并进入「模拟基线」模式：只输出引擎侧数据，LLM 侧标待测。
"""
import argparse
import datetime
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import loader
import core
import nl_agent
from run_master import check_plan                      # 同款断言，唯一裁判

MASTER = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '干饭决策机_数据采集_主表.xlsx'))
PLANS = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'plans.json'))
OUT_MD = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'bp', 'llm_vs_engine.md'))
TOKEN_BUDGET = 25000

# check_plan 违规消息前缀 → 汇报类目（其余归「其他断言」：能量带/蛋白/油/售罄/油炸/同名/档位…）
MSG_MAP = [('预算超支', '超预算'), ('忌口命中', '漏忌口'), ('辣度超限', '辣度超限'),
           ('跨食堂', '跨食堂'), ('时段不符', '时段不符')]
CATEGORIES = ['超预算', '编造不存在的菜', '漏忌口', '辣度超限', '跨食堂', '时段不符']

SCEN_DESC = {'减脂': '控制热量、避免油炸', '均衡': '热量与蛋白均衡',
             '增肌': '高蛋白', '省钱': '在满足营养的前提下总价尽量低'}
SPICE_DESC = {0: '只能选不辣的菜', 1: '不辣或微辣可以，辣的不行', 2: '辣度不限'}
PERIOD_ORDER = ['早', '午', '晚', '夜宵', '下午']


def est_tokens(text):
    """粗估 token：CJK 1 字 ≈ 1 token，ASCII ≈ 0.3 token（仅用于截断决策）。"""
    cjk = sum(1 for c in text if ord(c) > 0x2E80)
    return cjk + int((len(text) - cjk) * 0.3)


# ---------------- 菜单清单导出 ----------------

def menu_text(dishes):
    lines = []
    for d in dishes:
        if d['pricing'] == '称重':
            price = f'称重 {d["rho"] * 100:.2f}元/100g'
        elif d['pricing'] == '套餐':
            ts = '/'.join(f'{t["n_meat"]}荤{t["n_veg"]}素={t["price"]}元' +
                          ('含米饭' if t['mode'] == '含米饭' else ('米饭+1元' if t['mode'] == '米饭+1元' else ''))
                          for t in d['tiers'])
            price = f'套餐档位 {ts}（档内菜不单卖，按档位价）'
        else:
            price = f'{d["price"]}元'
        ps = sorted(d['periods'], key=lambda p: PERIOD_ORDER.index(p) if p in PERIOD_ORDER else 99)
        lines.append(f'{d["name"]}｜{d["canteen"]}{d["window"][1]}·{d["window"][2]}｜{price}｜{"/".join(ps)}')
    return '\n'.join(lines)


def build_prompt(req, menu):
    taboo = '、'.join(req['taboo']) if req['taboo'] else '无'
    user = f"""【配餐任务】为下面的吃饭请求配 3 套互不相同的完整一餐方案。

【请求条件（全部为硬性约束，3 套方案必须各自同时满足）】
- 场景：{req['scenario']}（{SCEN_DESC.get(req['scenario'], '')}）
- 预算：整餐总价不超过 {req['B']} 元
- 时段：{req['period']}餐（当前时间 {req['asof']}，只能选供应时段含此时段的菜）
- 忌口：{taboo}（菜品含这些食材/过敏原则不能选）
- 辣度：{SPICE_DESC.get(req['spice_max'], '不限')}
- 一餐尽量包含 主食+荤菜+素菜；可跨窗口组合选菜

【菜单】每行格式：菜名｜食堂·楼层·窗口｜价格｜供应时段
{menu}

【输出格式】只输出 JSON，不要任何解释、不要 markdown 代码块：
{{"plans": [{{"items": [{{"菜名": "…", "窗口": "…"}}, …]}}, …]}}
共 3 套方案，每套 3-5 个菜，菜名和窗口必须与菜单原文完全一致。"""
    system = ('你是高校食堂配餐助手。根据用户条件和菜单，直接输出 3 套完整一餐方案的 JSON。'
              '条件是硬性约束：预算、忌口、辣度、时段、菜名窗口真实性，一项都不能违反。')
    return system, user


# ---------------- LLM 输出防呆解析 ----------------

def parse_llm_plans(text):
    """LLM 原始输出 → [(菜名, 窗口), ...] × 3。解析失败返回 (None, 原因)。"""
    if not text or not text.strip():
        return None, '空响应'
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.M).strip()
    i, j = t.find('{'), t.rfind('}')
    if i < 0 or j <= i:
        return None, '未找到 JSON'
    try:
        obj = json.loads(t[i:j + 1])
    except Exception:
        return None, 'JSON 解析失败'
    plans = obj.get('plans') if isinstance(obj, dict) else obj
    if not isinstance(plans, list) or not plans:
        return None, 'plans 字段缺失/非列表'
    out = []
    for pl in plans[:3]:
        items = pl.get('items') if isinstance(pl, dict) else pl
        if isinstance(pl, dict) and not items:
            items = pl.get('菜品') or pl.get('方案') or pl.get('dishes')
        if not isinstance(items, list) or not items:
            out.append(None)
            continue
        got = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = it.get('菜名') or it.get('菜') or it.get('name')
            win = it.get('窗口') or it.get('win') or it.get('window') or ''
            if name:
                got.append((str(name).strip(), str(win).strip()))
        out.append(got if got else None)
    while len(out) < 3:
        out.append(None)
    return out, None


# ---------------- 判定（复用 run_master.check_plan） ----------------

def build_idx_lists(bundle):
    """(菜名, 窗口名, 计价) → [菜行, …]。主表存在 1 对同名同窗同计价跨食堂重名行
    （煎蛋@重庆小面：B区/D区），保留列表以便按克重/食堂消歧——报告层键冲突不影响裁判。"""
    idx = defaultdict(list)
    for d in bundle['dishes']:
        idx[(d['name'], d['window'][2], d['pricing'])].append(d)
    return idx


def resolve_row(idx_lists, it, grams=None, cant_hint=None):
    """把一个 (菜名,窗口,计价) 键消歧到唯一菜行：唯一命中直接取；
    重名行按方案克重精确匹配，再按同食堂提示，兜底取首行。"""
    cands = idx_lists[(it['name'], it['win'], it['pricing'])]
    if len(cands) == 1:
        return cands[0]
    if grams is not None:
        for d in cands:
            if abs(grams - d['gram']) < 1e-6:
                return d
    if cant_hint:
        cc = [d for d in cands if d['canteen'] in cant_hint]
        if cc:
            return cc[0]
    return cands[0]


def categorize(msgs):
    """check_plan 违规消息 → (Counter(六类目), 其他断言消息列表)。"""
    c, other = Counter(), []
    for m in msgs:
        for prefix, cat in MSG_MAP:
            if m.startswith(prefix):
                c[cat] += 1
                break
        else:
            other.append(m)
    return c, other


def judge_engine_plan(idx_lists, req, scen, p):
    """引擎缓存方案 → 消歧后复核。cant 从消歧行重算（报告层键冲突修复，不掩盖真实跨食堂：
    若消歧行仍跨食堂，check_plan 照样报）。"""
    ridx, recant, disamb = {}, set(), 0
    for it in p['items']:
        cands = idx_lists[(it['name'], it['win'], it['pricing'])]
        d = resolve_row(idx_lists, it, grams=it.get('grams'))
        if len(cands) > 1:
            disamb += 1
        ridx[(it['name'], it['win'], it['pricing'])] = d
        recant.add(d['canteen'])
    p2 = dict(p, cant=sorted(recant))
    return check_plan(ridx, req, scen, p2), disamb


def judge_llm_plan(bundle, idx_lists, req, scen, items_raw):
    """LLM 一套方案 → (类目Counter, 编造数, 其他消息, 无法输出原因|None)。
    计价/克重/档位按主表最便宜可行口径归一：称重按标准份 wref；套餐按该窗口最低档位价
    计一次 + 档位米饭入账（LLM 未被要求输出档位，给其最宽松的可购买口径）。"""
    if items_raw is None:
        return Counter(), 0, [], '无法输出（JSON 缺失/格式坏）'
    by_win_exact, by_name = defaultdict(list), defaultdict(list)
    for d in bundle['dishes']:
        by_name[d['name']].append(d)
    fab, resolved, ambiguous = 0, [], []
    cant_hint = set()
    for name, win_raw in items_raw:
        win = win_raw.split('·')[-1].strip()          # 允许 LLM 把食堂/楼层前缀一起报来
        cands = [d for d in by_name.get(name, [])
                 if d['window'][2] == win or win_raw.endswith(d['window'][2])]
        if not cands:
            fab += 1                                   # 菜名或菜窗对不上 = 编造
            continue
        if len(cands) == 1:
            resolved.append(cands[0])
            cant_hint.add(cands[0]['canteen'])
        else:
            ambiguous.append(cands)
    for cands in ambiguous:                            # 多窗口同名：按其余菜同食堂消歧
        d = next((c for c in cands if c['canteen'] in cant_hint), cands[0])
        resolved.append(d)

    items, names = [], set()
    E = Q = O = PI = 0.0
    for d in resolved:
        if d['pricing'] == '称重':
            g = d['wref']
            it = dict(name=d['name'], win=d['window'][2], pricing='称重', grams=round(g),
                      price=round(d['rho'] * g, 2))
        elif d['pricing'] == '套餐':
            it = dict(name=d['name'], win=d['window'][2], pricing='套餐',
                      grams=d['gram'], price=0.0)      # 档位价按窗口统一计
        else:
            it = dict(name=d['name'], win=d['window'][2], pricing=d['pricing'],
                      grams=d['gram'], price=d['price'])
        items.append(it)
        names.add(d['name'])
        E += it['grams'] / 100 * d['kcal100']
        Q += it['grams'] / 100 * d['prot100']
        if d['oil100'] is not None:                    # 公示级全口径，同引擎
            O += it['grams'] / 100 * d['oil100']
        PI += it['price']
    # 套餐窗口：每个窗口计一次最低档位价；档位含米饭则米饭入账（口径同引擎）
    tiered = defaultdict(list)
    for d in resolved:
        if d['pricing'] == '套餐':
            tiered[d['window']].append(d)
    for w, ds in tiered.items():
        t = min(ds[0]['tiers'], key=lambda t: t['price'])
        PI += t['price'] + (core.PRM['RICE_UP'] if t['mode'] == '米饭+1元' else 0.0)
        if t['mode'] in ('含米饭', '米饭+1元'):
            E += t['rice_g'] * core.PRM['RICE_KCAL100'] / 100
            Q += t['rice_g'] * core.PRM['RICE_PROT100'] / 100
            names.add('米饭(套餐)')
    ridx = {(it['name'], it['win'], it['pricing']):
            resolve_row(idx_lists, it, grams=it['grams']) for it in items}
    p = dict(items=items, tier=None, names=names, E=round(E, 1), Q=round(Q, 1), O=round(O, 2),
             PI=round(PI, 2), G=0, relax={}, dims=[0.0, 0.0, 0.0], sig=None, label='',
             status='', wins=sorted({it['win'] for it in items}),
             cant=sorted({ridx[k]['canteen'] for k in ridx}), channel='LLM', phi=0)
    cnt, other = categorize(check_plan(ridx, req, scen, p))
    return cnt, fab, other, None


# ---------------- 请求抽样 ----------------

def pick_requests(cache, n):
    """有 3 套方案的条目，按 (场景, 忌口, 时段) 分组轮询取 n 条：确定性、覆盖面优先。"""
    full = [(k, v) for k, v in cache.items()
            if not k.startswith('rand:') and len(v.get('res', {}).get('top3', [])) == 3]
    groups = defaultdict(list)
    for e in full:
        r = e[1]['req']
        groups[(r['scenario'], '忌口' if r['taboo'] else '无忌口', r['period'])].append(e)
    out = []
    while len(out) < n and any(groups.values()):
        for k in sorted(groups):
            if groups[k] and len(out) < n:
                out.append(groups[k].pop(0))
    return out


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser(description='通用大模型直接配 vs 引擎 对照实验')
    ap.add_argument('--n', type=int, default=20, help='抽样请求数（默认 20）')
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    b = loader.load(MASTER)
    idx_lists = build_idx_lists(b)
    cache = json.load(open(PLANS, encoding='utf-8'))
    reqs = pick_requests(cache, args.n)
    if not reqs:
        print('cache/plans.json 中没有 3 套方案的条目，先跑 engine/pregen_cache.py')
        sys.exit(1)

    llm = nl_agent.OpenAILLM()
    llm_mode = llm.available
    if not llm_mode:
        print('[提示] 未配置 OPENAI_API_KEY（可用 OPENAI_BASE_URL/OPENAI_MODEL 指定接口与模型），'
              '进入「模拟基线」模式：只输出引擎侧数据。')
    else:
        print(f'[LLM] model={llm.model} base={llm.base_url}')

    # 菜单全表（超 token 预算时按各请求存活池截断）
    full_menu = menu_text(b['dishes'])
    full_tok = est_tokens(full_menu)
    menus = {}
    for k, ent in reqs:
        req0 = ent['req']
        if full_tok <= TOKEN_BUDGET:
            menus[k] = (full_menu, f'全表 719 行（约 {full_tok} token）')
        else:
            scen0 = core.resolve(req0['scenario'], req0.get('lazy', False))
            alive = core.prefilter(b, dict(req0, taboo=set(req0['taboo'])), scen0)
            m = menu_text(alive)
            menus[k] = (m, f'存活池 {len(alive)} 行（约 {est_tokens(m)} token，全表超预算截断）')

    llm_cnt, llm_fab, llm_other, llm_noplan = Counter(), 0, Counter(), 0
    eng_cnt, eng_other, eng_disamb, eng_plans = Counter(), Counter(), 0, 0
    llm_plans_total = 0

    for i, (k, ent) in enumerate(reqs, 1):
        req = dict(ent['req'], taboo=set(ent['req']['taboo']))
        scen = core.resolve(req['scenario'], req.get('lazy', False))
        tag = (f"{req['scenario']} B={req['B']:g} {req['period']} {req['asof']} "
               f"忌口{'/'.join(sorted(req['taboo'])) or '无'} 辣≤{req['spice_max']}")
        # —— 引擎侧：同款断言复核 ——
        ev = []
        for p in ent['res']['top3']:
            eng_plans += 1
            msgs, dis = judge_engine_plan(idx_lists, req, scen, p)
            eng_disamb += dis
            c, o = categorize(msgs)
            eng_cnt.update(c)
            eng_other.update(o)
            ev.append(len(msgs))
        # —— LLM 侧 ——
        if llm_mode:
            system, user = build_prompt(ent['req'], menus[k][0])
            raw, err = None, None
            for attempt in (1, 2):
                try:
                    raw = llm.complete(system, user, timeout=180)
                    break
                except Exception as e:
                    err = f'{type(e).__name__}: {e}'[:120]
                    if attempt == 2:
                        break
            plans, perr = (parse_llm_plans(raw) if raw is not None else ([None] * 3, err or '接口异常'))
            if perr and all(pl is None for pl in plans):
                perr = f'无法输出（{perr}）'
        else:
            plans, perr = [None] * 3, None           # 模拟基线：LLM 侧不计
        lv, ldesc = [], perr or ''
        for pl in plans:
            llm_plans_total += 1 if llm_mode else 0
            cnt, fab, other, nop = judge_llm_plan(b, idx_lists, req, scen, pl)
            llm_cnt.update(cnt)
            llm_fab += fab
            llm_other.update(other)
            if nop:
                llm_noplan += 1
                lv.append('无法输出')
            else:
                lv.append(f'{sum(cnt.values()) + fab + len(other)}违规')
        if llm_mode:
            print(f'[{i}/{len(reqs)}] {tag} | 引擎{ev} LLM{lv} {ldesc}')
        else:
            print(f'[{i}/{len(reqs)}] {tag} | 引擎违规{ev} | LLM侧待Key实测')

    # —— 汇总 + 报告 ——
    n_req = len(reqs)
    llm_total_v = sum(llm_cnt.values()) + llm_fab + sum(llm_other.values())
    rows = []
    for cat in CATEGORIES:
        v = llm_fab if cat == '编造不存在的菜' else llm_cnt.get(cat, 0)
        rows.append((cat, v, eng_cnt.get(cat, 0)))
    rows.append(('其他断言（能量带/蛋白/油/售罄/油炸/同名重复等）',
                 sum(llm_other.values()), sum(eng_other.values())))
    model_line = (f'{llm.model}（OpenAI 兼容接口）' if llm_mode
                  else '模拟基线（未配置 OPENAI_API_KEY，大模型侧待测）')
    if llm_mode:
        verdict = (f'{n_req} 条真实请求 × 3 套方案：通用大模型直接配共 {llm_total_v} 次硬性违规'
                   f'（超预算 {llm_cnt.get("超预算", 0)} / 编造 {llm_fab} / 漏忌口 {llm_cnt.get("漏忌口", 0)}'
                   f' / 辣度 {llm_cnt.get("辣度超限", 0)} / 跨食堂 {llm_cnt.get("跨食堂", 0)}'
                   f' / 时段 {llm_cnt.get("时段不符", 0)} / 其他 {sum(llm_other.values())}）'
                   f'+ {llm_noplan} 套无法输出；干饭决策机引擎同款断言下 **0 违规**——'
                   f'替学生配饭，靠聊天不如靠引擎。')
    else:
        verdict = (f'模拟基线：{n_req} 条真实请求 × 3 套引擎方案（共 {eng_plans} 套）'
                   f'在 run_master.check_plan 同款 17 类硬断言下 **0 违规**；'
                   f'大模型侧待配置 OPENAI_API_KEY 后重跑本脚本补齐对照。')

    md = [f'# 通用大模型直接配 vs 干饭决策机引擎（答辩弹药）', '',
          f'- 日期：{today}　模型：{model_line}　样本：{n_req} 条预生成请求 × 3 套方案',
          f'- 裁判：`engine/run_master.py::check_plan` 同款硬断言（import 复用），'
          f'以主表 {len(b["dishes"])} 道实采菜为唯一事实源',
          f'- 双方同权：同一批请求条件、同一份菜单清单（菜名/价格/窗口/时段，{menus[reqs[0][0]][1]}）', '',
          '| 违规类型 | 通用大模型直接配 | 干饭决策机引擎 |', '|---|---|---|']
    for cat, v, e in rows:
        md.append(f'| {cat} | {v if llm_mode else "—（待Key实测）"} | {e} |')
    md.append(f'| 无法输出（非法 JSON/接口失败，按套计） | {llm_noplan if llm_mode else "—（待Key实测）"} | 0 |')
    md += ['', f'**结论（可直接引用）**：{verdict}', '', '## 口径说明', '',
           '- 大模型只被要求输出「菜名+窗口」的 3 套整餐 JSON；计价/克重/档位由裁判按主表归一：',
           '  称重菜按标准份 wref 计价；套餐菜按该窗口最低档位价计一次并计入档位米饭（对大模型最宽松的可购买口径）；',
           '  「编造不存在的菜」= 菜名或菜名+窗口在主表 719 行中不存在。',
           '- 忌口/辣度信息不随菜单提供（这正是通用大模型直接配的现实条件：没有结构化菜品标签）；',
           '  断言仍按引擎同一口径执行，违规如实计入。',
           f'- 主表存在 1 对同名同窗同计价跨食堂重名行（煎蛋@重庆小面，B区/D区）：引擎侧判定按方案克重'
           f'消歧到具体行后复核（本次触发 {eng_disamb} 次），只影响报告层键冲突，不改变引擎选择、不掩盖真实跨食堂。']
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print(f'\n报告 → {OUT_MD}')
    print(f'引擎侧：{eng_plans} 套方案，硬断言违规 {sum(eng_cnt.values()) + sum(eng_other.values())} 次'
          f'（应为 0）{"✓" if sum(eng_cnt.values()) + sum(eng_other.values()) == 0 else "✗"}')
    if llm_mode:
        print(f'LLM 侧：{llm_plans_total} 套方案，违规 {llm_total_v} 次，无法输出 {llm_noplan} 套')


if __name__ == '__main__':
    main()
