# 🍚 干饭决策机

[![CI](https://github.com/wenye9556/ganfan-decision-machine/actions/workflows/ci.yml/badge.svg)](https://github.com/wenye9556/ganfan-decision-machine/actions/workflows/ci.yml)

**吃透整座食堂，才敢替你配三套饭。**
饿着的人，不该做 719 道选择题。

一句话（如「减脂，18块，不吃香菜」）→ AI Agent 理解并调用整餐搭配引擎 → 在 **719 道真实菜品 / 26 个窗口 / 6 个食堂区** 中配出 **Top3 整餐方案卡**，兼顾预算、忌口、辣度、场景营养带、油克与一周不重样，参考排队与售罄风险（时点待实测；过了一般售罄时点的窗口不推，排队只在懒人模式计入）。

---

## 一、快速开始（本地 3 条命令）

```bash
pip install -r requirements.txt
streamlit run app.py            # 打开 http://localhost:8501，无需账号
python engine/run_master.py     # 引擎冒烟 + 17 类断言电池（全绿/确定性）
```

> Windows 中文控制台建议先 `set PYTHONIOENCODING=utf-8`（PowerShell: `$env:PYTHONIOENCODING='utf-8'`）。

### 建议试玩路径（60 秒）

| 步骤 | 操作 | 看点 |
|---|---|---|
| 1 | 输入「减脂，18块，不吃香菜」→「🍽️ 一键配饭」 | NL 解析 chips（含解析来源）+ 三套方案（缓存命中 <0.1s） |
| 2 | 同一句话再点一次「一键配饭」 | 同条件确定性重解，结果可复现（不走随机） |
| 3 | 清空输入再点「一键配饭」 | 随机抽一组条件（结果区明示本次条件） |
| 4 | 点「🎲 再换一批」 | 随机重挑三套，与上批低重合 |
| 5 | 「打卡这餐」×3，勾一次「算放纵餐」 | 周报热力图 + 放纵配额 2/3（只记账不拦截） |
| 6 | 输入「晚上懒得走，均衡点，20块，不吃牛和蛋」 | 懒人模式 + 并列忌口理解（中文数字/钟点也听得懂） |
| 7 | 手动切到夜宵 / 预算 5 元 | 「建议」降级标签 / 诚实无解页 + 一键「预算+3元重试」 |
| 8 | 结果区「🧾 这顿怎么配出来的」 | 决策小票：听懂了什么 → 719 道逐步筛到剩几道 → 出餐自检（如 17/17 ✓）→ 为什么是这三套 |
| 9 | 「🧪 给评委的刁难卡」任点一张 | 不读预存结果、现场实算并显示耗时；夜宵 23:00 进诚实页；「同句连点两次」并排比对两遍方案签名 |

## 二、在线体验（Streamlit Community Cloud）

部署方式（仓库已含全部依赖与数据，部署后回填链接）：

1. 将本目录推送到 GitHub（注意：主表 xlsx 需一并提交，约 125KB）。
2. https://share.streamlit.io → New app → 选择仓库，Main file path = `app.py`。
3. 无需 Secrets 即可运行（NL 自动走规则解析）；如需 LLM 解析与解释，
   在 Secrets 配置 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`（OpenAI 兼容协议）。

**测试账号**：无需账号，打开即用。打卡数据仅存本机（云端为临时存储，用于演示）。

## 三、目录结构

```
app.py                 Streamlit UI（手机框暖色 / 三卡上菜 / 打卡周报 / 评论 / 诚实边界）
app_helpers.py         UI 样式、营养表卡片、周报聚合、预置评论
engine/
  loader.py            主表装载 + 完整性断言（按列名读取，只读原件）
  core.py              整餐搭配引擎（硬过滤→三维打分→双通道MILP→TOPSIS→配额Top3）
  nl_agent.py          NL Agent：口语→结构化JSON（LLM/规则双通道）→ 每方案一句解释
  cache.py             方案缓存（键=引擎版本+规范化请求哈希；确定性/随机分命名空间；命中<0.1s）
  params.yaml          全部数值参数（带 source/calibrated 标注，🚧=AI参数待实测）
  run_master.py        主表冒烟 + 17 类断言电池 + 确定性校验
  run_nl.py            NL 链路验收（3 句口语 → Top3）
  test_nl.py           NL 解析回归（48 句：预算语境/中文数字/钟点/忌口裸词）
  pregen_cache.py      51 个代表性请求预生成缓存
  append_std.py        D区一层打标追加进标准菜名表 + 克重回填
  tag_rules.md         打标规则（LLM 初打 SSOT）
  export_video_data.py 引擎数据导出给视频工程
  merge_std.py/write_std.py  早期全量打标流水线（保留存档）
cache/plans.json       预生成方案缓存（随仓提交，云端演示走缓存命中）
data/seed_checkins.json 周报演示种子数据（云端首开周报非空）
干饭决策机_数据采集_主表.xlsx   唯一数据主表（719菜/26窗/6区 + 671标准菜名）
video/                 Remotion 视频工程（七幕分镜 / TTS 旁白 / 逐字字幕）
bp/                    商业计划书（HTML → PDF）
test_app.py            UI 全流程冒烟（NL→Top3→打卡→周报）
```

## 四、AI 技术实现（书面版）

- **NL Agent 链路**：口语 → 结构化请求（scenario/B/period/asof/anchor/spice_max/taboo/lazy，闭集校验）
  → 调用引擎 → 每方案一句解释。LLM 走 OpenAI 兼容协议；无 Key 自动规则解析（预算正则 + 忌口否定从句 + 场景词表）。
- **整餐多目标优化**：热量区间与蛋白下限不可分解到菜级，故采用 PuLP+CBC 的 MILP 整餐组合优化：
  硬过滤 → 三维打分（口味/营养/价格，当轮池中心化）→ 双通道（普通离散选菜 + 自选五档克重）
  → 权重扫描 + 迭代排他补解 + 定向补解（强制自选/去主导窗口）→ TOPSIS → 双配额 Top3。
- **诚实降级**：两段式松弛，max r̂>0.3 标「放宽版」、>0.5 降级「建议」并披露放宽项；
  忌口与预算上限永不放宽。
- **可复现营养算式**：标准菜名 → 主料构成 × 食物成分表（熟重口径）→ 每 100g 热量/蛋白；
  烹饪方式 × 吸油等级估油克；麦当劳为官方公示级。
- **断言电池 17 类全绿**：预算/油/能量带/蛋白/单食堂/现做≤1/售罄/忌口/辣度/减脂无油炸/
  套餐档位基数/米饭入账/称重克重带/同名菜≤1/双配额/Top3排他/确定性。

## 五、数据与诚实边界

- 菜品、价格、窗口：**实地采集，人工转录**；窗口照片编号一一对应。
- **待实测标注**：拥挤等待、步行时长、油克系数、售罄时点为 AI 参数，主表来源列保留「待实测」；
  菜品克重标「AI估计待实测」。不伪装成实测值。
- 营养为估算级（麦当劳公示级），仅供参考，**非医疗建议**。
- 称重自选仅建模水饺鲜生（1.88 元/50g，荤素同价），其余称重窗口不建模。
- 评论为预置样例 20 条（演示），非真实用户数据。
- 位置只到食堂锚点粒度；打卡记录仅保存本机。

## 六、视频与 BP 复现

```bash
python engine/export_video_data.py     # 导出统计/三场景方案/示例周报
.venv/Scripts/python.exe video/scripts/tts.py   # edge-tts 七幕旁白 + 逐字字幕（edge-tts 在项目 venv）
python video/scripts/shots.py          # Playwright 截取 UI 素材（需先启动 app）
cd video && npm install && npm run render   # 整片渲染（需本机 Chrome；需用户授权后执行）
python bp/build_bp.py                  # 生成 商业计划书 PDF（A4，<10M）
```

> 复现视频与 BP 额外需要 Node.js 18+、Playwright、edge-tts（均不属于应用运行依赖，
> 应用本身只装 `requirements.txt` 三个包）。AI 食欲 B-roll 插槽见 `video/public/assets/gen/README.md`
> （素材放进去 + 填 manifest 即生效，不填则纯程序化渲染，两者都合规）。

视频纪律：≤180s / 1920×1080 / 暖色食欲系 / 美食永远主角 / 全片零算法术语 /
逐字高亮字幕 / 每镜抽帧审片，**整片渲染需用户授权**。

Windows 一键启动应用：双击 `start.bat`（自动停旧实例、启动 Streamlit 并打开浏览器）。

## 七、提交清单（MINMAX 黑客松）

- [x] 可登录试用作品：Streamlit 链接（部署后回填）+ 本 README 运行说明，无需测试账号
- [x] 演示视频 ≤3 分钟 MP4 <300M：邮件附件版 `video/out/干饭决策机_演示.mp4`
      （122.3s / 1080p30 / 12.98MB / 响度 −16 LUFS / 中文旁白 + 同步逐字字幕）；
      高清母片 `video/out/ganfan.mp4`（122.2s / 50MB）存档备用
- [x] 商业计划书 PDF <10M（`bp/干饭决策机_商业计划书.pdf`，11 页 2.90MB）
- 决赛：PPT + Demo + 产品体验展示（BP 与视频素材可复用）
