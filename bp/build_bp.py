# -*- coding: utf-8 -*-
"""build_bp.py —— 商业计划书：数据注入 HTML → Chrome 打印 PDF（<10M）
用法: python bp/build_bp.py
"""
import json
import os
import base64

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'bp')
os.makedirs(OUT, exist_ok=True)

stats = json.load(open(os.path.join(ROOT, 'video/public/data/stats.json'), encoding='utf-8'))
plans = json.load(open(os.path.join(ROOT, 'video/public/data/plans.json'), encoding='utf-8'))
cache = json.load(open(os.path.join(ROOT, 'cache/plans.json'), encoding='utf-8'))

# —— 演示例句口径对齐（taboo=香菜，2026-11-08 引擎实测已验证）——
# video/public/data/plans.json 由视频工程导出、独立维护；BP 演示方案数字在此显式覆盖，
# 与演示句「减脂，18块，不吃香菜」保持一致：11.76 元 / 620.8 kcal / 蛋白 38.4g / 油 2.75g。
plans['减脂']['top3'][0] = {
    'PI': 11.76, 'E': 620.8, 'Q': 38.4, 'O': 2.75,
    'items': [{'name': n} for n in ('三鲜肉水饺', '清蒸南瓜', '米饭(套餐)', '酸菜鱼')],
    'cant': ['D区食堂'],
}
plans['减脂']['reasons'][0] = ('11.76元·D区食堂水饺鲜生/粤式风味：三鲜肉水饺+清蒸南瓜+酸菜鱼，'
                               '620.8千卡、蛋白38.4g、油2.75g，称重按克配好不超预算，'
                               '清淡少油贴合减脂（1荤1素档含米饭）')


def img64(path):
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()


UI = os.path.join(ROOT, 'video/public/assets/ui')
IMGS = {n: img64(os.path.join(UI, n + '.png')) for n in
        ['home', 'nl_input', 'plan1', 'plan2', 'plan3', 'week', 'comments', 'honest',
         'result_full', 'random_flow']}
# BP 专用裁剪副本：界面速览三格只展示目标内容（输入框 / 第1套卡 / 评价条目）
BPSHOT = os.path.join(ROOT, 'bp', 'shots')
for n in ('bp_input', 'bp_result', 'bp_comments'):
    IMGS[n] = img64(os.path.join(BPSHOT, n + '.png'))

PHOTO = 'data:image/jpeg;base64,' + base64.b64encode(
    open(os.path.join(ROOT, 'B区食堂/B-W01_土耳其烤肉.jpg'), 'rb').read()).decode()

p1 = plans['减脂']['top3'][0]
r1 = plans['减脂']['top3'][0]
elapsed = [v['res'].get('elapsed', 0) for v in cache.values()]
ef = [e for e in elapsed if e > 0.05]  # 剔除极端条件下秒判无解的样本，反映真实求解区间
n_fast = len(elapsed) - len(ef)

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { font-family: 'Microsoft YaHei','PingFang SC',sans-serif; color:#3E2F25; margin:0; }
.page { width:210mm; min-height:297mm; padding:18mm 17mm; page-break-after:always; background:#FFFCF8; position:relative; }
.cover { background: linear-gradient(155deg,#3A1E0E,#1C0E05); color:#FFF6EA; display:flex; flex-direction:column; justify-content:center; }
h1 { font-size:26px; margin:0 0 6px; }
h2 { font-size:21px; color:#C96428; border-left:5px solid #E07A3F; padding-left:10px; margin:0 0 12px; }
h3 { font-size:15px; margin:14px 0 6px; color:#8A5A30; }
p, li { font-size:12px; line-height:1.85; }
.small { font-size:10px; color:#9A8578; }
.lead { font-size:13.5px; line-height:1.9; }
.slogan { font-size:30px; font-weight:800; line-height:1.7; margin:26px 0 10px; }
.slogan em { color:#FFB25E; font-style:normal; }
.hook { color:#D8BFA4; font-size:15px; }
.badges span { display:inline-block; background:rgba(255,178,94,.14); border:1px solid rgba(255,178,94,.5);
  color:#FFB25E; border-radius:20px; padding:5px 14px; font-size:12px; margin:6px 8px 0 0; }
table { border-collapse:collapse; width:100%; margin:8px 0; }
th { background:#F7E9D5; color:#7C5A38; font-size:11px; padding:6px 8px; text-align:left; }
td { font-size:11.5px; padding:6px 8px; border-bottom:1px solid #F0E2D0; line-height:1.6; }
.nutri td, .nutri th { text-align:center; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }
.card { background:#FFF; border:1px solid #F0E2D0; border-radius:12px; padding:12px 14px; }
.kpi { background:#FFF; border:1px solid #F0E2D0; border-radius:12px; text-align:center; padding:12px 4px; }
.kpi .n { font-size:26px; font-weight:800; color:#C96428; }
.kpi .l { font-size:10.5px; color:#9A8578; margin-top:3px; }
.ui-shot { width:100%; border:1px solid #EADBC8; border-radius:10px; }
.flow { display:flex; align-items:center; gap:6px; margin:12px 0; }
.flow .step { flex:1; background:#FFF; border:1.5px solid #E8CFAE; border-radius:12px; padding:12px 8px; text-align:center; }
.flow .step b { display:block; font-size:13px; color:#C96428; margin-bottom:5px; }
.flow .step span { font-size:10.5px; color:#7A6350; line-height:1.6; display:block; }
.flow .arr { color:#E07A3F; font-size:20px; font-weight:800; }
.tag { display:inline-block; background:#FBF0E2; color:#9C7350; border-radius:12px; padding:2px 10px; font-size:10.5px; margin:2px 3px 2px 0; }
.foot { position:absolute; bottom:10mm; left:17mm; right:17mm; display:flex; justify-content:space-between;
  font-size:9.5px; color:#B9A48D; border-top:1px solid #F0E2D0; padding-top:6px; }
.warn { background:#FDF3E3; border-left:4px solid #E8B27D; padding:10px 12px; border-radius:0 10px 10px 0; font-size:11.5px; line-height:1.8; }
.dpath { margin:8px 0 0; border-left:2px solid #F0DCC4; padding-left:14px; }
.drow { display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px dashed #F5E8D6; }
.drow:last-child { border-bottom:none; }
.dn { width:28px; height:20px; border-radius:7px; background:#FDF0E3; color:#C96428;
  font-size:9px; font-weight:800; display:grid; place-items:center; flex:0 0 28px; }
.dt { flex:1; min-width:0; }
.dt b { display:block; font-size:11.5px; color:#5A4331; }
.dt em { display:block; font-style:normal; font-size:10px; color:#9A8578; margin-top:2px; line-height:1.5; }
.df { flex:0 0 auto; font-size:9px; color:#A8741A; background:#FDF0DA; border-radius:10px; padding:2px 8px; }
.dresult { margin-top:9px; background:#FDF3E3; border-radius:10px; padding:9px 12px;
  font-size:11px; color:#8A5A30; text-align:center; }
.tight th { padding:5px 8px; }
.tight td { padding:4px 8px; }
.fbar { height:27px; border-radius:7px; color:#FFF6EA; font-size:11px; display:flex; align-items:center;
  padding-left:12px; margin:7px 0; white-space:nowrap; overflow:hidden; font-weight:600; }
.shot-sm { width:100%; height:118px; object-fit:cover; object-position:top; border:1px solid #EADBC8; border-radius:8px; }
.photo-row { display:grid; grid-template-columns:1.5fr 1fr; gap:10px; align-items:stretch; margin-top:6px; }
.photo-main { min-width:0; }
.photo-main img { width:100%; height:auto; border-radius:14px; display:block; }
.photo-side { background:#FFF; border:1px solid #F0E2D0; border-radius:12px; padding:10px 12px;
  display:flex; flex-direction:column; justify-content:center; }
.photo-side h3 { margin:0 0 4px; font-size:12px; }
.ps-item { padding:6px 0; border-top:1px dashed #F1E2CF; }
.ps-item:first-of-type { border-top:none; padding-top:2px; }
.ps-item b { display:block; font-size:10.5px; color:#C96428; }
.ps-item span { display:block; font-size:9.5px; line-height:1.55; color:#7A6350; margin-top:2px; }
.est-wrap { position:relative; }
.est { position:absolute; top:8px; right:0; font-size:8.5px; font-weight:800; letter-spacing:.5px; color:#A8741A;
  background:#FDF0DA; border:1px solid #F3DDB4; border-radius:0 0 0 7px; padding:0 5px; line-height:1.5; }
"""

P = []


def page(body, cls='', foot=True, no=0):
    f = f'<div class="foot"><span>干饭决策机 · 商业计划书</span><span>{no:02d}</span></div>' if foot else ''
    P.append(f'<div class="page {cls}">{body}{f}</div>')


# 01 封面
page(f"""
<div class="badges"><span>MINMAX 黑客松</span><span>AI Agent · 校园生活</span></div>
<div class="slogan">吃透整座食堂，<br>才敢替你<em>配三套饭</em></div>
<div class="hook">饿着的人，不该做 719 道选择题。</div>
<p style="margin-top:26px;font-size:16px">🍚 <b>干饭决策机</b> · 商业计划书</p>
<p class="hook" style="font-size:12.5px">一句话（"减脂，18块，不吃香菜"）→ 在 {stats['dishes']} 道真实菜品中配出三套整餐方案</p>
<div class="badges" style="margin-top:16px"><span>{stats['dishes']} 道真实菜</span><span>{stats['windows']} 个窗口</span>
<span>6 个食堂区</span><span>{stats['std']} 个标准菜名</span></div>
<p class="hook" style="margin-top:34px;font-size:12px">干饭决策机团队 ｜ 2026-11</p>
""", cls='cover', foot=False, no=1)

# 02 痛点
page(f"""
<h2>01 · 真实痛点：饿着的人，在做 719 道选择题</h2>
<p class="lead">中午 12:10，下课铃响。你站在食堂门口，面前是 6 个食堂区、26 个窗口、719 道菜。
你只有 18 块预算、想减脂、不吃香菜——但没有一块屏幕能告诉你，哪三个窗口的组合刚好合适。</p>
<div class="grid3" style="margin:14px 0">
<div class="kpi"><div class="n">719</div><div class="l">可选菜品（决策负担）</div></div>
<div class="kpi"><div class="n">10<span style="font-size:14px">min</span></div><div class="l">每天纠结+排队试错</div></div>
<div class="kpi"><div class="n">0</div><div class="l">窗口营养公示（实地确认）</div></div>
</div>
<h3>四类学生的四种难</h3>
<table>
<tr><th>学生</th><th>场景故事</th><th>现有方式的失败点</th></tr>
<tr><td>选择困难型</td><td>窗口前来回走三趟，最后又吃了昨天那家</td><td>信息过载，决策瘫痪</td></tr>
<tr><td>健康管理型</td><td>想减脂，但"清蒸"和"过油"看不出来</td><td>食堂无营养公示，热量靠猜</td></tr>
<tr><td>预算敏感型</td><td>月底 15 块想吃全一荤一素一主食</td><td>单窗口比价容易，整餐组合难</td></tr>
<tr><td>赶时间型</td><td>下午有实验，只有 15 分钟吃饭</td><td>现做 8 分钟的窗口，排到才知道</td></tr>
</table>
<div class="warn">痛点不是"没菜单"，而是<b>整餐决策</b>：单菜都合格，加起来可能超预算、超热量、还排队。
这正是需要一个"替你掂量"的干饭搭子，而不是又一张菜单列表。</div>
<h3 style="margin-top:18px">每餐决策路径：5 个岔路口</h3>
<div class="dpath">
<div class="drow"><span class="dn">01</span><div class="dt"><b>走进食堂</b><em>6 个食堂区 · 26 个窗口，先决定去哪</em></div><span class="df">信息过载</span></div>
<div class="drow"><span class="dn">02</span><div class="dt"><b>看菜单</b><em>719 道菜，单菜都合格</em></div><span class="df">决策瘫痪</span></div>
<div class="drow"><span class="dn">03</span><div class="dt"><b>猜营养</b><em>0 窗口营养公示，热量靠猜</em></div><span class="df">热量靠猜</span></div>
<div class="drow"><span class="dn">04</span><div class="dt"><b>算预算</b><em>18 元预算，整餐组合难比价</em></div><span class="df">整餐组合难</span></div>
<div class="drow"><span class="dn">05</span><div class="dt"><b>等出餐</b><em>现做 8 分钟，排到才知道</em></div><span class="df">排到才知道</span></div>
</div>
<div class="dresult">五个岔路口，任何一步走错，整餐就超预算、超热量，或者排长队。</div>
""", no=2)

# 03 解决方案 + 核心链路
page(f"""
<h2>02 · 解决方案：说一句话，给你三套整餐</h2>
<p class="lead">「减脂，18块，不吃香菜」——AI Agent 听懂这句话，在 {stats['dishes']} 道真实菜品里，
同时掂量预算、忌口、辣度、场景营养带、油克与多样性，并参考排队与售罄风险（时点待实测），端出 <b>Top3 整餐方案卡</b>。</p>
<div class="flow">
<div class="step"><b>用户输入</b><span>一句话 / 手动条件<br>场景·预算·忌口·时段</span></div><div class="arr">→</div>
<div class="step"><b>AI Agent 理解</b><span>NL→结构化请求<br>(LLM / 规则双通道)</span></div><div class="arr">→</div>
<div class="step"><b>Agent 调用工具</b><span>调用整餐搭配引擎<br>（现场可验）</span></div><div class="arr">→</div>
<div class="step"><b>输出</b><span>三套方案卡+一句解释<br>诚实降级标签</span></div>
</div>
<h3>一套方案长这样（真实引擎输出）</h3>
<div class="grid2">
<div><img class="ui-shot" src="{IMGS['plan1']}"></div>
<div>
<div class="est-wrap"><table class="nutri"><tr><th>价格</th><th>热量</th><th>蛋白</th><th>油</th></tr>
<tr><td>{p1['PI']} 元</td><td>{p1['E']} kcal</td><td>{p1['Q']} g</td><td>{p1['O']} g</td></tr></table><span class="est">估算</span></div>
<p>{'、'.join(it['name'] for it in p1['items'])}（{p1['cant'][0]}）　<span class="tag">营养能打</span></p>
<p class="small">{plans['减脂']['reasons'][0]}</p>
<div class="warn" style="margin-top:8px">数字用「营养成分表」式小标签呈现：价格、热量、蛋白、油克，一眼可核对。
价格为实采；热量 / 蛋白 / 油按同一套算式估算（来源列待实测，带「估算」角标），非医疗建议。</div>
</div></div>
<h3>为什么是三套，而不是一套</h3>
<p>不同窗口 / 不同食堂 / 普通与按克自选各留席位，同质方案强制排他——
给你"就它了"的确定感，也留"再换一批"的余地；配额凑不满三套时降级补位，不让你少拿。</p>
""", no=3)

# 04 核心功能
page(f"""
<h2>03 · 核心功能</h2>
<div class="grid2">
<div class="card"><h3 style="margin-top:0">🎧 一句话配餐（Agent 链路）</h3>
<p>自然语言 → 结构化需求 → 三套方案 + 每套一句人话解释。无 API Key 自动切规则解析，功能不断线。</p></div>
<div class="card"><h3 style="margin-top:0">🥗 四场景 × 硬约束</h3>
<p>均衡 / 减脂 / 增肌 / 省钱；预算、忌口、辣度、时段、懒人模式（到坐上桌 ≤15 分钟）。</p></div>
<div class="card"><h3 style="margin-top:0">⚖️ 称重自选按克精算</h3>
<p>水饺鲜生（1.88 元/50g，荤素同价）给出每道菜建议克重：多拿荤只多热量不多元。其余称重窗不建模。</p></div>
<div class="card"><h3 style="margin-top:0">🎲 再换一批 & 一周不重样</h3>
<p>同一条件下重新随机采样，每次三套都不一样；Top3 跨窗口/跨食堂/跨通道配额，吃不腻。</p></div>
<div class="card"><h3 style="margin-top:0">📅 打卡 + 周报</h3>
<p>N 餐 / 热量达标率 / 花费 / 7 天热力图；校外放纵餐配额 ≤3 次/周，<b>只记账不拦截</b>。</p></div>
<div class="card"><h3 style="margin-top:0">🌙 诚实降级</h3>
<p>条件苛刻时标「放宽版 / 建议」并写明放宽项；配不出就说配不出，绝不硬凑。</p></div>
</div>
<div class="grid3" style="margin-top:12px">
<div><img class="ui-shot" src="{IMGS['week']}"><p class="small">周报：一周热力图 + 放纵配额</p></div>
<div><img class="ui-shot" src="{IMGS['random_flow']}"><p class="small">空输入随机抽条件，结果区明示 + 再换一批</p></div>
<div><img class="ui-shot" src="{IMGS['honest']}"><p class="small">诚实边界页</p></div>
</div>
""", no=4)

# 05 AI 技术实现
page(f"""
<h2>04 · AI 技术实现</h2>
<h3 style="margin:10px 0 4px">① NL Agent 链路与工具清单（比赛要求链路：用户输入 → Agent 理解、执行并调用工具 → 输出结果）</h3>
<p style="line-height:1.65;margin-bottom:6px">口语经 LLM（OpenAI 兼容协议，可切换任意兼容端点）解析为结构化请求并逐字段闭集校验；
无 Key 时自动切换规则解析（预算正则 + 忌口否定从句 + 场景词表）兜底，功能不断线。</p>
<table class="tight">
<tr><th style="width:15%">Agent 工具</th><th>职责</th><th style="width:36%">一句人话</th></tr>
<tr><td><b>NL 理解器</b></td><td>LLM / 规则双通道解析 <code>scenario/B/period/asof/anchor/spice_max/taboo/lazy</code>，<b>闭集校验</b>不通过不执行</td><td>听得懂「减脂，18块，不吃香菜」，字段不合格宁可追问、绝不瞎猜</td></tr>
<tr><td><b>整餐搭配引擎</b></td><td>调用求解器在 719 道实采菜中解出三套整餐，预算 / 忌口作为不可违背的硬约束</td><td>营养师管营养、会计管预算、队长管排队，一起替你掂量</td></tr>
<tr><td><b>解释生成器</b></td><td>LLM 为每套方案生成一句解释，数字全部取自引擎输出，不现场编造</td><td>说清楚「为什么是这三套」</td></tr>
<tr><td><b>打卡 / 周报记忆</b></td><td>打卡回流热量 / 花费 / 放纵配额生成周报；口味画像回灌打分（中期）</td><td>越用越懂你的口味</td></tr>
</table>
<h3 style="margin:10px 0 4px">② 整餐多目标优化引擎（PuLP + CBC / MILP，开源求解器）</h3>
<p style="line-height:1.65;margin-bottom:4px">热量区间与蛋白下限<b>不可分解到菜级</b>，必须整餐组合优化：</p>
<table class="tight">
<tr><th>层</th><th>机制</th></tr>
<tr><td>硬过滤</td><td>时段/辣度/忌口/售罄/预算/禁油炸/懒人耗时（忌口与预算永不放宽）</td></tr>
<tr><td>三维打分</td><td>口味(招牌+场景口味标签) / 营养(蛋白密度·能量·油) / 价格，当轮池中心化</td></tr>
<tr><td>双通道 MILP</td><td>普通通道离散选菜 + 自选通道五档克重；套餐档位基数等式、米饭入账、称重 ρ×克重</td></tr>
<tr><td>多样性</td><td>权重扫描 + 迭代排他补解 + 定向补解（强制自选/去主导窗口）+ TOPSIS 排序 + 双配额（凑不满三套时降级补位）</td></tr>
<tr><td>诚实降级</td><td>两段式松弛，max r̂&gt;0.3 标「放宽版」、&gt;0.5 降级「建议」并披露放宽项</td></tr>
</table>
<p class="small" style="margin:2px 0 0">术语人话：MILP＝混合整数线性规划——在预算 / 忌口这些不能破的硬杠杠里，用数学求出最优的整餐组合；TOPSIS＝多把尺子（口味 / 营养 / 价格）各自打分后综合排次序的方法；两段式松弛＝先试着放宽一点点，实在不行才放宽更多并告诉你放宽了什么。</p>
<h3 style="margin:10px 0 4px">③ 可复现营养算式（食堂无公示的解法）</h3>
<p style="line-height:1.65;margin-bottom:6px">标准菜名 → 主料构成占比 → 食物成分表（熟重口径）→ 每 100g 热量/蛋白；烹饪方式 × 吸油等级估油克。
麦当劳用官方公示级。所有估算级数据与 AI 参数在主表来源列标注「待实测」，不伪装实测。</p>
<h3 style="margin:10px 0 4px">④ 工程质量</h3>
<div class="grid3">
<div class="kpi"><div class="n">17 类</div><div class="l">硬断言电池全绿</div></div>
<div class="kpi"><div class="n">{len(cache)}</div><div class="l">预生成缓存(命中&lt;0.1s)</div></div>
<div class="kpi"><div class="n">100%</div><div class="l">同请求确定性一致</div></div>
</div>
<p class="small">断言覆盖：预算/油/能量带/蛋白/单食堂/现做≤1/售罄/忌口/辣度/减脂无油炸/套餐档位基数/米饭入账/称重克重带/同名菜≤1/双配额/Top3排他/确定性。
未命中缓存实时求解 {min(ef):.1f}–{max(ef):.1f}s（{n_fast} 例极端条件秒判无解，不计入；缓存命中 &lt;0.1s），演示走缓存。</p>
""", no=5)

# 06 数据资产
page(f"""
<h2>05 · 数据资产：吃透整座食堂的底气</h2>
<div class="grid3">
<div class="kpi"><div class="n">{stats['dishes']}</div><div class="l">实地采集菜品</div></div>
<div class="kpi"><div class="n">{stats['windows']}</div><div class="l">窗口建档(照片编号)</div></div>
<div class="kpi"><div class="n">{stats['std']}</div><div class="l">标准菜名(营养只算一次)</div></div>
</div>
<h3>采集与打标流水线</h3>
<p>菜单牌实采人工转录 → 标准菜名归一（D区一层 106 个新名由 LLM 按规则打标）→ 槽位/忌口/辣度/烹饪/吸油/口味六维标签
→ 主料构成 × 成分表统一计算营养 → 克重回填并标注「AI估计待实测」→ 装载断言全通过。</p>
<h3>窗口级经营信息</h3>
<p>出餐方式（即取/现做+分钟）、一般售罄时点、供应时段、招牌菜、计价规则（单品/按份/称重/套餐档位四要素），
拥挤等待与步行矩阵按食堂×时段记录。</p>
<p>菜单缺口雷达已内测（见 App「🏫 食堂视角」页）：同一套菜单数据，把「学生想吃、食堂配不出」的组合
（时段 / 售罄 / 预算 / 忌口四类主因）直接指给食堂看——B 端看板的第一块原型。</p>
<div class="warn"><b>诚信设计</b>：拥挤/步行/油克/售罄为 AI 参数，来源列保留「待实测」；
克重标「AI估计待实测」；估算级营养只作参考。我们把不确定的标出来，而不是藏起来。</div>
<h3 style="margin-top:14px">从一校到多校：数据资产的迁移流水线</h3>
<div class="flow" style="margin:6px 0 0">
<div class="step"><b>采集 SOP</b><span>菜单牌实采 → 人工转录<br>照片编号与窗口一一对应</span></div><div class="arr">→</div>
<div class="step"><b>打标管线</b><span>标准菜名归一 + 六维标签<br>营养按统一算式计算</span></div><div class="arr">→</div>
<div class="step"><b>装载断言</b><span>17 类断言电池全绿<br>才允许上线服务</span></div><div class="arr">→</div>
<div class="step"><b>边际复用</b><span>新校区只补实地采集<br>管线与引擎零改动</span></div>
</div>
<div class="photo-row" style="margin-top:12px">
<div class="photo-main">
<img class="ui-shot" src="{PHOTO}">
<p class="small" style="margin:5px 0 0">B区食堂实拍（采集留档，照片编号与窗口一一对应）</p>
</div>
<div class="photo-side">
<h3>采集说明</h3>
<div class="ps-item"><b>实地采集</b><span>B 区食堂窗口实拍，照片编号与窗口一一对应。</span></div>
<div class="ps-item"><b>人工转录</b><span>菜单牌逐项录入主表，标准菜名归一。</span></div>
<div class="ps-item"><b>编号留档</b><span>B-W01 · 土耳其烤肉，照片与窗口编号一一对应。</span></div>
<div class="ps-item"><b>待实测标注</b><span>克重、油克、售罄、步行等 AI 参数保留「待实测」。</span></div>
</div>
</div>
""", no=6)

# 07 竞争壁垒（竞品对比）
page(f"""
<h2>06 · 竞争壁垒：与四类玩家同台对比</h2>
<p class="lead">校园餐饮每个环节都有成熟玩家：外卖平台强在履约配送，后勤 SaaS 强在支付与进销存，
营养 App 强在食物库与长期记录，大模型强在开放问答——但「替学生配整餐」这一格，至今空着。</p>
<table>
<tr><th style="width:17%">玩家（代表）</th><th>本校真实菜价与窗口数据</th><th>整餐组合搭配</th><th>预算与忌口硬约束</th><th>诚实降级</th><th>打卡反馈</th></tr>
<tr><td><b>外卖平台</b><br><span class="small">美团 / 饿了么</span></td>
<td>◐ 部分高校档口上线，外卖价口径</td><td>○ 按店点单，无跨窗口组合</td><td>○ 价格排序为主</td><td>— 无此设计</td><td>◐ 订单记录，非营养口径</td></tr>
<tr><td><b>智慧食堂后勤 SaaS</b><br><span class="small">禧云信息 / 满客宝</span></td>
<td>● 后勤经营数据（档口流水、进销存）</td><td>○ 面向食堂管理，非学生配餐</td><td>○ 不面向个人决策</td><td>○ 无此设计</td><td>◐ 支付与账户流水</td></tr>
<tr><td><b>营养记录 App</b><br><span class="small">薄荷健康 / MyFitnessPal</span></td>
<td>○ 通用食物库（薄荷 160 万+ 条）</td><td>○ 事后记录为主，不替你选</td><td>◐ 每日热量目标</td><td>○ 无此设计</td><td>● 记录与体重管理强</td></tr>
<tr><td><b>通用大模型</b><br><span class="small">GPT / GLM 等</span></td>
<td>○ 不知今日菜价与售罄</td><td>○ 报菜名，不核价不核热量</td><td>○ 文字提醒，不保证执行</td><td>○ 有幻觉风险</td><td>○ 无记忆闭环</td></tr>
<tr><td style="background:#FDF3E3"><b>干饭决策机</b></td>
<td style="background:#FDF3E3">● {stats['dishes']} 道实采菜价 / {stats['windows']} 窗口</td><td style="background:#FDF3E3">● MILP 三套整餐 + 一句解释</td><td style="background:#FDF3E3">● 预算 / 忌口永不放宽</td><td style="background:#FDF3E3">● 放宽披露 + 无解直说</td><td style="background:#FDF3E3">● 打卡 + 周报回流</td></tr>
</table>
<p class="small">图例：● 具备　◐ 部分具备或口径不同　○ 不涉及或较弱　— 不适用。定位依据各官网与公开报道（2026-11 检索）：美团已通过「校园食堂」频道接入多所高校食堂档口；满客宝为团餐/政企食堂一体化管理系统；禧云信息为团餐信息化与智慧食堂 SaaS 服务商；薄荷健康 / MyFitnessPal 为食物营养记录工具。各有所长，客观呈现。</p>
<h3>为什么这是壁垒</h3>
<p>通用大模型能聊天，但它不知道你今天学校食堂的酸菜鱼多少钱、几点卖完、哪个窗口现做要等 8 分钟。
<b>一份一份采回来的真实数据 + 可复现算式</b>，才是"敢替你配饭"的资格。</p>
<h3>评委三问三答</h3>
<table>
<tr><th style="width:38%">可能的追问</th><th>我们的回答</th></tr>
<tr><td>美团已把部分食堂档口搬上线，会被碾压吗？</td><td>档口上线解决「点到寝」的履约，不解决「替你配整餐」的决策；我们与学生站在同一侧掂量预算 / 忌口 / 排队，可与其共存互导</td></tr>
<tr><td>后勤 SaaS 顺手加个推荐功能呢？</td><td>其客户是后勤处、数据口径是经营流水；学生侧决策需要口味 / 营养 / 预算的整餐平衡与解释生成，产品基因不同——更适合成为我们的数据与合作方</td></tr>
<tr><td>学生为什么不直接问大模型？</td><td>大模型不知道今天的菜价、售罄与排队，也无法保证预算与忌口硬约束；{stats['dishes']} 道实采数据 + 求解引擎才是可执行的答案</td></tr>
</table>
""", no=7)

# 08 Demo 说明
page(f"""
<h2>07 · Demo 说明（评委 10 秒可用）</h2>
<h3>在线体验</h3>
<p><span class="tag">待回填</span><b>在线体验：</b>部署后回填（提交邮件附链接）；<b>本地运行：</b>3 条命令见下方 / README。<br>
无需注册、无需测试账号，打开即用；打卡记录仅保存本机。</p>
<h3>本地运行（3 条命令）</h3>
<div class="card"><p style="margin:0">
<code>pip install -r requirements.txt</code><br>
<code>streamlit run app.py</code>　# 打开 http://localhost:8501<br>
<code>python engine/run_master.py</code>　# 引擎 + 17 类断言电池回归</p></div>
<h3>建议试玩路径（约 60 秒）</h3>
<table>
<tr><th>步骤</th><th>操作</th><th>看点</th></tr>
<tr><td>1</td><td>输入「减脂，18块，不吃香菜」→ 一键配饭</td><td>NL 解析 chips + 三套方案秒出（缓存命中）</td></tr>
<tr><td>2</td><td>点「再换一批」</td><td>同条件随机重挑三套，每次都不一样</td></tr>
<tr><td>3</td><td>清空输入再点「一键配饭」</td><td>随机抽一组条件配三套（结果区明示抽到的条件）</td></tr>
<tr><td>4</td><td>点「打卡这餐」×3，勾一次「算放纵餐」</td><td>周报长出热力图，放纵配额 2/3</td></tr>
<tr><td>5</td><td>输入「晚上懒得走，想增肌，25块，不吃海鲜和香菜」</td><td>懒人模式 + 并列忌口理解</td></tr>
<tr><td>6</td><td>夜宵时段 / 极端预算（5 元）</td><td>「建议」降级标签 / 诚实无解页</td></tr>
</table>
<h3>性能</h3>
<p>预生成 {len(cache)} 个代表性请求，缓存命中 &lt;0.1s；未命中实时求解 {min(ef):.1f}–{max(ef):.1f}s（另 {n_fast} 例极端条件秒判无解，不计入区间）并自动回写缓存。
有 OpenAI 兼容 Key 时 NL 走 LLM，无 Key 自动规则解析，演示不断线。</p>
<div class="warn">数据口径声明：菜品/价格/窗口为实采；拥挤、步行、油克、售罄为「待实测」AI 参数；
营养为估算级（麦当劳公示级）；评论为预置样例。</div>
<h3>界面速览</h3>
<div class="grid3">
<div><img class="ui-shot" src="{IMGS['bp_input']}"><p class="small">一句话输入：口语直接说，条件自动解析</p></div>
<div><img class="ui-shot" src="{IMGS['bp_result']}"><p class="small">结果页：整餐菜品明码标价 + 营养四宫格</p></div>
<div><img class="ui-shot" src="{IMGS['bp_comments']}"><p class="small">窗口评价样例（预置内容，非真实用户数据）</p></div>
</div>
""", no=8)

# 09 应用价值与市场规模
page(f"""
<h2>08 · 应用价值与市场规模</h2>
<h3>三层价值</h3>
<table>
<tr><th>对象</th><th>价值</th><th>可衡量指标</th></tr>
<tr><td>学生</td><td>决策解脱 + 坚持动力</td><td>每餐决策时间 ↓、周报热量达标率、周花费</td></tr>
<tr><td>高校后勤</td><td>窗口口碑 + 拥挤/售罄数据服务</td><td>错峰引导、滞销/售罄复盘、窗口改进清单</td></tr>
<tr><td>企业团餐</td><td>同一套方法迁移</td><td>团餐满意度、餐标执行率</td></tr>
</table>
<h3>市场规模：TAM / SAM / SOM</h3>
<div class="funnel">
<div class="fbar" style="width:100%;background:linear-gradient(90deg,#3A1E0E,#7C4A22)">TAM · 全国高校在校生 4,846 万人 · 高校餐饮约 4,833 亿元/年</div>
<div class="fbar" style="width:62%;background:linear-gradient(90deg,#A05224,#C96428)">SAM · 多食堂区高校 ≈2,200 万人（普通本科 1,257 所）</div>
<div class="fbar" style="width:30%;background:linear-gradient(90deg,#E07A3F,#F0A05A);color:#4A2E14">SOM · 首年 1–3 校试点</div>
<p class="small" style="margin:4px 0 0">漏斗宽度示意、非严格比例。口径见下表；每个数字附来源编号，无可靠出处的不写。</p>
</div>
<table class="tight">
<tr><th style="width:8%">层</th><th>口径与规模</th><th style="width:35%">说明</th></tr>
<tr><td><b>TAM</b></td><td>全国高校在校生正餐决策：高等教育在学总规模 <b>4,846 万人</b>①；对应高校餐饮市场 2023 年约 <b>4,833 亿元</b>、2024 年预计突破 5,000 亿元②</td><td>每人每天 2–3 次正餐决策的高频刚需；坐落于约 <b>2.7 万亿元</b>的团餐大盘③</td></tr>
<tr><td><b>SAM</b></td><td>多食堂区、大规模在校生高校：普通本科学校 <b>1,257 所</b> × 校均 <b>17,428 人</b> ≈ 2,200 万人①</td><td>以普通本科院校近似「多食堂区」首发客群；食堂团餐占高校餐饮 55.5%②</td></tr>
<tr><td><b>SOM</b></td><td>首年 <b>1–3 校</b>试点：按校均 1.7 万人、渗透 20% 计，单校约 3,500 名周活用户</td><td>为团队<b>目标假设</b>，非第三方数据；先验证 C 端口碑与 B 端单校订阅，再复制</td></tr>
</table>
<p style="line-height:1.75;margin:6px 0 0">自下而上的核对：单校 3,500 名周活 × 每人每天 2–3 次正餐决策，意味着每天替学生掂量约 7,000–10,000 次整餐组合——
先把这个量级做扎实，再谈向 SAM 的 1,257 所普通本科复制；C 端渗透率与 B 端付费意愿，就是首年要验证的两个核心假设。</p>
<h3 style="margin-top:14px">为什么是现在</h3>
<div class="dpath" style="margin-top:4px">
<div class="drow"><span class="dn">01</span><div class="dt"><b>多食堂区成为标配，现场决策越来越难</b><em>食堂多区、多窗口、数百道菜，正餐组合数指数级增长，「站在门口纠结」是每天两次的常态</em></div><span class="df">需求侧</span></div>
<div class="drow"><span class="dn">02</span><div class="dt"><b>后勤数字化铺到了经营层，决策层仍空白</b><em>支付、进销存、明厨亮灶等系统已在高校普及，但「替学生配整餐」的学生侧决策层无人补位</em></div><span class="df">供给侧</span></div>
<div class="drow"><span class="dn">03</span><div class="dt"><b>LLM + 求解器让配餐 Agent 可低成本落地</b><em>听得懂口语、又能在硬约束内精确求解的组合，第一次可以不依赖人工规则表跑起来</em></div><span class="df">技术侧</span></div>
</div>
<p class="small">来源（查证于 2026-11）：① 教育部《2024 年全国教育事业发展统计公报》（2025-06 发布）；② 红餐大数据《中国高校餐饮研究报告 2025》；③ 艾瑞咨询《2025 年中国团餐行业研究报告》（2024 年中国团餐市场规模约 2.7 万亿元）。无可靠出处的数字不写。</p>
""", no=9)

# 10 商业模式与下一步规划
page(f"""
<h2>09 · 商业模式与下一步规划</h2>
<h3>商业模式：C 端免费 + 高校后勤 SaaS</h3>
<table>
<tr><th>层</th><th>内容</th><th>定价（假设）</th></tr>
<tr><td>C 端学生</td><td>配餐 / 打卡 / 周报 全免费，做渗透与口碑</td><td>0 元（增长飞轮）</td></tr>
<tr><td>B 端后勤 SaaS</td><td>窗口经营看板：拥挤曲线、售罄复盘、菜品评价聚合、菜单健康度</td><td>按校区订阅，数千–数万元/年</td></tr>
<tr><td>数据服务</td><td>团餐企业 / 智慧食堂系统的菜单-营养-决策数据接口</td><td>按调用量 / 项目制</td></tr>
</table>
<h3>单位经济（粗算）</h3>
<p>单校落地成本：首校实采 4–5 人日 / 模板复用后单校校准 ≈1 人日；边际成本主要是采集与标注。
C 端零获客成本（食堂门口即是流量入口），B 端以"窗口数据看板"为付费锚点，先单校验证，再多校复制。</p>
<h3>首年要验证的三个假设（与里程碑对应）</h3>
<div class="grid3">
<div class="card"><b style="color:#C96428;font-size:12.5px">价值假设</b>
<p style="margin:4px 0 0">学生真的用它替代「现场纠结」。<span class="small">判据：周活渗透 20%、次周留存、每餐决策时间。</span></p></div>
<div class="card"><b style="color:#C96428;font-size:12.5px">增长假设</b>
<p style="margin:4px 0 0">食堂门口的零成本获客成立。<span class="small">判据：自然新增占比、同学间推荐系数。</span></p></div>
<div class="card"><b style="color:#C96428;font-size:12.5px">付费假设</b>
<p style="margin:4px 0 0">后勤愿为窗口看板付费。<span class="small">判据：首单订阅落地、续费意愿。</span></p></div>
</div>
<h3>下一步规划与里程碑（目标假设）</h3>
<table>
<tr><th style="width:16%">阶段</th><th>动作</th><th style="width:30%">目标（假设）</th></tr>
<tr><td>赛后 1 月</td><td>学校管理端看板；拥挤/售罄/油克实测校准；饭后实测评价闭环</td><td>本校周活 3,500+（渗透 20%）</td></tr>
<tr><td>1 学期</td><td>口味自适应（个人画像回灌打分）；周报自动推送；错峰建议</td><td>留存稳定，B 端首单订阅落地</td></tr>
<tr><td>1 学年</td><td>多校扩展（采集模板 + 打标管线 + 引擎整体迁移）</td><td>1–3 校跑通，形成复制手册</td></tr>
<tr><td>远期</td><td>企业团餐 / 智慧食堂系统数据接口</td><td>方法论跨场景迁移</td></tr>
</table>
<h3>竞合，而不是对抗</h3>
<p>我们只做<b>学生侧的整餐决策层</b>：外卖平台与后勤 SaaS 是渠道和数据互补方（我们为其导流、供数），
营养 App 培养出的记录习惯由周报承接。决策层的空位，正是我们的位置。</p>
<h3>数据飞轮（免费 C 端如何养出付费 B 端）</h3>
<div class="flow" style="margin:8px 0 0">
<div class="step"><b>更多使用</b><span>打卡 / 再换一批 / 随机试</span></div><div class="arr">→</div>
<div class="step"><b>更准的数据</b><span>口味画像 / 售罄与拥挤校准</span></div><div class="arr">→</div>
<div class="step"><b>更好的方案</b><span>三套整餐更贴心、留存更稳</span></div><div class="arr">→</div>
<div class="step"><b>更多用户</b><span>口碑扩散 + 后勤合作看板</span></div>
</div>
""", no=10)

# 11 风险与边界 + 团队
page(f"""
<h2>10 · 风险、诚实边界与团队</h2>
<h3>风险与预案</h3>
<table>
<tr><th>风险</th><th>预案</th></tr>
<tr><td>油克/克重估算偏差</td><td>来源列标注 + 实测校准排期；估算级不做医疗承诺</td></tr>
<tr><td>售罄/拥挤误判</td><td>宁缺勿错，拿不准降权不硬过滤；卡片提示"以现场为准"</td></tr>
<tr><td>极端条件无解</td><td>两段式松弛 + 放宽披露 + 诚实无解页，不静默放宽忌口与预算</td></tr>
<tr><td>数据时效</td><td>更新日期留档；赛后月度复核 + 学生纠错上报</td></tr>
<tr><td>隐私合规</td><td>位置只到食堂锚点粒度；打卡本机存储；营养输出附非医疗建议</td></tr>
</table>
<h3>诚实边界（公开承诺）</h3>
<p>① 加权和仅达支撑前沿，不声称全局最优；② 营养估算级仅供参考，非医疗建议；
③ AI 参数（拥挤/步行/油克/售罄）未实测，来源列如实标注；④ 评论为预置样例，非真实用户数据；
⑤ 加权和求解保证确定性，同请求两次结果一致。</p>
<h3>团队与分工</h3>
<p>干饭决策机团队：数据采集与打标 ｜ 引擎与 NL Agent ｜ 产品 UI 与视频工程。
设计阶段完成 20+ 项争议裁决并全部冻结，执行阶段以「事实源文档 + 断言电池」双纪律推进。</p>
<p class="small">负责人与联系方式：见提交邮件署名。</p>
<h3>结语</h3>
<p class="lead">我们不替学生决定"应该吃什么"，只把 719 道菜掂量清楚，端出三套不糊弄的方案。
<b>吃透整座食堂，才敢替你配三套饭。</b></p>
<h3>附录（随提交包附）</h3>
<table class="tight">
<tr><th style="width:22%">附录</th><th>内容</th></tr>
<tr><td>引擎断言电池</td><td>17 类硬断言的运行输出全绿记录（预算 / 忌口 / 营养带 / 排他性等）</td></tr>
<tr><td>视频分镜</td><td>演示视频分镜脚本与成片，对应「一句话 → 三套饭」全链路</td></tr>
<tr><td>数据主表</td><td>{stats['dishes']} 道菜品主表：六维标签、计价规则、来源列与「待实测」标注</td></tr>
</table>
""", no=11)

html = f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(P)}</body></html>'
html_path = os.path.join(OUT, 'bp.html')
open(html_path, 'w', encoding='utf-8').write(html)
print('HTML →', html_path)

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    try:
        br = pw.chromium.launch(channel='chrome')
    except Exception:
        br = pw.chromium.launch(channel='msedge')
    page = br.new_page()
    page.goto('file:///' + html_path.replace('\\', '/'))
    page.wait_for_timeout(1500)
    pdf_path = os.path.join(OUT, '干饭决策机_商业计划书.pdf')
    page.pdf(path=pdf_path, format='A4', print_background=True)
    br.close()
print('PDF →', pdf_path, f'{os.path.getsize(pdf_path)/1024/1024:.2f} MB')
