# -*- coding: utf-8 -*-
"""干饭决策机 · Streamlit Demo
吃透整座食堂，才敢替你配三套饭。
运行: streamlit run app.py
"""
import html
import os
import random
import sys
from datetime import datetime, date, timedelta

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'engine'))

import loader
import core
import nl_agent
import cache as C
import run_master
import app_helpers as H

st.set_page_config(page_title='干饭决策机', page_icon='🍚', layout='centered')
st.markdown(H.CSS, unsafe_allow_html=True)

MASTER = os.path.join(ROOT, '干饭决策机_数据采集_主表.xlsx')
BANDS = {k: v['E'] for k, v in core.SCEN.items()}
TABOO_ALL = ['猪', '牛', '羊', '海鲜', '蛋', '奶', '花生', '芝麻', '麸质', '香菜', '内脏']
QUICK_TABOO = ['猪', '牛', '羊', '海鲜', '蛋', '奶', '花生', '香菜']   # 快选条忌口 chips（NL 回填仅点亮这 8 项）
SCEN_OPTS = ['均衡', '减脂', '增肌', '省钱']
SCEN_EMOJI = {'均衡': '🍽️', '减脂': '🥗', '增肌': '💪', '省钱': '💰'}
SPICE_OPTS = [0, 1, 2]
SPICE_LABEL = ['不辣', '微辣', '能吃辣']
ANCHOR_OPTS = ['图书馆', '教学楼', '宿舍区']
PARSER_CN = {'rule': '规则解析', 'llm': '大模型解析'}
PERIOD_CN = {'早': '早餐', '午': '午餐', '下午': '下午茶', '晚': '晚餐', '夜宵': '夜宵'}
BUDGET_CAP = 50          # 预算重试按钮在此上限内生效；快选滑杆只能表达 10–30，出界以滑杆边界显示
SRC_QUICK = '快选条（按你拖 / 点的条件）'


@st.cache_resource
def get_bundle():
    return loader.load(MASTER)


@st.cache_resource
def get_cache():
    return C.PlanCache(writeback=True)


@st.cache_resource
def get_index():
    """出餐自检用的菜品索引（与 engine/run_master.py 断言电池同一份）。"""
    return run_master.dish_index(get_bundle())


bundle = get_bundle()
pc = get_cache()

for k, v in dict(req=None, res=None, reasons=[], meta=None, last_nl='', parsed_rc=None,
                rand_note='', last_parsed_req=None, manual_dirty=False,
                req_src='', nl_src='', pick_mode='fixed', avoid_n=0, challenge=None,
                plan_history=[]).items():
    st.session_state.setdefault(k, v)
for k, v in dict(scen='均衡', budget=18, period='午 餐', asof='12:30', anchor='图书馆',
                 spice=2, lazy=False).items():
    st.session_state.setdefault(k, v)
for t in QUICK_TABOO:                                    # 忌口 chips：每个忌口一个布尔键（点亮=忌口）
    st.session_state.setdefault(f'taboo_{t}', False)


def clear_cheats():
    """清空「算放纵餐」勾选：任何新一批方案上线前调用（del 不受实例化限制）。"""
    for i in range(3):
        st.session_state.pop(f'cheat_{i}', None)


def remember_plans(res, reset=False):
    """把本批方案记入本次会话历史（最多 30 套），供「再换一批」判重与跨窗口优先。
    reset=True：一键配饭 = 新一轮配饭起点，历史重置为本次三套（换一批则继续累积）。"""
    if not res:
        return
    hist = [] if reset else st.session_state.plan_history
    for p in res.get('top3', []):
        hist.append(dict(names=sorted(p['names']), wins=sorted(p['wins']), sig=str(p['sig'])))
    st.session_state.plan_history = hist[-30:]


def recent_avoid(days=7):
    """近 7 天打卡吃过的菜（按餐分组）→ avoid/exclude 名单：换着吃，不吃连茬。
    每条打卡一餐 → 一个菜名集合，接入引擎既有 avoid/exclude 机制（C15 至少换 2 道 /
    随机配重叠拒收）；无打卡返回空表，行为与从前完全一致。演示占位菜名不计入。"""
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    meals = []
    for log in H.load_checkins():
        if str(log.get('date', '')) >= since:
            names = {n for n in log.get('items', []) if n and n != '示例搭配（演示）'}
            if names:
                meals.append(names)
    return meals


def do_solve(req, avoid=None, src=None):
    """avoid=None → 自动带上近 7 天打卡史（换着吃）；显式传 () 可退回无回避求解。
    src：决策小票「听懂了什么」的条件来源（None=沿用上一次）。"""
    req = nl_agent.sanitize(req)
    if avoid is None:
        avoid = recent_avoid()
    llm, brk = llm_channel()
    with st.spinner('正在 719 道菜里替你掂量…' if not (pc.get(req) and not avoid) else '正在上菜…'):
        res, reasons, meta = C.solve(bundle, req, cache=pc, avoid=avoid, llm=llm, breaker=brk)
    clear_cheats()
    st.session_state.req = req
    st.session_state.res = res
    st.session_state.reasons = reasons
    st.session_state.meta = meta
    st.session_state.pick_mode = 'fixed'
    st.session_state.avoid_n = len(avoid)
    st.session_state.challenge = None
    remember_plans(res, reset=True)
    if src is not None:
        st.session_state.req_src = src


def do_solve_random(req):
    """随机条件路径：先查随机命名空间缓存（同条件可复现）；未命中用解空间采样
    （1–2s）并回写 rand: 命名空间（origin='random'，永不遮蔽确定性键）。"""
    st.session_state.pick_mode = 'random'
    st.session_state.req_src = '随机抽条件（没输入、也没碰快选条）'
    st.session_state.avoid_n = 0
    st.session_state.challenge = None
    ent = pc.get(req, origin='random')
    if ent:
        st.session_state.req = nl_agent.sanitize(req)
        st.session_state.res = ent['res']
        st.session_state.reasons = ent['reasons']
        st.session_state.meta = dict(hit=True, elapsed=0.0, key=C.req_key(req, origin='random'))
        clear_cheats()
        remember_plans(ent["res"], reset=True)
        return
    with st.spinner('正在随机抽条件、配三套…'):
        rres = core.random_recommend(bundle, req, n=3, exclude=recent_avoid(),
                                     history=st.session_state.plan_history)
    if not rres.get('top3'):
        do_solve(req)                       # 采样不出 → 走完整求解（含放宽阶梯）
        return
    reasons = [nl_agent.rule_explain(req, p) for p in rres['top3']]
    st.session_state.req = nl_agent.sanitize(req)
    st.session_state.res = rres
    st.session_state.reasons = reasons
    st.session_state.meta = dict(hit=False, elapsed=rres['elapsed'], key=C.req_key(req, origin='random'))
    clear_cheats()
    remember_plans(rres, reset=True)
    pc.put(req, rres, reasons, origin='random')


def llm_channel():
    """LLM 优先通道（Key 可选）：st.secrets / 环境变量双通道读 OPENAI_*，部署后在
    Streamlit Cloud 填 Secrets 即自动升级，零代码改动；未配 Key 返回 (None, breaker)，
    解析走规则版、解释走模板，行为与从前完全一致。熔断器挂在会话上：LLM 解析失败/超时
    一次，本会话后续解析与解释直接走离线兜底（回执标注「离线兜底」）。"""
    st.session_state.setdefault('llm_breaker', {'broken': False})
    cfg = {}
    try:
        for k in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL'):
            if k in st.secrets:
                cfg[k] = str(st.secrets[k])
    except Exception:
        pass                                            # 无 secrets.toml / 非 Streamlit 环境
    for k in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL'):
        cfg[k] = cfg.get(k) or os.environ.get(k, '')
    llm = None
    if cfg['OPENAI_API_KEY']:
        llm = nl_agent.OpenAILLM(api_key=cfg['OPENAI_API_KEY'],
                                 base_url=cfg['OPENAI_BASE_URL'] or None,
                                 model=cfg['OPENAI_MODEL'] or None)
    return llm, st.session_state.llm_breaker


def parsed_receipt_of(req, pmeta):
    """解析结果 → 三色听懂回执数据（渲染见 H.heard_receipt_html）：
    ✅ 你说的（origin=user 的字段）/ 📌 我先默认的（origin=default 的关键字段，
    可点按钮跳高级微调）/ 🙁 这个我还管不了（葱姜蒜等闭集外忌口，没有则整行不显示）。"""
    o = pmeta.get('origin') or {}
    user, dflt = [], []

    def put(field, text_user, text_dflt=None):
        """origin=user 进 ✅ 段；default 且给了展示文案的进 📌 段（默认关闭态不展示，免歧义）。"""
        if o.get(field) == 'user':
            user.append(text_user)
        elif text_dflt:
            dflt.append(text_dflt)

    put('scenario', req['scenario'], f"{req['scenario']}（没说就先按这个配）")
    put('B', f"预算 {req['B']:g} 元")
    if o.get('period') == o.get('asof'):                 # 时段与钟点同源 → 合并成一颗
        put('period', f"{PERIOD_CN.get(req['period'], req['period'])} {req['asof']}",
            f"{PERIOD_CN.get(req['period'], req['period'])} {req['asof']}")
    else:
        put('period', PERIOD_CN.get(req['period'], req['period']),
            PERIOD_CN.get(req['period'], req['period']))
        put('asof', req['asof'], req['asof'])
    put('anchor', req['anchor'], f"{req['anchor']}附近")
    put('spice_max', SPICE_LABEL[req['spice_max']], f"辣度先按「{SPICE_LABEL[req['spice_max']]}」")
    put('taboo', '忌 ' + '、'.join(sorted(req['taboo'])))
    put('lazy', '懒人模式（懒得走/赶时间）')
    src = PARSER_CN.get(pmeta['parser'], pmeta['parser'])
    if pmeta.get('fallback'):
        src += ' · 离线兜底'
    return dict(user=user, dflt=dflt, unsupported=list(pmeta.get('unsupported') or []), src=src)


def run_challenge(key):
    """拆台模式：刁难卡题面走与用户完全相同的一句话解析 → 回填快选条 → no_cache 现场实算
    （不读也不写缓存、不带打卡记录 avoid）；「同句连点两次」连算两遍并排比对方案签名。
    须在快选 widgets 实例化之前调用（配饭页顶部 pending_challenge 处）。"""
    c = H.CHALLENGE_BY_KEY[key]
    llm, brk = llm_channel()
    req, pmeta = nl_agent.parse(c['say'], llm=llm, breaker=brk)
    req = nl_agent.sanitize(req)
    parser = PARSER_CN.get(pmeta['parser'], pmeta['parser'])
    if pmeta.get('fallback'):
        parser += ' · 离线兜底'
    st.session_state.last_nl = c['say']
    st.session_state.parsed_rc = parsed_receipt_of(req, pmeta)
    st.session_state.rand_note = ''
    st.session_state.last_parsed_req = req
    st.session_state.nl_src = f'一句话 · {parser}'
    apply_req_to_panel(req)
    st.session_state.manual_dirty = False
    runs = []
    n_runs = 2 if c.get('twin') else 1
    for i in range(n_runs):
        msg = f'🧪 不读预存结果，现场实算中（第 {i + 1}/{n_runs} 遍）…' if n_runs > 1 else '🧪 不读预存结果，现场实算中…'
        with st.spinner(msg):
            res, reasons, meta = C.solve(bundle, req, cache=pc, avoid=(), no_cache=True,
                                         llm=llm, breaker=brk)
        runs.append(dict(elapsed=meta['elapsed'],
                         plans=[(H.sig_code(p['sig']), p['PI']) for p in res.get('top3', [])]))
    clear_cheats()
    st.session_state.req = req
    st.session_state.res = res
    st.session_state.reasons = reasons
    st.session_state.meta = meta
    st.session_state.avoid_n = 0
    st.session_state.pick_mode = 'twin' if c.get('twin') else 'challenge'
    st.session_state.req_src = f"刁难卡「{c['title']}」· 一句话 · {parser}"
    st.session_state.challenge = dict(key=key, ico=c['ico'], title=c['title'], twin=bool(c.get('twin')),
                                      runs=runs, same=len({tuple(r['plans']) for r in runs}) == 1)


def apply_req_to_panel(req):
    """把一个结构化条件回填点亮到快选条（须在快选 widgets 实例化之前调用）。
    预算滑杆只能表达 10–30，出界值以滑杆边界显示；求解永远用原值。"""
    st.session_state.scen = req['scenario'] if req['scenario'] in SCEN_OPTS else '均衡'
    try:
        st.session_state.budget = max(10, min(30, int(req['B'])))
    except (TypeError, ValueError):
        st.session_state.budget = 18
    st.session_state.period = req['period'] + ' 餐'
    st.session_state.asof = req['asof']
    st.session_state.anchor = req['anchor'] if req['anchor'] in ANCHOR_OPTS else '图书馆'
    st.session_state.spice = max(0, min(2, int(req['spice_max'])))
    for t in QUICK_TABOO:                           # chips 外的忌口（芝麻/麸质/内脏）只留在求解条件里
        st.session_state[f'taboo_{t}'] = t in req['taboo']
    st.session_state.lazy = bool(req['lazy'])


def manual_req():
    return dict(scenario=st.session_state.scen, B=st.session_state.budget,
                period=st.session_state.period.split(' ')[0],
                asof=st.session_state.asof, anchor=st.session_state.anchor,
                spice_max=st.session_state.spice,
                taboo={t for t in QUICK_TABOO if st.session_state[f'taboo_{t}']},
                lazy=st.session_state.lazy)


def random_req():
    """没条件时随机抽一组偏好约束：场景/预算/辣度/忌口随机；
    时段/时间/位置（事实类）保持当前值，懒人模式默认关闭。"""
    base = manual_req()
    return dict(scenario=random.choice(['均衡', '均衡', '减脂', '增肌', '省钱']),
                B=random.choice([12, 14, 15, 16, 18, 20, 22, 25]),
                period=base['period'], asof=base['asof'], anchor=base['anchor'],
                spice_max=random.choice([0, 1, 2, 2]),
                taboo=set(random.sample(TABOO_ALL, random.choice([0, 0, 1]))),
                lazy=False)


def mark_manual():
    """标记用户亲手动过快选条 / 高级微调（NL 解析回填不算，见 NL 分支里重置）。"""
    st.session_state.manual_dirty = True
    st.session_state.tune_open = False      # 用户已上手微调，收回「跳高级微调」的强制展开


def ticks_html(labels, cur):
    """滑杆下方的档位标签行：当前档位高亮（随滑杆位置变化，每次 rerun 重绘）。"""
    cells = ''.join(f'<span class="on">{html.escape(l)}</span>' if i == cur
                    else f'<span>{html.escape(l)}</span>' for i, l in enumerate(labels))
    return f'<div class="qb-ticks">{cells}</div>'


# ---------------- 头部 ----------------
st.markdown(f"""<div class="hero">
 <div class="hero-top"><div class="hero-mark">🍚</div>
  <div class="hero-name"><div class="logo">干饭决策机</div>
   <div class="hero-tag">吃透整座食堂，才敢替你配三套饭</div></div></div>
 <div class="data-badges"><span>{len(bundle['dishes'])} 道真实菜</span><span>{len(bundle['windows'])} 个窗口</span>
 <span>6 个食堂区</span><span>一句话配餐</span></div></div>""", unsafe_allow_html=True)

tab_meal, tab_week, tab_canteen, tab_comment, tab_about = st.tabs(
    ['🍚 配饭', '📅 周报', '🏫 食堂视角', '💬 评价', '📖 关于'])

# ---------------- 配饭 ----------------
with tab_meal:
    # 回填快选条只能在快选 widgets 实例化之前做：NL 新句子 / 无解页一键重试 / 刁难卡都只在按钮处
    # 存 pending_req（或 pending_challenge）并立即 rerun，由这里（位于所有 widgets 之前）回填 + 求解。
    pending = st.session_state.pop('pending_req', None)
    if pending is not None:
        apply_req_to_panel(pending)
        st.session_state.manual_dirty = bool(st.session_state.pop('pending_dirty', True))
        st.session_state.rand_note = ''
        do_solve(pending, src=st.session_state.pop('pending_src', SRC_QUICK))
    pending_chal = st.session_state.pop('pending_challenge', None)
    if pending_chal in H.CHALLENGE_BY_KEY:
        run_challenge(pending_chal)

    st.markdown('<div class="ask-row"><div class="ask-ava">🍚</div>'
                '<div class="ask-bubble"><b>跟我说说今天想吃啥</b>'
                '<span>一句话，或者拖下面的快选条</span></div></div>', unsafe_allow_html=True)
    nl = st.text_input('说一句话，剩下的交给我', value=st.session_state.last_nl,
                       placeholder='没想法？不输入也行——点「一键配饭」随机抽组条件配三套',
                       label_visibility='collapsed')
    has_text = bool(nl.strip())
    same_text = has_text and nl.strip() == st.session_state.last_nl
    new_input = has_text and not same_text
    manual_dirty = bool(st.session_state.manual_dirty)

    # ---------------- 滑动快选条：预算 / 场景 / 辣度 / 忌口 ----------------
    # 任一交互 → mark_manual（manual_dirty=True）→ 下一次「一键配饭」按快选条件确定性配。
    scen_now, spice_now = st.session_state.scen, st.session_state.spice
    st.markdown('<div class="qb-head"><span class="qb-t">⚡ 滑动快选</span>'
                '<span class="qb-s">拖一拖、点一点，再按「一键配饭」</span></div>'
                f'<div class="qb-row"><span class="qb-lab">💰 预算上限</span>'
                f'<span class="qb-bval">{st.session_state.budget}<i>元</i></span></div>',
                unsafe_allow_html=True)
    st.slider('预算（元）', 10, 30, step=1, key='budget', on_change=mark_manual,
              label_visibility='collapsed')
    st.markdown('<div class="qb-ends"><span>10 元</span><span>20</span><span>30 元</span></div>',
                unsafe_allow_html=True)
    qs1, qs2 = st.columns(2)
    with qs1:
        st.markdown(f'<div class="qb-row qb-duo"><span class="qb-lab">场景</span>'
                    f'<span class="qb-val">{SCEN_EMOJI[scen_now]} {scen_now}</span></div>',
                    unsafe_allow_html=True)
        st.select_slider('场景', options=SCEN_OPTS, key='scen', on_change=mark_manual,
                         format_func=lambda s: f'{s}{SCEN_EMOJI[s]}', label_visibility='collapsed')
        st.markdown(ticks_html(SCEN_OPTS, SCEN_OPTS.index(scen_now)), unsafe_allow_html=True)
    with qs2:
        st.markdown(f'<div class="qb-row qb-duo"><span class="qb-lab">辣度</span>'
                    f'<span class="qb-val">🌶️ {SPICE_LABEL[spice_now]}</span></div>',
                    unsafe_allow_html=True)
        st.select_slider('辣度', options=SPICE_OPTS, key='spice', on_change=mark_manual,
                         format_func=lambda x: SPICE_LABEL[x], label_visibility='collapsed')
        st.markdown(ticks_html(SPICE_LABEL, spice_now), unsafe_allow_html=True)
    n_taboo = sum(bool(st.session_state[f'taboo_{t}']) for t in QUICK_TABOO)
    st.markdown(f'<div class="qb-row qb-row-chips"><span class="qb-lab">🚫 忌口</span>'
                f'<span class="qb-s">{f"已点亮 {n_taboo} 项 · 再点熄灭" if n_taboo else "点亮 = 不吃，再点熄灭"}</span></div>',
                unsafe_allow_html=True)
    for col, t in zip(st.columns(len(QUICK_TABOO)), QUICK_TABOO):   # 8 列 chips 行（CSS 按 8 列定位成药丸）
        col.checkbox(t, key=f'taboo_{t}', on_change=mark_manual)

    if st.button('🍽️ 一键配饭', type='primary', use_container_width=True):
        if new_input:
            llm, brk = llm_channel()
            req, pmeta = nl_agent.parse(nl, llm=llm, breaker=brk)
            st.session_state.last_nl = nl.strip()
            st.session_state.parsed_rc = parsed_receipt_of(req, pmeta)
            st.session_state.rand_note = ''
            st.session_state.manual_dirty = False               # NL 回填不算手动配置
            st.session_state.last_parsed_req = req              # 记住条件：同句二连击确定性重解用
            parser = PARSER_CN.get(pmeta['parser'], pmeta['parser'])
            if pmeta.get('fallback'):
                parser += ' · 离线兜底'
            st.session_state.nl_src = f"一句话 · {parser}"
            # 快选条在按钮上方、本轮已实例化 → 回填点亮须走 pending + rerun（见本页顶部）
            st.session_state.pending_dirty = False
            st.session_state.pending_src = st.session_state.nl_src
            st.session_state.pending_req = req
            st.rerun()
        elif same_text and not manual_dirty:
            # 同句二连击：快选条没动过 → 按「上次 NL 解析出的条件」确定性重解（缓存命中秒出）
            req = st.session_state.last_parsed_req or manual_req()
            st.session_state.rand_note = ''
            do_solve(req, src=st.session_state.nl_src or '一句话')
        elif not has_text and not manual_dirty:
            req = random_req()                          # 空输入且从未碰快选条 → 随机抽条件
            st.session_state.rand_note = (
                f"{req['scenario']} · {req['B']:g}元 · {SPICE_LABEL[req['spice_max']]}"
                + (f" · 忌{'/'.join(sorted(req['taboo']))}" if req['taboo'] else ''))
            st.session_state.parsed_rc = None
            do_solve_random(req)                        # 该随机条件下的解（缓存可复现）
        else:
            # 空输入+快选条动过，或同句+快选条动过 → 以快选条（+高级微调）为准，确定性解
            st.session_state.rand_note = ''
            st.session_state.parsed_rc = None
            do_solve(manual_req(), src=SRC_QUICK)

    if not has_text:
        if manual_dirty:
            st.markdown(H.hint_html('🎛️ 点「一键配饭」将按上方快选条的条件配（条件动过，同条件结果可复现）；'
                                    '想随机换口味，点结果下方「再换一批」。'),
                        unsafe_allow_html=True)
        else:
            st.markdown(H.hint_html(
                '🎲 没想法？不输入、不碰快选条——点「一键配饭」会随机抽一组条件（场景/预算/辣度/忌口），'
                '每次都不一样；想按固定条件配，就拖一下上面的快选条。'),
                unsafe_allow_html=True)
    elif new_input:
        st.markdown(H.hint_html('💡 新句子 → 点「一键配饭」先听懂再配三套，听懂的条件会回填点亮到快选条'
                                '（同条件可复现）。'), unsafe_allow_html=True)
    elif manual_dirty:
        st.markdown(H.hint_html('💡 这句话已经听懂过了；但快选条动过，点按钮将以快选条上的条件为准（可复现）。'),
                    unsafe_allow_html=True)
    else:
        st.markdown(H.hint_html('💡 这句话已经听懂过了；再点「一键配饭」会按已听懂的条件原样重配一遍'
                                '（结果可复现，缓存命中秒出，不走随机）。'), unsafe_allow_html=True)

    # 三色听懂回执：✅ 你说的 / 📌 我先默认的（点按钮跳高级微调）/ 🙁 管不了的（无则整行不显示）
    rc = st.session_state.parsed_rc
    if rc:
        rc_html = H.heard_receipt_html(rc)
        if rc_html:
            st.markdown(rc_html, unsafe_allow_html=True)
            if rc.get('dflt') and st.button('🎛️ 默认项不合意？点这里去微调', key='jump_tune'):
                st.session_state.tune_open = True
                st.rerun()

    with st.expander('🎛️ 高级微调（时段 / 时间 / 位置 / 懒人）',
                     expanded=bool(st.session_state.pop('tune_open', False))):
        c1, c2 = st.columns(2)
        c1.selectbox('时段', ['午 餐', '早 餐', '下午 餐', '晚 餐', '夜宵 餐'], key='period',
                     on_change=mark_manual)
        c2.selectbox('位置（锚点）', ANCHOR_OPTS, key='anchor', on_change=mark_manual)
        c3, c4 = st.columns(2)
        c3.text_input('时间', key='asof', help='HH:MM，用于售罄与排队判定', on_change=mark_manual)
        c4.checkbox('🛋️ 懒人模式', key='lazy', help='到坐上桌 ≤15 分钟', on_change=mark_manual)

    # ---------------- 拆台模式：给评委的刁难卡（点卡＝no_cache 现场实算） ----------------
    with st.expander('🧪 给评委的刁难卡（6 张 · 点卡＝现场实算）'):
        st.markdown(H.challenge_intro_html(), unsafe_allow_html=True)
        for row in range(0, len(H.CHALLENGES), 2):              # 每行两张，行内对齐
            for col, c in zip(st.columns(2), H.CHALLENGES[row:row + 2]):
                with col:
                    if st.button(f"{c['ico']} {c['title']}", key=f"chal_{c['key']}",
                                 use_container_width=True):
                        st.session_state.pending_challenge = c['key']    # 快选条已实例化 → 顶部回填 + 实算
                        st.rerun()
                    st.markdown(H.challenge_say_html(c), unsafe_allow_html=True)

    res, reasons, meta = st.session_state.res, st.session_state.reasons, st.session_state.meta
    if res is None:
        st.markdown(f"""<div class="empty"><div class="empty-art"><span>🍚</span><span>🍗</span><span>🥬</span></div>
        <div class="empty-t">还没有配饭</div>
        <div class="empty-s">点上面的按钮，我会在 {len(bundle['dishes'])} 道真实菜里配三套；<br>也可以先告诉我预算和忌口。</div></div>""",
                    unsafe_allow_html=True)
    if res is not None:
        if meta:
            # 数字精简：主视觉只留「N 道菜符合你的条件」；缓存命中/耗时收纳进 ⓘ 悬停小字
            detail = '缓存命中 <0.1s' if meta['hit'] else f"实时求解 {meta['elapsed']}s"
            st.markdown(
                f'<div class="solve-meta"><b>{res.get("alive", 0)} 道菜符合你的条件</b>'
                f'<span class="meta-info" title="{html.escape(detail)}">ⓘ</span></div>',
                unsafe_allow_html=True)
        if st.session_state.get('rand_note'):
            st.markdown(H.hint_html(f'🎲 本次随机条件：{st.session_state.rand_note} —— 想换就点下方「再换一批」'),
                        unsafe_allow_html=True)
        tops = res.get('top3', [])
        rq = st.session_state.req
        chal = st.session_state.get('challenge')
        mode = st.session_state.get('pick_mode') or 'fixed'
        if chal:
            st.markdown(H.challenge_banner_html(chal), unsafe_allow_html=True)
            if chal.get('twin'):
                st.markdown(H.twin_html(chal), unsafe_allow_html=True)
        trace = None
        if rq:
            # 决策小票：数字全部按这一次的真实条件现算（硬过滤逐步计数 + 断言电池运行时自检）
            trace = core.prefilter_trace(bundle, rq, core.resolve(rq['scenario'], rq.get('lazy', False)))
            check = (H.self_check(get_index(), rq, tops, quota=mode not in ('random', 'reshuffle'))
                     if tops else None)
            el = chal['runs'][-1]['elapsed'] if chal and chal.get('runs') else (meta or {}).get('elapsed')
            with st.expander('🧾 这顿怎么配出来的', expanded=bool(chal)):
                st.markdown(H.receipt_html(rq, st.session_state.get('req_src') or SRC_QUICK, trace, check,
                                           mode=mode, n_plans=len(tops), elapsed=el,
                                           avoid_n=st.session_state.get('avoid_n', 0),
                                           twin=chal if mode == 'twin' else None),
                            unsafe_allow_html=True)
        if not tops:
            diag = html.escape(H.bottleneck_text(rq, trace)) if (rq and trace) else ''
            st.markdown(f"""<div class="meal-card"><div class="mc-head"><div class="mc-idx">🥲</div>
            <div class="mc-headl"><div class="mc-l1"><b>这条件下真的配不出来，我不想糊弄你。</b></div></div></div>
            <div class="mc-ai"><div class="ai-ava">🤖</div><div class="ai-bub"><span class="ai-name">干饭小助手</span>
            <div class="ai-txt">{diag}试试：① 预算加 2–5 元 ② 辣度放宽一档 ③ 换个时段
            ④ 减少忌口项。忌口与预算上限我绝不会偷偷放宽。</div></div></div></div>""", unsafe_allow_html=True)
            # 一键改条件重试：把「配不出」的挫败路径变成演示亮点（改条件 → 重新配）。
            fail_req = st.session_state.req or {}
            can_budget = bool(fail_req) and float(fail_req.get('B', BUDGET_CAP)) < BUDGET_CAP
            can_taboo = bool(fail_req) and bool(fail_req.get('taboo'))
            if can_budget or can_taboo:
                retry_cols = st.columns(2)
                if can_budget and retry_cols[0].button('💰 预算 +3 元重试', key='retry_budget',
                                                       use_container_width=True):
                    r = dict(fail_req)
                    r['B'] = min(BUDGET_CAP, float(r['B']) + 3)
                    st.session_state.pending_req = nl_agent.sanitize(r)
                    st.session_state.pending_dirty = True
                    st.session_state.pending_src = f"一键重试 · 预算 {float(fail_req['B']):g}→{r['B']:g} 元"
                    st.session_state.parsed_rc = None
                    st.rerun()
                if can_taboo and retry_cols[1].button('🥬 去掉忌口重试', key='retry_taboo',
                                                      use_container_width=True):
                    r = dict(fail_req)
                    r['taboo'] = set()
                    st.session_state.pending_req = nl_agent.sanitize(r)
                    st.session_state.pending_dirty = True
                    st.session_state.pending_src = '一键重试 · 去掉忌口'
                    st.session_state.parsed_rc = None
                    st.rerun()
                tips = []
                if can_budget:
                    tips.append(f"预算 {fail_req['B']:g}→{min(BUDGET_CAP, float(fail_req['B']) + 3):g} 元")
                if can_taboo:
                    tips.append(f"去掉忌口（{'/'.join(sorted(fail_req['taboo']))}）")
                st.caption('一键重试只改你点名的那一项：' + ' 或 '.join(tips)
                           + '；其余条件原样，改完仍配不出会再次诚实告知。')
        else:
            if len(tops) < 3:
                st.caption(f'这个条件下只配得出 {len(tops)} 套不糊弄的方案，宁可少给也不硬凑。')
            for i, p in enumerate(tops):
                st.markdown(H.plan_card(p, reasons[i] if i < len(reasons) else '', i), unsafe_allow_html=True)
                b1, b2 = st.columns([1.3, 1])
                if b1.button('✅ 打卡这餐', key=f'ck_{i}', use_container_width=True):
                    cheat = st.session_state.get(f'cheat_{i}', False)
                    H.save_checkin(dict(date=date.today().isoformat(), ts=datetime.now().isoformat(),
                                        period=st.session_state.req['period'], scenario=st.session_state.req['scenario'],
                                        price=p['PI'], kcal=p['E'], protein=p['Q'], oil=p['O'],
                                        items=[it['name'] for it in p['items']], wins=p['wins'],
                                        kind='放纵' if cheat else '正常'))
                    st.toast('已打卡！去「周报」看看这周的变化 🎉')
                b2.checkbox('🍔 算放纵餐', key=f'cheat_{i}', help='每周放纵配额 3 次，只记账不拦截')
            if st.button('🎲 再换一批（随机重挑三套）', key='reshuffle'):
                with st.spinner('正在重新挑三套…'):
                    preq = st.session_state.req or manual_req()
                    rres = core.random_recommend(
                        bundle, preq, n=3,
                        exclude=[set(p['names']) for p in tops] + recent_avoid(),
                        history=st.session_state.plan_history)
                if rres.get('top3'):
                    st.session_state.res = rres
                    st.session_state.reasons = [nl_agent.rule_explain(preq, p) for p in rres['top3']]
                    st.session_state.meta = dict(hit=False, elapsed=rres['elapsed'], key='reshuffle')
                    st.session_state.pick_mode = 'reshuffle'     # 小票④：同条件随机换的一批
                    st.session_state.challenge = None
                    clear_cheats()                       # 新一批方案上线：放纵餐勾选作废
                    remember_plans(rres)
                    st.rerun()
                else:
                    st.toast('这批条件采样不出新的三套，调调预算或忌口再来')
            st.caption('🎲 再换一批＝同一条件下重新随机挑三套（每次都不一样）；'
                       '称重方案已按克算好价格与营养。')

# ---------------- 周报 ----------------
with tab_week:
    logs = H.load_checkins()
    s = H.week_stats(logs, BANDS)
    st.markdown('<div class="section-title">本周干饭报告</div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="stat-grid">
      <div class="stat"><div class="si">🍚</div><div><div class="num">{s['n']}</div><div class="lab">打卡餐数</div></div></div>
      <div class="stat"><div class="si">✅</div><div><div class="num">{s['rate']}%</div><div class="lab">热量达标率</div></div></div>
      <div class="stat"><div class="si">💰</div><div><div class="num">{s['cost']:g}</div><div class="lab">本周花费(元)</div></div></div>
      <div class="stat"><div class="si">🍔</div><div><div class="num">{s['cheat_left']}</div><div class="lab">放纵配额剩余</div></div></div>
      </div>""", unsafe_allow_html=True)
    st.caption(f"正常 {s['normal']} 餐 · 放纵 {s['cheat']}/3 餐（只记账，不拦截）")
    cells = ''
    for d in s['days']:
        if d['n'] == 0:
            bg, fg = 'linear-gradient(165deg,#F8F1E7,#F3E9DB)', '#B9A48D'
        else:
            depth = min(1.0, d['kcal'] / 1600)
            a = 0.30 + 0.55 * depth
            bg = (f'linear-gradient(165deg,rgba(246,168,110,{min(1.0, a):.2f}),'
                  f'rgba(224,122,63,{min(1.0, a + 0.12):.2f}))')
            fg = '#FFFFFF' if depth > 0.45 else '#6B3E1D'
        cells += (f'<div class="hc" style="background:{bg};color:{fg};border-color:transparent">'
                  f'<b>{d["weekday"]}</b><span>{d["date"][5:]}</span><em>{d["n"]}餐</em></div>')
    st.markdown(f'<div class="heat">{cells}</div>', unsafe_allow_html=True)
    st.caption('颜色越深＝当天热量越高；营养目标为参考区间，非医疗建议。')
    if logs:
        st.markdown('<div class="section-title">最近打卡</div>', unsafe_allow_html=True)
        tl = '<div class="tl">'
        for l in list(reversed(logs))[:8]:
            cheat = l.get('kind') == '放纵'
            kind = '🍔放纵' if cheat else '🍚正常'
            tl += (f'<div class="tl-item"><div class="tl-dot{" c" if cheat else ""}"></div>'
                   f'<div class="tl-card"><div class="tl-top"><b>{l["date"]}</b><span>·</span>'
                   f'<span>{l.get("period", "")}</span><span>·</span><span>{l.get("scenario", "")}</span>'
                   f'<span class="tk">· {kind}</span></div>'
                   f'<div class="tl-items">{"、".join(l.get("items", []))}</div>'
                   f'<div class="tl-kv"><b>{l.get("price", 0):g}元</b><span>·</span>'
                   f'<b>{l.get("kcal", 0):g}kcal</b></div></div></div>')
        st.markdown(tl + '</div>', unsafe_allow_html=True)
        if st.button('🗑️ 清空本机打卡记录（演示）'):
            H.clear_checkins()
            st.rerun()
    else:
        st.info('还没有打卡。回到「配饭」，给一套方案点「打卡这餐」，周报就长出来了。')
        if st.button('✨ 填入示例一周（演示数据，可清空）'):
            for entry in H.demo_week():
                H.save_checkin(entry)
            st.rerun()

# ---------------- 食堂视角（B 端看板原型：读 engine/gap_scan.py 离线结果，不实时扫） ----------------
with tab_canteen:
    gap_rep = H.load_gap_report()
    if gap_rep is None:
        st.info('菜单缺口雷达还没生成：先在本地跑 python engine/gap_scan.py，再回到这一页。')
    else:
        st.markdown(H.gap_page_html(gap_rep), unsafe_allow_html=True)

# ---------------- 评价 ----------------
with tab_comment:
    st.markdown('<div class="section-title">同学们怎么说</div>', unsafe_allow_html=True)
    st.caption('预置样例评价 20 条（演示用，非真实用户数据；赛后接入饭后实测评价闭环）')
    for win, stars, tag, txt in H.COMMENTS:
        st.markdown(H.comment_card(win, stars, tag, txt), unsafe_allow_html=True)

# ---------------- 关于 / 诚实边界 ----------------
with tab_about:
    st.markdown('<div class="section-title">这台决策机的诚实边界</div>', unsafe_allow_html=True)
    st.markdown(H.about_html(len(bundle['dishes']), len(bundle['windows']), len(bundle['std'])),
                unsafe_allow_html=True)
