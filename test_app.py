# -*- coding: utf-8 -*-
"""test_app.py —— UI 全流程冒烟 + 三态入口 / 滑动快选条 / 无解重试 / 关于披露回归
覆盖：首屏 → NL输入出Top3 → 同句二连击确定性重解 → 打卡周报 → 随机明示轮换
      → 再换一批换新 → 快选条辣度生效 / NL 回填点亮快选条 → 无解页一键重试 → 关于页披露。
跑前自动备份 data/checkins.json 与 cache/plans.json 到系统临时目录，跑完恢复
（cache 恢复为 pregen 的 51 条确定性条目，测试写入的 rand:/solve 条目全部清掉）。
用法: python test_app.py
"""
import json
import os
import random
import shutil
import sys
import tempfile

from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engine'))
import app_helpers as H
import core as _core

# ---- 测试替身：稳定化随机采样 --------------------------------------------------
# AppTest 的元素树无法表达「换一批后方案数变少」的中间态：换一批成功路径会
# clear_cheats + st.rerun，若新一批不足 3 套，残留的旧 cheat_* 复选框节点在下次
# run 收集 widget 状态时因键被弹掉而 KeyError（AppTest 工件，真实前端无此问题；
# 兜底自愈见 heal_stale_widgets）。这里给 core.random_recommend 包一层固定种子
# 轮询：优先给满 n 套且不与 exclude 重合；都失败则给套数最多的一批（保持
# 「宁可少给也不硬凑」语义可测）。
_orig_rr = _core.random_recommend


def _stable_random_recommend(bundle, req, n=3, seed=None, exclude=()):
    ex = {tuple(sorted(e)) for e in exclude}
    best = None
    for s in range(1, 41):
        r = _orig_rr(bundle, req, n=n, seed=s, exclude=exclude)
        sigs = {tuple(sorted(p['names'])) for p in r.get('top3', [])}
        if not (sigs & ex):
            if len(r.get('top3', [])) == n:
                return r
            if best is None or len(r.get('top3', [])) > len(best.get('top3', [])):
                best = r
    return best if best and best.get('top3') else _orig_rr(
        bundle, req, n=n, seed=None, exclude=exclude)


_core.random_recommend = _stable_random_recommend


def heal_stale_widgets(at):
    """把元素树里「键已被 clear_cheats 弹掉」的残留复选框节点，按节点 id 直接补回
    底层 widget-state 默认值（widget-id→user-key 映射已被剪枝，走用户键补不进去；
    _new_widget_state 存的是 WidgetState proto，裸 bool 会让下次 compact 崩溃）。
    纯测试侧自愈，不改变任何被测行为。"""
    try:                                              # 1.50 起 proto 模块名为复数 WidgetStates_pb2
        from streamlit.proto.WidgetStates_pb2 import WidgetState
    except ImportError:
        from streamlit.proto.WidgetState_pb2 import WidgetState
    ss = at.session_state._state

    def walk(n):
        if getattr(n, 'type', None) == 'checkbox' and getattr(n, 'key', None):
            try:
                at.session_state[n.key]
            except KeyError:
                ws = WidgetState()
                ws.id = n.id
                ws.bool_value = False
                ss._new_widget_state[n.id] = ws
        for c in (getattr(n, 'children', None) or {}).values():
            walk(c)

    walk(at._tree)

ROOT = os.path.dirname(os.path.abspath(__file__))
CHECKINS = os.path.join(ROOT, 'data', 'checkins.json')
PLANS = os.path.join(ROOT, 'cache', 'plans.json')
# 无解句：夜宵 23:55 + 全忌口 + 预算3元 + 不辣 → 过滤后无菜（top3=0）
INFEASIBLE_NL = '夜宵23点55分吃，不吃猪、牛、羊、海鲜、蛋、奶、花生、芝麻、麸质、香菜、内脏，预算3元，不辣'


def click_button(at, label):
    """按按钮文案点击（UI 增删按钮不影响测试）。"""
    for b in at.button:
        if label in b.label:
            b.click()
            return
    raise AssertionError(f'按钮不存在: {label}')


def has_button(at, label):
    return any(label in b.label for b in at.button)


def sget(at, key, default=None):
    """AppTest 的 session_state 代理没有 .get，用下标取。"""
    try:
        return at.session_state[key]
    except KeyError:
        return default


def top3_sigs(at):
    return tuple(str(p['sig']) for p in at.session_state.res['top3'])


def backup():
    tmpdir = tempfile.mkdtemp(prefix='ganfan_test_backup_')
    saved = {}
    for p in (CHECKINS, PLANS):
        if os.path.exists(p):
            dst = os.path.join(tmpdir, os.path.basename(p))
            shutil.copy2(p, dst)
            saved[p] = dst
    return saved


def restore(saved):
    for p, dst in saved.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        shutil.copy2(dst, p)


def run_checks():
    # 固定全局随机种子：随机抽卡条件 / 换一批采样 / 无种子兜底全部确定化，
    # 消除「相邻随机条件恰好撞车 → 换一批无新方案」这类偶发翻转（断言不变）。
    random.seed(20261108)
    at = AppTest.from_file('app.py', default_timeout=300)
    at.run()
    assert not at.exception, f'首屏异常: {at.exception}'
    print('首屏加载 ✓')

    # ---- NL 首解：减脂18忌猪 ----
    at.text_input[0].set_value('减脂，18块，不吃猪')
    at.run()
    assert any('一键配饭' in b.label for b in at.button), '主按钮应为「一键配饭」'
    click_button(at, '🍽️ 一键配饭')
    at.run()
    assert not at.exception, f'NL推荐异常: {at.exception}'
    res = at.session_state.res
    assert res and len(res['top3']) == 3, 'Top3 未产出'
    assert not sget(at, 'rand_note'), 'NL 路径不应有随机条件明示'
    first_sigs = top3_sigs(at)
    # 数字精简：结果区 meta 主视觉只留「N 道菜符合你的条件」，实现细节收纳进 ⓘ 悬停（title 属性）
    md_now = ''.join(m.value for m in at.markdown)
    meta_html = next(m.value for m in at.markdown if m.value.lstrip().startswith('<div class="solve-meta"'))
    import re as _re
    meta_body = _re.sub(r'title="[^"]*"', '', meta_html)      # title 悬停属性不算正文
    # hint 提示条里的「缓存命中秒出」是引导文案（非 meta 行），不在本断言范围
    assert '道菜符合你的条件' in meta_body, '主视觉应保留「N 道菜符合你的条件」一句'
    assert 'meta-info' in meta_html and 'ⓘ' in meta_html, '缓存命中/耗时应收纳为 ⓘ 小字（title 悬停）'
    assert '缓存命中' in meta_html or '实时求解' in meta_html, 'ⓘ 悬停里应带缓存命中/耗时细节'
    assert '缓存命中' not in meta_body and '实时求解' not in meta_body, 'meta 实现细节不应出现在正文'
    print('NL→Top3 ✓', [round(p['PI'], 2) for p in res['top3']], 'meta=', at.session_state.meta)

    # ---- 同句二连击：面板未脏 → 按上次解析条件确定性重解，结果一致、rand_note 为空 ----
    click_button(at, '🍽️ 一键配饭')
    at.run()
    assert not at.exception, f'同句二连击异常: {at.exception}'
    assert top3_sigs(at) == first_sigs, '同句二连击应与首解完全一致（确定性重解）'
    assert not sget(at, 'rand_note'), '同句二连击不应走随机（rand_note 须为空）'
    assert at.session_state.res['top3'][0]['sig'] == res['top3'][0]['sig']
    print('同句二连击 ✓ 与首解逐位一致，rand_note 为空，meta=', at.session_state.meta)

    # ---- 打卡 → 周报 ----
    at.session_state['cheat_0'] = True              # 顺手验证放纵餐勾选
    click_button(at, '✅ 打卡这餐')
    at.run()
    assert not at.exception, f'打卡异常: {at.exception}'
    logs = H.load_checkins()
    assert logs and logs[-1]['kind'] == '放纵', '打卡未写入或未按勾记放纵'
    s = H.week_stats(logs, {'减脂': (400, 650)})
    print(f'打卡→周报 ✓ N={s["n"]} 花费={s["cost"]} 配额剩余={s["cheat_left"]}')

    # ---- 新求解自动清空 cheat_* ----
    click_button(at, '🍽️ 一键配饭')
    at.run()
    assert all(f'cheat_{i}' not in at.session_state or not at.session_state[f'cheat_{i}']
               for i in range(3)), '新求解应清空 cheat_0/1/2 勾选'
    print('新求解清空放纵勾选 ✓')

    # ---- 快选条：拖辣度滑杆到「能吃辣」→ manual_dirty + 点求解 spice_max=2 生效 ----
    at.select_slider(key='spice').set_value(0)       # 先离开目标档，确保再拖到 2 会触发 on_change
    at.run()                                         # 注意：run 后元素树重建，须重新取元素再操作
    at.select_slider(key='spice').set_value(2)
    at.run()
    ss = at.session_state
    assert ss['spice'] == 2 and ss['manual_dirty'], '拖辣度到「能吃辣」应标记 manual_dirty'
    click_button(at, '🍽️ 一键配饭')
    at.run()
    assert not at.exception, f'快选求解异常: {at.exception}'
    assert at.session_state.req['spice_max'] == 2, '快选辣度「能吃辣」应进入求解条件（spice_max=2）'
    assert not sget(at, 'rand_note'), '碰过快选条后点按钮不应走随机'
    assert at.session_state.res['top3'], '快选条件应配出方案'
    print('快选辣度生效 ✓ req.spice_max=', at.session_state.req['spice_max'])

    # ---- NL 输入「减脂，18块，不吃香菜」→ 解析并回填点亮快选条 ----
    at.text_input[0].set_value('减脂，18块，不吃香菜')
    at.run()
    click_button(at, '🍽️ 一键配饭')
    at.run()
    assert not at.exception, f'NL回填快选条异常: {at.exception}'
    ss = at.session_state
    assert ss['scen'] == '减脂', 'NL 场景应回填快选场景滑杆'
    assert ss['budget'] == 18, 'NL 预算应回填快选预算滑杆'
    assert ss['taboo_香菜'] is True, 'NL 忌口应点亮香菜 chip'
    assert not ss['manual_dirty'], 'NL 回填不算手动配置'
    assert ss['res']['top3'], 'NL 回填后应出结果'
    print('NL 回填快选条 ✓', dict(scen=ss['scen'], budget=ss['budget'], 香菜chip=ss['taboo_香菜']))

    # ---- 无解页：0 套 → 一键改条件重试按钮 ----
    at.text_input[0].set_value(INFEASIBLE_NL)
    at.run()
    click_button(at, '🍽️ 一键配饭')
    at.run()
    assert not at.exception, f'无解路径异常: {at.exception}'
    assert at.session_state.res is not None and not at.session_state.res['top3'], '应配不出（0 套）'
    assert has_button(at, '预算 +3 元重试'), '无解页应有「预算 +3 元重试」按钮'
    assert has_button(at, '去掉忌口重试'), '无解页应有「去掉忌口重试」按钮'
    print('无解页重试按钮 ✓ B=', at.session_state.req['B'], '忌口', len(at.session_state.req['taboo']), '项')

    click_button(at, '💰 预算 +3 元重试')
    at.run()
    assert not at.exception, f'预算重试异常: {at.exception}'
    assert at.session_state.req['B'] == 6, '预算 +3 重试后 B 应为 6'
    assert at.session_state.budget == 10 and at.session_state.manual_dirty, \
        '重试应回填预算（快选滑杆 10–30，出界以边界 10 显示）并标记条件动过'
    assert not at.session_state.res['top3'], '该极端条件重试后仍配不出（诚实告知）'
    print('预算+3重试 ✓ 条件与面板同步更新（仍无解则再次诚实告知）')

    # ---- 随机配：空输入 + 面板未脏 → 随机抽条件并明示；连点 3 次各不相同 ----
    at.text_input[0].set_value('')
    at.run()
    ss = at.session_state
    ss['manual_dirty'] = False                      # 还原「面板未脏」，隔离随机路径
    for k, v in dict(period='午 餐', asof='12:30', anchor='图书馆').items():
        ss[k] = v                                   # 事实类字段回到常规午餐语境（极端夜宵语境下随机也无菜可抽）
    sigs = []
    for i in range(3):
        click_button(at, '🍽️ 一键配饭')
        at.run()
        assert not at.exception, f'随机配异常: {at.exception}'
        res = at.session_state.res
        assert res and res['top3'], f'随机配第{i+1}次未产出方案'
        assert sget(at, 'rand_note'), '随机配应明示随机条件'
        sigs.append(tuple(str(p['sig']) for p in res['top3']))
        assert all(f'cheat_{j}' not in at.session_state or not at.session_state[f'cheat_{j}']
                   for j in range(3)), '随机新解应清空放纵勾选'
    for a, b in zip(sigs, sigs[1:]):
        assert a != b, '相邻两次随机配给出了相同方案'
    print('随机配轮换 ✓ 相邻两次各不相同（连点 3 次）+ 随机条件明示')

    # ---- 再换一批：随机重挑三套，结果必须不同 + 清空放纵勾选 ----
    at.session_state['cheat_1'] = True
    before = tuple(str(p['sig']) for p in at.session_state.res['top3'])
    click_button(at, '再换一批')
    at.run()
    assert not at.exception, f'换一批异常: {at.exception}'
    after = tuple(str(p['sig']) for p in at.session_state.res['top3'])
    assert after and after != before, '换一批后方案应不同'
    assert all(f'cheat_{j}' not in at.session_state or not at.session_state[f'cheat_{j}']
               for j in range(3)), '换一批应清空放纵勾选'
    print('再换一批 ✓ 三套已换新 + 放纵勾选已清')

    # ---- 关于页：三条诚实披露 ----
    # 「再换一批」成功路径带 st.rerun：AppTest 元素树可能残留旧一批方案卡上已被
    # clear_cheats 弹掉键的 cheat_* 复选框节点（新一批方案数变少时），下次 run 收集
    # widget 状态会 KeyError —— 先按树节点自愈补值（见 heal_stale_widgets 注释）。
    heal_stale_widgets(at)
    at.run()
    md = ''.join(m.value for m in at.markdown)
    assert '+150kcal 宽容带' in md, '关于页应披露周报 +150kcal 宽容带'
    assert '候选池内的相对位置' in md and '跨条件不可直接比较' in md, '关于页应披露三维分数口径'
    assert '规则模板' in md and '大模型' in md, '关于页应披露解释生成链路'
    assert '满分 100' in md, '三维条形应带「满分 100」小注'
    print('关于页披露 ✓（宽容带 / 三维口径 / 解释链路 / 满分100）')

    # ---- chips 中文化（解析来源不再出现 rule/llm 英文）----
    assert 'rule 解析' not in md and 'llm 解析' not in md, '解析来源应显示中文（规则解析/大模型解析）'
    print('界面中文化 ✓')


def main():
    saved = backup()
    print(f'已备份 {len(saved)} 个状态文件到系统临时目录，测试结束自动恢复')
    try:
        run_checks()
    finally:
        restore(saved)
        # 双保险：cache 里只允许 pregen 条目（清掉测试写入的 rand:/solve 条目）
        if os.path.exists(PLANS):
            data = json.load(open(PLANS, encoding='utf-8'))
            stray = [k for k, v in data.items()
                     if v.get('origin', 'solve') != 'pregen' or k.startswith('rand:')]
            for k in stray:
                data.pop(k, None)
            if stray:
                json.dump(data, open(PLANS, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'cache 清理 ✓ pregen {sum(1 for v in data.values() if v.get("origin") == "pregen")} 条，'
                  f'清掉测试残留 {len(stray)} 条')
        print('状态已恢复（checkins / cache）')
    print('UI 全流程冒烟通过 ✓')


if __name__ == '__main__':
    main()
