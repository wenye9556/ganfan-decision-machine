# -*- coding: utf-8 -*-
"""test_app.py —— UI 全流程冒烟 + 三态入口 / 快捷按钮 / 无解重试 / 关于披露回归
覆盖：首屏 → NL输入出Top3 → 同句二连击确定性重解 → 打卡周报 → 随机明示轮换
      → 再换一批换新 → 快捷按钮回填面板 → 无解页一键重试 → 关于页披露。
跑前自动备份 data/checkins.json 与 cache/plans.json 到系统临时目录，跑完恢复
（cache 恢复为 pregen 的 51 条确定性条目，测试写入的 rand:/solve 条目全部清掉）。
用法: python test_app.py
"""
import json
import os
import shutil
import sys
import tempfile

from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app_helpers as H

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

    # ---- 快捷按钮：回填面板 widgets + manual_dirty ----
    click_button(at, '🪙 省钱15微辣')
    at.run()
    assert not at.exception, f'快捷按钮异常: {at.exception}'
    ss = at.session_state
    assert (ss['scen'], ss['budget'], ss['spice']) == ('省钱', 15, 1), '快捷按钮未回填场景/预算/辣度'
    assert (ss['period'], ss['asof'], ss['anchor'], ss['taboo'], ss['lazy']) == \
        ('午 餐', '12:00', '教学楼', [], False), '快捷按钮未回填时段/时间/锚点/忌口'
    assert ss['manual_dirty'] is True, '快捷按钮应标记 manual_dirty'
    assert ss['req']['scenario'] == '省钱' and ss['res']['top3'], '快捷按钮应出结果且与面板一致'
    assert all(f'cheat_{i}' not in ss or not ss[f'cheat_{i}'] for i in range(3)), '快捷按钮应清空放纵勾选'
    print('快捷按钮回填面板 ✓', {k: ss[k] for k in ('scen', 'budget', 'spice', 'anchor', 'asof')})

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
    assert at.session_state.budget == 6 and at.session_state.manual_dirty, '重试应回填预算并标记面板'
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
