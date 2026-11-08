# -*- coding: utf-8 -*-
"""nl_agent.py —— NL Agent 链路：自然语言 → 结构化请求JSON → 引擎 → 每方案一句解释
LLM 走 OpenAI 兼容协议（环境变量 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL），
无 key 或调用失败自动回落规则解析；接口抽象层随时可切换实现。
"""
import json
import os
import re

TABOO_WORDS = {
    '猪': ['猪', '猪肉', '排骨', '猪脚', '肥肠'],
    '牛': ['牛', '牛肉', '牛腩', '肥牛', '牛杂'],
    '羊': ['羊', '羊肉', '羊杂'],
    '海鲜': ['海鲜', '鱼', '虾', '蟹', '鱿鱼'],
    '蛋': ['鸡蛋', '蛋'],
    '奶': ['牛奶', '牛乳', '奶牛', '奶', '芝士', '乳制品'],
    '花生': ['花生'],
    '芝麻': ['芝麻', '麻酱'],
    '麸质': ['麸质', '面筋', '面食'],
    '香菜': ['香菜'],
    '内脏': ['内脏', '猪杂', '羊杂', '鸡杂', '鸭血'],
}
# 乳制品长词遮蔽内含的裸词「牛/奶」：『不吃牛奶』忌奶、不忌牛（牛奶≠牛肉）。
# 其余重叠不遮蔽：『不吃猪杂』同时计入 猪+内脏（猪杂既是猪肉也是内脏）。
TABOO_SHIELD = {'牛奶', '牛乳', '奶牛'}
NEG = ['不吃', '不要', '不能吃', '不爱吃', '忌口', '忌', '免', '过敏', '去掉']
SCEN_WORDS = [
    ('减脂', ['减脂', '减肥', '低脂', '瘦身', '掉秤', '少油', '刮油']),
    ('增肌', ['增肌', '健身', '长肌肉', '高蛋白', '练后', '塑形']),
    ('省钱', ['省钱', '便宜', '穷', '实惠', '性价比', '拮据', '吃土']),
    ('均衡', ['均衡', '随便', '正常', '都可以', '营养']),
]
PERIODS = [
    ('夜宵', ['夜宵', '宵夜'], '21:30'),
    ('早', ['早餐', '早上', '早饭'], '08:00'),
    ('午', ['中午', '午饭', '午餐', '午间'], '12:30'),
    ('下午', ['下午茶', '下午'], '15:00'),
    ('晚', ['晚上', '晚饭', '晚餐', '傍晚'], '18:30'),
]
ANCHORS = ['图书馆', '教学楼', '宿舍区', '宿舍', '体育馆', '实验楼']
SCHEMA_HINT = (
    '输出严格JSON：{"scenario":"均衡|减脂|增肌|省钱","B":数字(预算元),'
    '"period":"早|午|下午|晚|夜宵","asof":"HH:MM","anchor":"图书馆|教学楼|宿舍区",'
    '"spice_max":0|1|2(0不辣/1微辣/2辣),"taboo":["猪","牛","羊","海鲜","蛋","奶","花生","芝麻","麸质","香菜","内脏"],'
    '"lazy":true|false(赶时间/懒得走)}。只输出JSON。'
)

# —— 中文数字预算（十五块/二十块/十八块五/一百块……覆盖 1–199 + 块五/块半） ——
CN_DIGIT = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
CN_BUDGET_RE = re.compile(r'([零一二两三四五六七八九十百]+)(?:点([一二两三四五六七八九]))?'
                          r'\s*(块钱?|元)\s*([半一二三四五七八九])?')


def _cn2int(s):
    """中文数字 → 整数（支持 1–199：十五/十八/二十/二十一/一百/一百二十/一百零五）。"""
    total = section = 0
    num = None
    for ch in s:
        if ch in CN_DIGIT:
            num = CN_DIGIT[ch]
        elif ch == '十':
            section += (num if num is not None else 1) * 10
            num = None
        elif ch == '百':
            total += (num if num is not None else 1) * 100
            section = 0
            num = None
        else:
            return None
    v = total + section + (num or 0)
    return v if 0 < v < 1000 else None


def _parse_budget(text):
    """预算必须有语境才算：货币词（块/元/块钱/¥）、预算词（预算/最多/不超过…）、
    或「N(块|元)?以内」。句中任意裸数字不算（『减脂第2周了』『想吃3个菜』『3楼食堂』）。
    中文数字另带量词防误判：『一块鸡排/两块牛排』的"块"是量词不是钱——
    数值≤2 且无小数尾（块五/点五）且后面直接跟实物时不算预算（『十五块牛肉面』照常算）。
    返回 float 或 None。"""
    t = text
    m = re.search(r'[¥￥]\s*(\d+(?:\.\d+)?)', t)                       # ¥18 / ￥18.5
    if m: return float(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:块钱|块|元)', t)               # 18块 / 18元 / 18块钱
    if m: return float(m.group(1))
    for m in CN_BUDGET_RE.finditer(t):                                 # 十五块 / 十八块五 / 十八点五块
        base = _cn2int(m.group(1))
        if base is None:
            continue
        frac = 0.0
        if m.group(2):
            frac = CN_DIGIT[m.group(2)] / 10.0                          # 十八点五块
        elif m.group(4):
            frac = 0.5 if m.group(4) == '半' else CN_DIGIT[m.group(4)] / 10.0   # 十八块半/十八块八
        small = base <= 2 and not m.group(2) and not m.group(4)
        after = t[m.end():]
        if small and not re.match(r'\s*(?:以内|之内|[，。,.;!?！？]|$)', after):
            continue                                                   # 一块/两块+实物 → 量词
        return float(base + frac)
    m = re.search(r'(?:预算|不超过|顶多|最多|上限)\D{0,4}(\d+(?:\.\d+)?)', t)
    if m: return float(m.group(1))
    m = re.search(r'(?:预算|不超过|顶多|最多|上限)\D{0,4}([零一二两三四五六七八九十百]+)', t)
    if m:
        v = _cn2int(m.group(1))
        if v is not None:
            return float(v)
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:块钱?|元)?\s*(?:以内|之内)', t)   # 18以内 / 18块以内
    if m: return float(m.group(1))
    m = re.search(r'(?:花了|花)\D{0,4}(\d+(?:\.\d+)?)', t)               # 花了20
    if m: return float(m.group(1))
    return None


# —— 口语钟点：(早上|上午|中午|下午|傍晚|晚上|夜里|半夜|凌晨)?X点(半|X分)? → asof ——
CLOCK_RE = re.compile(r'(早上|上午|中午|下午|傍晚|晚上|夜里|半夜|凌晨)?\s*(\d{1,2})\s*点\s*(半|(\d{1,2})\s*分?|一刻)?')
CLOCK_HHMM_RE = re.compile(r'(?<![\d:.])(\d{1,2}):(\d{2})(?![\d:])')


def _clock(text):
    """口语钟点 → 'HH:MM'（无钟点返回 None）。
    下午/傍晚/晚上/夜里 自动 +12（下午2点半→14:30）；『晚上/夜里/半夜12点』按午夜 23:59；
    中午 12 点附近：12点保持 12:xx，『中午1点/2点』按口语习惯= 13/14 点。"""
    m = CLOCK_RE.search(text)
    if m:
        pre, hh, mm = m.group(1), int(m.group(2)), 0
        tail = m.group(3)
        if tail == '半':
            mm = 30
        elif tail == '一刻':
            mm = 15
        elif tail:
            mm = int(m.group(4) or tail.rstrip('分'))
        if pre in ('下午', '傍晚'):
            if hh < 12: hh += 12
        elif pre in ('晚上', '夜里', '半夜'):
            if hh == 12: return '23:59'
            if hh < 12: hh += 12
        elif pre == '中午':
            if hh in (1, 2): hh += 12
        # 早上/上午/凌晨/无前缀：钟点原样
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        return f'{hh:02d}:{mm:02d}'
    m2 = CLOCK_HHMM_RE.search(text)
    if m2:
        hh, mm = int(m2.group(1)), int(m2.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f'{hh:02d}:{mm:02d}'
    return None


def _period_from_asof(asof):
    """按 PERIODS 口径（各时段默认钟点为锚）就近归段，跨午夜取环距。"""
    h, m = map(int, asof.split(':'))
    t = h * 60 + m
    best, best_d = None, None
    for period, _words, dflt in PERIODS:
        dh, dm = map(int, dflt.split(':'))
        d = abs(t - (dh * 60 + dm))
        d = min(d, 1440 - d)
        if best_d is None or d < best_d:
            best, best_d = period, d
    return best


class OpenAILLM:
    """OpenAI 兼容 chat completions 客户端（无第三方依赖，urllib 直连）。"""

    def __init__(self, api_key=None, base_url=None, model=None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY', '')
        self.base_url = (base_url or os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')).rstrip('/')
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    @property
    def available(self):
        return bool(self.api_key)

    def complete(self, system, user, timeout=30):
        import urllib.request
        body = json.dumps(dict(model=self.model, temperature=0,
                               messages=[dict(role='system', content=system),
                                         dict(role='user', content=user)])).encode('utf-8')
        rq = urllib.request.Request(self.base_url + '/chat/completions', data=body,
                                    headers={'Content-Type': 'application/json',
                                             'Authorization': 'Bearer ' + self.api_key})
        with urllib.request.urlopen(rq, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data['choices'][0]['message']['content']


def _clause_before(text, pos):
    """pos 前最近句读分隔符到 pos 的从句（否定/忌口语义看这一段）。"""
    start = max(text.rfind(c, 0, pos) for c in '，。；,.;!?！？')
    return text[start + 1:pos]


def _parse_taboo(text):
    """忌口闭集抽取：词表全表扫描（TABOO_SHIELD 长词先遮蔽裸词，如『牛奶』不忌『牛』）；
    词所在从句含否定/忌口语义才算（覆盖『不吃海鲜和香菜』并列，避免『我想吃牛肉』误判）；
    全句出现『忌口/过敏』时任何命中词直接计入。"""
    shield = [(m.start(), m.end()) for w in TABOO_SHIELD if w in text
              for m in re.finditer(re.escape(w), text)]
    hits = []
    for taboo, words in TABOO_WORDS.items():
        for w in words:
            for m in re.finditer(re.escape(w), text):
                if any(m.start() >= s and m.end() <= e and (m.start(), m.end()) != (s, e)
                       for s, e in shield):
                    continue                                   # 遮蔽词自身不遮蔽自己
                hits.append((m.start(), taboo))
    global_neg = any(k in text for k in ['忌口', '过敏'])
    out = set()
    for pos, taboo in hits:
        if global_neg or any(n in _clause_before(text, pos) for n in NEG):
            out.add(taboo)
    return out


def rule_parse(text):
    """规则兜底解析：预算(语境+中文数字) + 忌口词表(带否定语义) + 场景/时段/位置/钟点。"""
    t = text.strip()
    req = dict(scenario='均衡', B=20, period='午', asof='12:30', anchor='图书馆',
               spice_max=2, taboo=set(), lazy=False)
    for scen, words in SCEN_WORDS:
        if any(w in t for w in words):
            req['scenario'] = scen
            break
    B = _parse_budget(t)
    if B is not None:
        B = max(3, min(100, B))
        req['B'] = int(B) if B == int(B) else B
    period_word = None
    for period, words, asof in PERIODS:
        if any(w in t for w in words):
            req['period'], req['asof'] = period, asof
            period_word = period
            break
    clock = _clock(t)                                                  # 口语钟点 → asof
    if clock:
        req['asof'] = clock
        if not period_word:                                            # 没说时段词 → 按 asof 归段
            req['period'] = _period_from_asof(clock)
    for a in ANCHORS:
        if a in t:
            req['anchor'] = '宿舍区' if a == '宿舍' else a
            break
    if any(w in t for w in ['不辣', '免辣', '不要辣', '不能吃辣']):
        req['spice_max'] = 0
    elif any(w in t for w in ['微辣', '少辣', '不要太辣', '别太辣', '一点点辣']):
        req['spice_max'] = 1
    if any(w in t for w in ['懒得走', '不想走', '赶时间', '快点', '懒人', '就近', '不想排队']):
        req['lazy'] = True
    req['taboo'] = _parse_taboo(t)
    return req


def sanitize(req):
    """闭集校验 + 默认值兜底（LLM 输出也必须过这道）。"""
    from core import SCEN
    out = dict(scenario='均衡', B=20, period='午', asof='12:30', anchor='图书馆',
               spice_max=2, taboo=set(), lazy=False)
    if req.get('scenario') in SCEN:
        out['scenario'] = req['scenario']
    try:
        out['B'] = max(3, min(100, float(req.get('B', 20))))
        if out['B'] == int(out['B']):
            out['B'] = int(out['B'])
    except (TypeError, ValueError):
        pass
    if req.get('period') in ('早', '午', '下午', '晚', '夜宵'):
        out['period'] = req['period']
    asof = str(req.get('asof', ''))
    if re.match(r'^\d{1,2}:\d{2}$', asof):
        out['asof'] = asof
    if req.get('anchor'):
        out['anchor'] = str(req['anchor'])
    try:
        out['spice_max'] = max(0, min(2, int(req.get('spice_max', 2))))
    except (TypeError, ValueError):
        pass
    tb = req.get('taboo', set())
    if isinstance(tb, str):
        tb = re.split(r'[,，、]', tb)
    out['taboo'] = {str(x).strip() for x in tb} & set(TABOO_WORDS)
    out['lazy'] = bool(req.get('lazy', False))
    return out


def parse(text, llm=None):
    """NL → AtomReq。返回 (req, meta)；LLM 可用则优先，失败/无key自动规则兜底。"""
    llm = llm or OpenAILLM()
    if llm.available:
        try:
            raw = llm.complete('你是校园干饭助手的需求理解器。' + SCHEMA_HINT, text)
            m = re.search(r'\{.*\}', raw, re.S)
            req = sanitize(json.loads(m.group(0)))
            return req, dict(parser='llm', model=llm.model)
        except Exception:
            pass  # 静默回落，演示不崩
    return sanitize(rule_parse(text)), dict(parser='rule')


def rule_explain(req, p):
    """无LLM时的模板解释：一句人话，说清窗口/菜/钱/营养/放宽。"""
    dishes = '+'.join(it['name'] for it in p['items'])
    loc = p['cant'][0] if p.get('cant') else '校内'
    head = f"{p['PI']:g}元·{loc}{'/'.join(p['wins'])}"
    body = f"{dishes}，{p['E']:g}千卡、蛋白{p['Q']:g}g、油{p['O']:g}g"
    if p['label'] == '自选':
        body += '，称重按克配好不超预算'
    if req['scenario'] == '减脂':
        body += '，清淡少油贴合减脂'
    elif req['scenario'] == '增肌':
        body += '，蛋白优先'
    elif req['scenario'] == '省钱':
        body += '，预算内尽量吃全'
    if p.get('tier'):
        body += f"（{p['tier']['n_meat']}荤{p['tier']['n_veg']}素档含米饭）"
    if p['status'] != '推荐' and p.get('relax'):
        cn = {'槽_主': '主食', '槽_荤': '荤菜', '槽_素': '素菜', '热量下': '热量下限', '热量上': '热量上限',
              '蛋白': '蛋白', '油': '油', '素量': '素菜量', '耗时': '耗时'}
        body += '；已放宽：' + '、'.join(cn.get(k, k) for k in p['relax'])
    return head + '：' + body


def explain(req, res, llm=None):
    """为 Top3 每方案生成一句解释；LLM 失败逐条回落模板。"""
    llm = llm or OpenAILLM()
    out = []
    for p in res.get('top3', []):
        text = None
        if llm.available:
            try:
                brief = dict(items=[it['name'] for it in p['items']], wins=p['wins'], cant=p['cant'],
                             price=p['PI'], kcal=p['E'], protein=p['Q'], oil=p['O'],
                             status=p['status'], relax=p.get('relax', {}), label=p['label'])
                text = llm.complete(
                    '你是贴心的干饭搭子。根据方案JSON写一句≤60字中文推荐理由，口语、温暖、不堆砌数字、'
                    '不提算法/模型/优化等术语；若有relax要诚实说明放宽了什么。',
                    json.dumps(dict(scenario=req['scenario'], budget=req['B'], plan=brief), ensure_ascii=False))
                text = text.strip().strip('"')
            except Exception:
                text = None
        out.append(text or rule_explain(req, p))
    return out
