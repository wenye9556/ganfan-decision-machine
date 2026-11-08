# -*- coding: utf-8 -*-
"""test_nl.py —— NL 规则解析回归电池（≥25 句）：
覆盖 ①忌口裸词/并列/遮蔽（不吃牛和羊、不吃猪和牛、不吃牛奶、奶茶类边界）
     ②预算语境（¥/块/元/块钱/预算N/N以内；裸数字不算：减脂第2周了/想吃3个菜/3楼食堂）
     ③中文数字预算（十五块/十八块五/十八块半/十八点五块/二十五元/一百块/一块鸡排量词防误判）
     ④口语钟点（早上/上午/中午/下午/傍晚/晚上/夜里/半夜/凌晨 X点(半|X分)→asof+时段推断）
     ⑤run_nl 原 3 句演示样例 ⑥辣度/懒人/锚点。
用法: python engine/test_nl.py   （断言全过输出 all green，退出码 0）"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nl_agent

# 默认期望值 = rule_parse 的兜底默认；每条用例给"期望覆盖项"，其余字段必须等于默认
# （防止误触发：如忌口/预算多抓）。B 允许 int/float 等值比较（18 == 18.0）。
DEFAULT = dict(scenario='均衡', B=20, period='午', asof='12:30', anchor='图书馆',
               spice_max=2, taboo=set(), lazy=False)

CASES = [
    # —— 原 run_nl 三句演示样例 ——
    ('减脂，18块，不吃猪', dict(scenario='减脂', B=18, taboo={'猪'})),
    ('中午在图书馆，想吃点便宜的，15块以内，不要太辣',
     dict(scenario='省钱', period='午', anchor='图书馆', B=15, spice_max=1)),
    ('晚上懒得走，想增肌，25块，不吃海鲜和香菜',
     dict(scenario='增肌', period='晚', asof='18:30', lazy=True, B=25, taboo={'海鲜', '香菜'})),
    # —— ① 忌口裸词/并列/遮蔽 ——
    ('不吃牛和羊', dict(taboo={'牛', '羊'})),
    ('不吃猪和牛', dict(taboo={'猪', '牛'})),
    ('我想吃牛肉面', dict(taboo=set())),                        # 无否定 → 不忌
    ('不吃牛奶', dict(taboo={'奶'})),                            # 牛奶≠牛肉：忌奶不忌牛
    ('我对牛奶过敏', dict(taboo={'奶'})),
    ('想喝奶茶，15块以内', dict(B=15, taboo=set())),             # 奶茶类边界：不触发忌口
    ('来杯奶茶吧', dict(taboo=set(), B=20)),
    ('不吃香菜和内脏', dict(taboo={'香菜', '内脏'})),
    ('不吃猪杂', dict(taboo={'猪', '内脏'})),                    # 猪杂既是猪肉也是内脏
    ('忌口海鲜', dict(taboo={'海鲜'})),
    # —— ② 预算必须有语境：裸数字不算 ——
    ('减脂第2周了，中午吃点清淡的', dict(scenario='减脂', period='午')),
    ('想吃3个菜，20块以内', dict(B=20)),
    ('3楼食堂有什么好吃的', dict()),
    ('今天吃顿好的，33', dict()),                                # 裸数字不算预算 → 默认20
    # —— ③ 预算语境变体 ——
    ('18块', dict(B=18)),
    ('18元吃午饭', dict(B=18, period='午')),
    ('18块钱以内', dict(B=18)),
    ('¥18解决一顿', dict(B=18)),
    ('预算18', dict(B=18)),
    ('最多花25', dict(B=25)),
    # —— ③' 中文数字预算（1–199 + 块五/块半） ——
    ('十五块以内有什么推荐', dict(B=15)),
    ('预算二十块', dict(B=20)),
    ('十八块五能吃什么', dict(B=18.5)),
    ('十八块半行不行', dict(B=18.5)),
    ('十八点五块吃顿好的', dict(B=18.5)),
    ('二十五元以内', dict(B=25)),
    ('一百块吃顿好的', dict(B=100)),
    ('一块鸡排解解馋', dict()),                                  # 量词"块"≠钱 → 默认20
    ('两块牛排就行', dict(taboo=set())),                         # 量词防误判，且不忌牛
    # —— ④ 口语钟点 → asof + 时段推断 ——
    ('下午2点半去吃', dict(period='下午', asof='14:30')),
    ('晚上8点吃夜宵', dict(period='夜宵', asof='20:00')),
    ('中午12点半图书馆见', dict(period='午', asof='12:30', anchor='图书馆')),
    ('上午11点下课去吃饭', dict(period='午', asof='11:00')),     # 无时段词 → 按钟点归段
    ('中午1点在宿舍区吃', dict(period='午', asof='13:00', anchor='宿舍区')),
    ('早上7点吃早餐', dict(period='早', asof='07:00')),
    ('傍晚6点吃饭', dict(period='晚', asof='18:00')),
    ('凌晨1点还能吃到什么', dict(period='夜宵', asof='01:00')),  # 跨午夜就近归夜宵
    ('晚上12点饿了', dict(period='晚', asof='23:59')),           # 午夜口径
    ('夜里11点半叫外卖', dict(period='夜宵', asof='23:30')),    # 就近锚点 21:30 → 夜宵
    ('没说时间随便吃', dict(period='午', asof='12:30')),         # 没说钟点 → 行为不变
    # —— ⑤ 辣度/懒人/锚点 ——
    ('不能吃辣，来点清淡的', dict(spice_max=0, scenario='均衡')),
    ('微辣就好', dict(spice_max=1)),
    ('赶时间，就近吃个午饭', dict(lazy=True, period='午')),
    ('从宿舍过来，随便吃点', dict(anchor='宿舍区', scenario='均衡')),
    # —— ⑤' 辣度否定词表补充（不吃辣/怕辣/吃不了辣→0；勿与「能吃辣」冲突） ——
    ('不吃辣，来点清淡的', dict(spice_max=0)),
    ('我怕辣', dict(spice_max=0)),
    ('吃不了辣', dict(spice_max=0)),
    ('我能吃辣，越辣越好', dict(spice_max=2)),               # 肯定式不误伤
    # —— ⑤'' 饮食模式短语 → 忌口闭集（吃素/不吃肉/清真/穆斯林/乳糖不耐） ——
    ('我吃素，18块以内', dict(taboo={'猪', '牛', '羊'}, B=18)),
    ('不吃肉', dict(taboo={'猪', '牛', '羊'})),
    ('不吃素，就想吃肉', dict(taboo=set())),                 # 否定式不触发素食
    ('清真餐，15块', dict(taboo={'猪', '牛', '羊', '内脏'}, B=15)),
    ('我是穆斯林', dict(taboo={'猪', '牛', '羊', '内脏'})),
    ('我乳糖不耐', dict(taboo={'奶'})),
    # —— ③'' 预算前缀吞字修复（\D 不再吃中文数字首字：二十/十八/十五完整捕获） ——
    ('预算二十', dict(B=20)),
    ('不超过十八', dict(B=18)),
    ('最多十五', dict(B=15)),
    # —— 主演示句：不吃香菜 ——
    ('减脂，18块，不吃香菜', dict(scenario='减脂', B=18, taboo={'香菜'})),
]


def run():
    passed = failed = 0
    for text, want_over in CASES:
        req = nl_agent.rule_parse(text)
        want = dict(DEFAULT)
        want.update(want_over)
        errs = []
        for k in DEFAULT:
            got, exp = req[k], want[k]
            if k == 'B':
                okv = abs(float(got) - float(exp)) < 1e-9
            elif k == 'taboo':
                okv = set(got) == set(exp)
            else:
                okv = got == exp
            if not okv:
                errs.append(f'{k}: got {got!r} want {exp!r}')
        if errs:
            failed += 1
            print(f'[FAIL] "{text}"')
            for e in errs:
                print('       ', e)
        else:
            passed += 1
    # sanitize 闭环：规则解析结果过闭集校验字段不丢
    r = nl_agent.sanitize(nl_agent.rule_parse('减脂，18块，不吃猪，晚上7点半，微辣，赶时间'))
    assert r['scenario'] == '减脂' and r['B'] == 18 and r['taboo'] == {'猪'} \
        and r['period'] == '晚' and r['asof'] == '19:30' and r['spice_max'] == 1 and r['lazy'], r
    passed += 1
    print(f'NL 回归电池: {passed} 全过 ✓ / {failed} 失败（共 {len(CASES) + 1} 例）')
    return failed


if __name__ == '__main__':
    sys.exit(1 if run() else 0)
