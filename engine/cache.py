# -*- coding: utf-8 -*-
"""cache.py —— 方案缓存：键=规范化请求哈希（含 CACHE_VERSION）；命中<0.1s，未命中实时求解并回写。
条目带 origin（'pregen' 预生成 / 'solve' 实时求解 / 'random' 随机配）：
  · 确定性查询（get 不带 origin / origin='solve'|'pregen'）只命中非 random 条目；
  · 随机路径写入独立命名空间（键前缀 'rand:'），永远不遮蔽确定性键；
  · origin='random' 的 get 只查 rand: 命名空间。
引擎行为改变（改参数/改模型/改数据口径）时手动 bump CACHE_VERSION，旧键自然失效。"""
import hashlib
import json
import os
import time

import core
import nl_agent

DEFAULT_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'plans.json'))

CACHE_VERSION = 2        # v2：B 统一 float 归一 + origin 字段 + rand 命名空间（2026-11 引擎修复线）
RAND_PREFIX = 'rand:'
ORIGINS = ('pregen', 'solve', 'random')


def norm_req(req):
    return dict(scenario=req['scenario'], B=float(req['B']), period=req['period'], asof=req['asof'],
                anchor=req['anchor'], spice_max=int(req['spice_max']),
                taboo=sorted(req.get('taboo', [])), lazy=bool(req.get('lazy', False)))


def req_key(req, origin=None):
    """origin='random' → 'rand:' 前缀键（独立命名空间）；其余同一确定性键（版本在哈希盐里）。"""
    blob = json.dumps(dict(v=CACHE_VERSION, req=norm_req(req)), ensure_ascii=False, sort_keys=True)
    base = hashlib.sha1(blob.encode('utf-8')).hexdigest()[:16]
    return RAND_PREFIX + base if origin == 'random' else base


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted(jsonable(v) for v in o)
    return o


class PlanCache:
    def __init__(self, path=DEFAULT_PATH, writeback=True):
        self.path = path
        self.writeback = writeback
        self.store = {}
        if os.path.exists(path):
            try:
                self.store = json.load(open(path, encoding='utf-8'))
            except Exception:
                self.store = {}

    def get(self, req, origin=None):
        """确定性查询（origin=None）只命中非 random 条目；origin='random' 查随机命名空间。"""
        if origin == 'random':
            return self.store.get(req_key(req, origin='random'))
        ent = self.store.get(req_key(req))
        return ent if ent and ent.get('origin', 'solve') != 'random' else None

    def put(self, req, res, reasons, origin='solve'):
        """origin：'pregen'（预生成）/ 'solve'（实时求解）/ 'random'（随机配 → rand: 键）。"""
        if not self.writeback:
            return
        self.store[req_key(req, origin=origin)] = dict(
            req=norm_req(req), res=jsonable(res), reasons=reasons, origin=origin)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + f'.{os.getpid()}.tmp'
        json.dump(self.store, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
        for _ in range(5):                       # Windows 多进程下目标文件可能被短暂占用
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                time.sleep(0.2)
        try:                                     # 落盘失败只留内存，绝不让求解崩在缓存上
            os.remove(tmp)
        except OSError:
            pass


def solve(bundle, req, cache=None, llm=None, avoid=(), origin='solve', no_cache=False):
    """统一入口：先查缓存（只命中确定性条目），未命中实时求解并回写。
    origin 透传给 cache.put（预生成走 'pregen'）。返回 (res, reasons, meta)。
    no_cache=True（拆台模式 / 刁难卡）：不读也不写缓存，强制现场实时求解——既不拿预存答案
    充数，也不让现场结果覆盖预生成条目（键算法与已有条目原样不动）；meta 带 no_cache=True。"""
    cache = cache if cache is not None else PlanCache()
    if not avoid and not no_cache:
        ent = cache.get(req)
        if ent:
            return ent['res'], ent['reasons'], dict(hit=True, elapsed=0.0, key=req_key(req))
    t0 = time.time()
    res = core.recommend(bundle, req, avoid=avoid)
    reasons = nl_agent.explain(req, res, llm=llm)
    el = round(time.time() - t0, 2)
    res = jsonable(res)
    if not avoid and not no_cache:
        cache.put(req, res, reasons, origin=origin)
    meta = dict(hit=False, elapsed=el, key=req_key(req))
    if no_cache:
        meta['no_cache'] = True
    return res, reasons, meta
