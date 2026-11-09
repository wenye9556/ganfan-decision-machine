# -*- coding: utf-8 -*-
"""nl_agent.py —— NL Agent 链路：自然语言 → 结构化请求JSON → 引擎 → 每方案一句解释
LLM 走 OpenAI 兼容协议（OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL），
无 key 或调用失败自动回落规则解析；接口抽象层随时可切换实现。
字段来源跟踪：parse() 的 meta 附 origin={field:'user'|'default'}（用户明确提到=user，
sanitize/兜底默认补的=default），供 UI 三色听懂回执（✅ 你说的 / 📌 我先默认的 / 🙁 管不了的）。
LLM 优先通道带熔断：解析超时(8s)/失败一次 → breaker['broken']=True，本会话后续解析与
解释直接走规则版（meta.fallback=True，UI 标注「离线兜底」）；未配 Key 行为与从前完全一致。
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
# 饮食模式短语 → 忌口闭集映射（整句命中即计入，无须否定词；与词表扫描结果取并集）：
# 吃素/不吃肉 → 忌红肉{猪,牛,羊}；清真/穆斯林 → 猪牛羊+内脏（闭集能力内的近似）；
# 乳糖不耐 → 忌奶。葱姜蒜等不在闭集内，识别不了就不硬猜——留给「管不了就明说」。
# 注意否定语义：『不吃素』是能吃肉，不触发素食映射。
DIET_TABOO = [
    ('清真', ('清真', '穆斯林'), {'猪', '牛', '羊', '内脏'}),
    ('素食', ('吃素', '不吃肉'), {'猪', '牛', '羊'}),
    ('乳糖不耐', ('乳糖不耐', '乳糖不耐受'), {'奶'}),
]
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
    '"lazy":true|false(赶时间/懒得走),'
    '"unsupported":["葱"|"姜"|"蒜"等用户明确说不能吃、但不在taboo闭集内的食材词]}。'
    '只填用户这句话里明确提到的字段，没提到的字段整个省略不要替用户猜（由默认值补）；'
    'unsupported 没有就给空数组。只输出JSON。'
)
# 字段来源口径（三色回执用）：parse() 的 meta['origin'] 对这些字段逐一标 'user'/'default'
ORIGIN_FIELDS = ('scenario', 'B', 'period', 'asof', 'anchor', 'spice_max', 'taboo', 'lazy')
# 闭集外忌口类别（菜品档案没标到这么细）：命中就如实交出「管不了」，绝不硬猜进 taboo
UNSUPPORTED_TABOO = {
    '葱姜蒜': ['葱姜蒜', '葱花', '蒜末', '蒜蓉', '生姜', '大蒜', '香葱', '姜蓉', '葱', '姜', '蒜'],
}
# LLM 优先通道参数：解析超时 8s；解释三套合并为一次调用，超时 15s
LLM_PARSE_TIMEOUT = 8
LLM_EXPLAIN_TIMEOUT = 15
# 模块级兜底熔断器（app 按会话传入自己的 breaker；引擎独立跑时共用这一份）
_BREAKER = {'broken': False}

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
    # 前缀填充词只允许「非数字且非中文数字」（如 大概/左右/花）：\D 会吞掉中文数字首字，
    # 『预算二十』曾解析成 10（\D 吃掉"二"、捕获组只剩"十"）。排除字类后 二十/十八/十五 完整捕获。
    m = re.search(r'(?:预算|不超过|顶多|最多|上限)[^\d零一二两三四五六七八九十百]{0,4}'
                  r'([零一二两三四五六七八九十百]+)', t)
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
# 小时/分钟均支持 ASCII 数字与中文数字（晚上8点 / 晚上八点 / 八点二十分）
CLOCK_NUM = r'(?:\d{1,2}|[零一二两三四五六七八九十]{1,3})'
CLOCK_RE = re.compile(r'(早上|上午|中午|下午|傍晚|晚上|夜里|半夜|凌晨)?\s*(' + CLOCK_NUM +
                      r')\s*点\s*(半|一刻|(' + CLOCK_NUM + r')\s*分?)?')
CLOCK_HHMM_RE = re.compile(r'(?<![\d:.])(\d{1,2}):(\d{2})(?![\d:])')


def _clock_num(s):
    """钟点数字段（ASCII 或中文）→ int；解析不了返回 None。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    return _cn2int(s)


def _clock(text):
    """口语钟点 → 'HH:MM'（无钟点返回 None）。
    下午/傍晚/晚上/夜里 自动 +12（下午2点半→14:30、晚上八点→20:00）；
    『晚上/夜里/半夜12点』按午夜 23:59；
    中午 12 点附近：12点保持 12:xx，『中午1点/2点』按口语习惯= 13/14 点。
    货币语境守卫：『十八点五块/八点五元』的"点"是小数点不是钟点，紧跟块/元即判钱。"""
    m = CLOCK_RE.search(text)
    if m and re.match(r'\s*[块元]', text[m.end():]):
        m = None                                            # 十八点五块＝18.5元，不是 18:05
    if m:
        pre, hh, mm = m.group(1), _clock_num(m.group(2)), 0
        if hh is None:
            return None
        tail = m.group(3)
        if tail == '半':
            mm = 30
        elif tail == '一刻':
            mm = 15
        elif tail:
            mm = _clock_num(m.group(4) or tail.rstrip('分'))
            if mm is None:
                mm = 0
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


def _diet_taboo(text):
    """饮食模式短语 → 忌口集（DIET_TABOO 整句扫描；『不吃素』否定式不触发素食）。"""
    out = set()
    for _name, phrases, taboos in DIET_TABOO:
        for ph in phrases:
            if ph in text and not (ph == '吃素' and '不吃素' in text):
                out |= taboos
                break
    return out


def _parse_unsupported(text):
    """闭集外忌口（葱姜蒜等）：句中命中且所在从句带否定/忌口/避开语义 → 如实列出。
    与 _parse_taboo 同一套否定判据（『我想吃葱油拌面』不误报）；长词命中后遮蔽内含
    短词（『葱姜蒜』只报一次，不再拆出葱/姜/蒜）。返回命中原词列表（展示用）。"""
    global_neg = any(k in text for k in ['忌口', '过敏'])
    seen = set()
    for words in UNSUPPORTED_TABOO.values():
        for w in words:
            for m in re.finditer(re.escape(w), text):
                if global_neg or any(n in _clause_before(text, m.start()) for n in NEG):
                    seen.add(w)
    kept = []
    for w in sorted(seen, key=len, reverse=True):        # 长词优先，短词是其子串则不重复报
        if not any(w in k for k in kept):
            kept.append(w)
    return kept


def rule_parse(text):
    """规则兜底解析（保持原契约：只返回 req dict，兼容既有调用与回归电池）。"""
    return rule_parse_full(text)[0]


def rule_parse_full(text):
    """规则解析 + 字段来源：返回 (req, origin, unsupported)。
    origin={field:'user'|'default'}——用户话语里明确提到的字段（场景/预算/时段/辣度/
    忌口/懒人/钟点/位置）标 user，引擎兜底默认（sanitize 同款默认值）标 default。"""
    t = text.strip()
    req = dict(scenario='均衡', B=20, period='午', asof='12:30', anchor='图书馆',
               spice_max=2, taboo=set(), lazy=False)
    origin = {f: 'default' for f in ORIGIN_FIELDS}
    for scen, words in SCEN_WORDS:
        if any(w in t for w in words):
            req['scenario'] = scen
            origin['scenario'] = 'user'
            break
    B = _parse_budget(t)
    if B is not None:
        B = max(3, min(100, B))
        req['B'] = int(B) if B == int(B) else B
        origin['B'] = 'user'
    period_word = None
    for period, words, asof in PERIODS:
        if any(w in t for w in words):
            req['period'], req['asof'] = period, asof
            period_word = period
            origin['period'] = 'user'                       # 时段词只标时段；asof 是段内默认锚点
            break
    clock = _clock(t)                                                  # 口语钟点 → asof
    if clock:
        req['asof'] = clock
        origin['asof'] = 'user'
        if not period_word:                                            # 没说时段词 → 按钟点归段
            req['period'] = _period_from_asof(clock)
            origin['period'] = 'user'                                  # 钟点推出的时段也算用户给的
    for a in ANCHORS:
        if a in t:
            req['anchor'] = '宿舍区' if a == '宿舍' else a
            origin['anchor'] = 'user'
            break
    if any(w in t for w in ['不辣', '免辣', '不要辣', '不能吃辣', '不吃辣', '怕辣', '吃不了辣']):
        req['spice_max'] = 0
        origin['spice_max'] = 'user'
    elif any(w in t for w in ['微辣', '少辣', '不要太辣', '别太辣', '一点点辣']):
        req['spice_max'] = 1
        origin['spice_max'] = 'user'
    if any(w in t for w in ['懒得走', '不想走', '赶时间', '快点', '懒人', '就近', '不想排队']):
        req['lazy'] = True
        origin['lazy'] = 'user'
    req['taboo'] = _parse_taboo(t) | _diet_taboo(t)
    if req['taboo']:
        origin['taboo'] = 'user'
    return req, origin, _parse_unsupported(t)


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


def _origin_from_llm_raw(raw):
    """LLM 通道的字段来源：提示词要求只填用户提到的字段 → 原始 JSON 里有值即 user，
    省略/留空即 default（值由 sanitize 补默认）。"""
    origin = {f: 'default' for f in ORIGIN_FIELDS}

    def said(v):
        return v is not None and v != '' and v != [] and v != {}

    if said(raw.get('scenario')):
        origin['scenario'] = 'user'
    if said(raw.get('B')):
        origin['B'] = 'user'
    if said(raw.get('period')):
        origin['period'] = 'user'
    if said(raw.get('asof')):
        origin['asof'] = 'user'
    if said(raw.get('anchor')):
        origin['anchor'] = 'user'
    if raw.get('spice_max') is not None:
        origin['spice_max'] = 'user'
    tb = raw.get('taboo')
    if (isinstance(tb, (list, tuple, set)) and len(tb) > 0) or (isinstance(tb, str) and tb.strip()):
        origin['taboo'] = 'user'
    if raw.get('lazy') is True:
        origin['lazy'] = 'user'
    return origin


def parse(text, llm=None, breaker=None):
    """NL → AtomReq。返回 (req, meta)；配置 Key 时解析优先走 LLM（超时 8s），
    失败/超时 → 熔断（breaker['broken']=True），本会话后续解析直接走规则版并在
    meta 标 fallback=True（UI 回执标注「离线兜底」）。未配 Key 与从前行为完全一致。
    meta 附 origin={field:'user'|'default'}（字段来源，三色回执用）与
    unsupported（葱姜蒜等闭集外忌口原词，如实交出）。"""
    llm = llm or OpenAILLM()
    breaker = breaker if breaker is not None else _BREAKER
    if llm.available and not breaker.get('broken'):
        try:
            raw = llm.complete('你是校园干饭助手的需求理解器。' + SCHEMA_HINT, text,
                               timeout=LLM_PARSE_TIMEOUT)
            m = re.search(r'\{.*\}', raw, re.S)
            raw_json = json.loads(m.group(0))
            req = sanitize(raw_json)
            uns = raw_json.get('unsupported') or []
            if isinstance(uns, str):
                uns = re.split(r'[,，、]', uns)
            uns = [str(x).strip() for x in uns if str(x).strip()]
            return req, dict(parser='llm', model=llm.model,
                             origin=_origin_from_llm_raw(raw_json), unsupported=uns[:6])
        except Exception:
            breaker['broken'] = True          # 本会话熔断：后续解析不再试 LLM
    req, origin, uns = rule_parse_full(text)
    meta = dict(parser='rule', origin=origin, unsupported=uns)
    if llm.available and breaker.get('broken'):
        meta['fallback'] = True              # 有 Key 但本会话已降级 → 离线兜底
    return sanitize(req), meta


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


def explain(req, res, llm=None, breaker=None):
    """为 Top3 每方案生成一句解释。三套合并为一次 LLM 调用（批量提示词一次返回 3 段，
    替代原逐套调用）；失败/超时/段数不符 → 整批回落 rule_explain 模板。熔断状态下
    （breaker['broken']）不再试 LLM，直接模板，保证离线兜底也不拖慢演示。"""
    llm = llm or OpenAILLM()
    breaker = breaker if breaker is not None else {}
    plans = res.get('top3', [])
    texts = None
    if llm.available and not breaker.get('broken') and plans:
        try:
            briefs = [dict(items=[it['name'] for it in p['items']], wins=p['wins'], cant=p['cant'],
                           price=p['PI'], kcal=p['E'], protein=p['Q'], oil=p['O'],
                           status=p['status'], relax=p.get('relax', {}), label=p['label'])
                      for p in plans]
            raw = llm.complete(
                '你是贴心的干饭搭子。输入JSON里有plans数组（共%d套方案）。对每一套写一句≤60字中文推荐'
                '理由，口语、温暖、不堆砌数字、不提算法/模型/优化等术语；若有relax要诚实说明放宽了什么。'
                '输出严格JSON：一个字符串数组，长度必须等于%d、顺序与plans一致，第i条对应第i套；'
                '除该数组外不要输出任何文字。' % (len(briefs), len(briefs)),
                json.dumps(dict(scenario=req['scenario'], budget=req['B'], plans=briefs), ensure_ascii=False),
                timeout=LLM_EXPLAIN_TIMEOUT)
            m = re.search(r'\[.*\]', raw, re.S)
            arr = json.loads(m.group(0))
            if isinstance(arr, list) and len(arr) == len(plans):
                texts = [str(x).strip().strip('"') for x in arr]
        except Exception:
            texts = None                                  # 整批回落模板，不逐套重试
    out = []
    for i, p in enumerate(plans):
        t = texts[i] if texts and i < len(texts) else ''
        out.append(t or rule_explain(req, p))
    return out
