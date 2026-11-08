# -*- coding: utf-8 -*-
"""合并子agent打标结果 → 标准菜名表 + 克重回填 + 麻辣香锅池中央打标 + 引擎冒烟测试
前置：tag_out_1..5.json 由5个子agent产出
"""
import json
import openpyxl

MASTER = '干饭决策机_数据采集_主表.xlsx'

# 组件库（与 tag_rules.md 完全一致）
LIB = {
 '米饭': (116, 2.6), '煮面条': (140, 4.0), '煮米粉': (120, 2.5), '凉皮': (117, 3.3),
 '馄饨': (230, 8.0), '烙饼火烧馍': (260, 8.0), '葱油饼': (280, 7.0),
 '鸡腿肉': (215, 27), '鸡胸肉': (165, 25), '炸鸡排': (235, 16), '鸭腿卤': (225, 21),
 '卤鸭': (234, 14.5), '烤猪肉': (208, 28), '叉烧': (279, 23.8), '红烧肉': (380, 12),
 '卤猪蹄': (260, 20), '酱牛肉': (246, 31.4), '炖牛肉': (145, 20), '牛腩炖': (225, 18),
 '肥牛': (280, 17), '牛杂': (175, 17), '牛肉丸': (218, 14), '包心鱼丸': (168, 11),
 '狮子头': (235, 12), '茶叶蛋': (141, 13.5), '卤蛋': (132, 12), '煎蛋': (170, 12),
 '火腿肠': (212, 14), '广式香肠': (500, 13), '卤肥肠': (280, 13), '鸭血': (108, 13.6),
 '鸭胗': (125, 18.5), '凤爪': (235, 19), '羊肉串': (250, 18), '鸡肉串': (230, 20),
 '豆腐串': (225, 17),
 '青菜': (20, 1.5), '酸笋': (25, 1.5), '土豆丝': (136, 2.5), '腐竹': (194, 18),
 '海带结': (30, 1.8), '面筋': (141, 23.5), '鸡蛋面皮': (280, 9), '沙拉酱': (330, 1),
 '芝士': (350, 25), '咖喱酱': (150, 3), '骨汤': (40, 2), '牛肉汤': (55, 4),
 '清汤': (30, 1), '糖醋汁': (180, 0), '辣油': (900, 0), '米饭配料菜': (60, 2),
 '杂酱肉末': (260, 12), '擂椒酱': (90, 1), '谷物饭': (130, 3), '意面': (150, 5),
 '米饭配料菜 ': (60, 2),
 # 麻辣香锅池补充组件
 '土豆片': (136, 2.5), '莲藕片': (120, 2.0), '金针菇': (40, 2.5), '木耳': (45, 1.5),
 '宽粉': (110, 1.0), '方便面饼': (420, 8.0), '午餐肉': (260, 12), '培根': (400, 15),
 '鹌鹑蛋': (150, 12),
}
TABOO_SET = {'猪','牛','羊','海鲜','蛋','奶','花生','芝麻','麸质','香菜','内脏'}
COOKS = {'清蒸水煮','凉拌','少油炒','正常炒','爆炒过油','干煸','油炸'}
ABSORB = {'弱','中','强'}
CONFS = {'公示级','计算级','估算级'}
TASTES = {'甜','咸','酸','鲜','清淡'}

# ---- 麻辣香锅池中央打标（20项） ----
HOTPOT = {
 '肥牛卷': ([0,1,0,0], '牛', '爆炒过油', '中', [['肥牛',100]], '咸'),
 '午餐肉': ([0,1,0,0], '猪', '爆炒过油', '中', [['午餐肉',100]], '咸'),
 '牛肉丸': ([0,1,0,0], '牛', '爆炒过油', '中', [['牛肉丸',100]], '咸'),
 '包心鱼丸': ([0,1,0,0], '海鲜', '爆炒过油', '中', [['包心鱼丸',100]], '鲜'),
 '鹌鹑蛋': ([0,1,0,0], '蛋', '爆炒过油', '中', [['鹌鹑蛋',100]], '清淡'),
 '鸭血': ([0,1,0,0], '内脏', '爆炒过油', '中', [['鸭血',100]], '咸'),
 '鸭胗': ([0,1,0,0], '内脏', '爆炒过油', '中', [['鸭胗',100]], '咸'),
 '鸡腿肉': ([0,1,0,0], None, '爆炒过油', '中', [['鸡腿肉',100]], '咸'),
 '广式香肠': ([0,1,0,0], '猪', '爆炒过油', '中', [['广式香肠',100]], '甜'),
 '培根': ([0,1,0,0], '猪', '爆炒过油', '中', [['培根',100]], '咸'),
 '土豆片': ([0,0,1,0], None, '爆炒过油', '强', [['土豆片',100]], '清淡'),
 '莲藕片': ([0,0,1,0], None, '爆炒过油', '中', [['莲藕片',100]], '清淡'),
 '海带结': ([0,0,1,0], None, '爆炒过油', '弱', [['海带结',100]], '鲜'),
 '豆泡': ([0,0,1,0], None, '爆炒过油', '强', [['豆腐串',100]], '清淡'),
 '腐竹': ([0,0,1,0], None, '爆炒过油', '强', [['腐竹',100]], '清淡'),
 '青菜': ([0,0,1,0], None, '爆炒过油', '弱', [['青菜',100]], '清淡'),
 '金针菇': ([0,0,1,0], None, '爆炒过油', '弱', [['金针菇',100]], '鲜'),
 '木耳': ([0,0,1,0], None, '爆炒过油', '弱', [['木耳',100]], '清淡'),
 '宽粉': ([1,0,0,0], None, '爆炒过油', '中', [['宽粉',100]], '清淡'),
 '方便面饼': ([1,0,0,0], '麸质', '爆炒过油', '中', [['方便面饼',100]], '咸'),
}
HOTPOT_GRAM = {'荤菜': 90, '素菜': 90, '主食': 80}

def hotpot_std():
    out = {}
    for name, (slots, taboo, cook, absorb, recipe, taste) in HOTPOT.items():
        kcal = sum(LIB[c][0] * p / 100 for c, p in recipe)
        prot = sum(LIB[c][1] * p / 100 for c, p in recipe)
        out[name] = dict(name=name, slots=slots, taboo=taboo or '—', cook=cook, absorb=absorb,
                         recipe=recipe, conf='估算级', taste=taste,
                         est_gram=90, cat='素菜' if slots[2] else ('主食' if slots[0] else '荤菜'),
                         kcal100=round(kcal, 1), prot100=round(prot, 1))
    return out

def main():
    tagged = {}
    problems = []
    for i in range(1, 6):
        arr = json.load(open(f'engine/tag_out_{i}.json', encoding='utf-8'))
        for x in arr:
            n = x['name']
            if n in tagged:
                continue  # 跨片同名（如粤式池=大众餐）取首个
            # ---- 校验 ----
            if x['cook'] not in COOKS: problems.append(f'{n}: 烹饪 {x["cook"]}')
            if x['absorb'] not in ABSORB: problems.append(f'{n}: 吸油 {x["absorb"]}')
            if x['conf'] not in CONFS: problems.append(f'{n}: 置信 {x["conf"]}')
            if x['taste'] not in TASTES: problems.append(f'{n}: 口味 {x["taste"]} → 咸')
            tb = str(x['taboo']).strip()
            if tb not in ('—', ''):
                bad = {t for t in tb.split(',') if t.strip()} - TABOO_SET
                if bad: problems.append(f'{n}: 忌口越界 {bad}')
            slots = x['slots']
            assert len(slots) == 4 and all(s in (0, 1) for s in slots), f'{n} 槽位非法'
            if x['conf'] == '公示级' and sum(slots) < 2:
                problems.append(f'{n}: 公示级须多槽')
            # ---- 计算 kcal/prot ----
            if x.get('kcal100_override') is not None:
                kcal, prot = float(x['kcal100_override']), float(x.get('prot100_override') or 0)
            else:
                kcal = prot = 0.0
                tot = sum(p for _, p in x['recipe'])
                for comp, p in x['recipe']:
                    if comp in LIB:
                        k, pr = LIB[comp]
                    elif comp.startswith('新组件:'):
                        kv, pv = comp[4:].split(','); k, pr = float(kv), float(pv)
                    else:
                        problems.append(f'{n}: 未知组件 {comp}'); k, pr = 0, 0
                    kcal += k * p / tot; prot += pr * p / tot
            if not (10 <= kcal <= 900):
                problems.append(f'{n}: kcal100={kcal:.0f} 越界(钳制)')
                kcal = min(max(kcal, 12.0), 880.0)
            x['kcal100'] = round(kcal, 1); x['prot100'] = round(prot, 1)
            tagged[n] = x
    # 麻辣香锅池并入
    for n, x in hotpot_std().items():
        tagged.setdefault(n, x)
    print(f'打标合并: {len(tagged)} 唯一名; 问题 {len(problems)} 条')
    for p in problems[:25]: print('  [!]', p)
    return tagged, problems

if __name__ == '__main__':
    main()
