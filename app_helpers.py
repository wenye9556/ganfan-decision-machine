# -*- coding: utf-8 -*-
"""app_helpers.py —— 干饭决策机 Streamlit UI：样式 / 卡片 / 打卡周报 / 预置评论"""
import hashlib
import html
import json
import os
import time
from datetime import date, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
CHECKIN_PATH = os.path.join(DATA_DIR, 'checkins.json')
SEED_PATH = os.path.join(DATA_DIR, 'seed_checkins.json')    # 云端首开种子（入库；checkins.json 被 gitignore）

CSS = """
<style>
/* ================= design tokens ================= */
:root{
  --pri:#E07A3F; --pri-d:#C4602A; --pri-l:#F8C49B;
  --ink:#33261C; --ink2:#6E5744; --mut:#9A8470; --faint:#B9A48F;
  --line:#F1E2CF; --cream:#FFFCF7; --card:#FFFFFF; --soft:#FBF1E4;
}
html, body, .stApp{
  font-family:"PingFang SC","Microsoft YaHei","Hiragino Sans GB",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
html{ scrollbar-width:none; }
::-webkit-scrollbar{ width:0; height:0; }
body{ overflow-x:hidden; }

/* ================= page canvas ================= */
.stApp{
  background-color:#F6E7D4;
  background-image:
    radial-gradient(rgba(176,124,72,.13) 1px, rgba(0,0,0,0) 1.7px),
    radial-gradient(1000px 620px at 12% -6%, #FFE6C7 0%, rgba(255,230,199,0) 58%),
    radial-gradient(900px 700px at 88% 4%, #FBE0C9 0%, rgba(251,224,201,0) 55%),
    radial-gradient(1200px 900px at 50% 108%, #F2DDC5 0%, rgba(242,221,197,0) 60%);
  background-size:18px 18px, auto, auto, auto;
  background-attachment:fixed;
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
#MainMenu, footer{ display:none !important; }
[data-testid="stMain"]{ padding-top:0 !important; }
[data-testid="stMainBlockContainer"]{
  max-width:470px !important;
  width:min(470px, calc(100vw - 20px)) !important;
  min-height:calc(100vh - 44px);
  flex-shrink:0;
  margin:18px auto 24px !important;
  padding:0 16px 50px !important;
  box-sizing:border-box;
  position:relative;
  background:var(--cream);
  border:1px solid rgba(224,122,63,.13);
  border-radius:32px;
  box-shadow:
    0 1px 0 rgba(255,255,255,.95) inset,
    0 36px 80px -32px rgba(122,72,32,.40),
    0 8px 22px -14px rgba(122,72,32,.20);
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]{ gap:.5rem; }
/* 自定义 HTML 块的 markdown 容器默认带 -15px 底边距，会把下一个控件吸上来 */
[data-testid="stMarkdownContainer"]:has(> .heat),
[data-testid="stMarkdownContainer"]:has(> .chips),
[data-testid="stMarkdownContainer"]:has(> .meal-card),
[data-testid="stMarkdownContainer"]:has(> .hint),
[data-testid="stMarkdownContainer"]:has(> .ask-row),
[data-testid="stMarkdownContainer"]:has(> .stat-grid){ margin-bottom:0 !important; }
/* 快选条逐行 HTML：同样要归零，否则每行被吞 15px 高、与下方滑杆/刻度叠压 */
[data-testid="stMarkdownContainer"]:has(> .qb-head),
[data-testid="stMarkdownContainer"]:has(> .qb-row),
[data-testid="stMarkdownContainer"]:has(> .qb-ends),
[data-testid="stMarkdownContainer"]:has(> .qb-ticks){ margin-bottom:0 !important; }
[data-testid="stMarkdownContainer"]:has(> .hint){ padding-bottom:3px; }
[data-testid="stMainBlockContainer"]::after{
  content:"干饭决策机 · 数据实地采集 · 打卡仅存本机";
  position:absolute; left:0; right:0; bottom:13px;
  text-align:center; font-size:9.5px; letter-spacing:.6px;
  color:#C9B49D; pointer-events:none;
}
h1,h2,h3,h4{ color:var(--ink); }

/* ================= hero ================= */
.hero{
  margin:0 -16px 12px; padding:26px 20px 15px;
  border-radius:31px 31px 22px 22px;
  background:radial-gradient(130% 120% at 50% -20%, #FFEDD7 0%, #FFF6EA 46%, rgba(255,246,234,0) 100%);
  position:relative; overflow:hidden;
}
.hero::after{
  content:''; position:absolute; left:0; right:0; bottom:0; height:1px;
  background:linear-gradient(90deg,transparent,rgba(224,122,63,.16),transparent);
}
.hero-top{ display:flex; align-items:center; justify-content:center; gap:12px; }
.hero-mark{
  width:52px; height:52px; flex:0 0 52px; border-radius:17px;
  display:grid; place-items:center; font-size:27px;
  background:linear-gradient(145deg,#FFC38D 0%,#EE8B4C 55%,#D96C2F 100%);
  box-shadow:0 10px 20px -8px rgba(205,110,50,.62), inset 0 1px 0 rgba(255,255,255,.5);
  transform:rotate(-4deg);
}
.hero-name{ text-align:left; min-width:0; }
.hero .logo{
  font-size:27px; font-weight:900; letter-spacing:1.5px; line-height:1.1;
  color:#2F2118; white-space:nowrap;
}
.hero-tag{
  font-size:11.5px; color:#9A7C60; margin-top:4px; letter-spacing:.2px;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
.data-badges{ display:flex; justify-content:center; gap:6px; margin:14px 0 0; flex-wrap:wrap; }
.data-badges span{
  display:inline-flex; align-items:center; gap:5px;
  background:rgba(255,255,255,.74); border:1px solid #F2E1CC; color:#9A7552;
  font-size:10.5px; padding:4px 9px; border-radius:20px; line-height:1.35;
  box-shadow:0 1px 2px rgba(150,90,40,.04);
}
.data-badges span::before{
  content:''; width:4px; height:4px; border-radius:50%; background:#E9B486; flex:0 0 4px;
}
.data-badges span:nth-child(1){
  background:#FFF1E2; border-color:#F6D8BC; color:#C0602A; font-weight:800;
}
.data-badges span:nth-child(1)::before{ background:#E07A3F; }

/* ================= tabs as segmented nav ================= */
.stTabs{ margin-top:2px; }
.stTabs > div > div:first-child{
  position:sticky; top:0; z-index:60;
  padding:9px 0 4px; margin:0 0 -4px;
  background:#FFFCF7;
}
.stTabs [data-baseweb="tab-list"]{
  display:flex; gap:3px; padding:4px;
  background:#F6EADB; border-radius:15px; border:none;
  box-shadow:0 1px 0 rgba(255,255,255,.85) inset, 0 8px 18px -16px rgba(120,70,30,.5);
}
.stTabs [data-baseweb="tab"]{
  flex:1 1 0; justify-content:center; height:38px; padding:0 2px;
  border-radius:11px; background:transparent; border:none; color:#9B8470;
  transition:background .18s, color .18s, box-shadow .18s;
}
.stTabs [data-baseweb="tab"] p{
  font-size:12.5px !important; font-weight:700; color:inherit !important;
  white-space:nowrap; margin:0;
}
.stTabs [data-baseweb="tab"][aria-selected="true"]{
  background:#FFFDFA; color:#C4602A;
  box-shadow:0 2px 8px -2px rgba(150,90,40,.24), 0 0 0 1px rgba(224,122,63,.08);
}
.stTabs [data-baseweb="tab"]:hover{ color:#C4602A; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{ display:none !important; }
.stTabs [role="tabpanel"]{ padding-top:12px !important; }

/* ================= chat ask bubble ================= */
.ask-row{ display:flex; gap:8px; align-items:flex-start; margin:2px 0 4px; }
.ask-ava{
  width:30px; height:30px; flex:0 0 30px; border-radius:50%;
  background:#FFF1E1; border:1px solid #F6DCC0;
  display:grid; place-items:center; font-size:15px;
}
.ask-bubble{
  background:#FFF6EA; border:1px solid #F5E3CC;
  border-radius:4px 14px 14px 14px; padding:8px 12px 9px;
}
.ask-bubble b{ font-size:13px; color:#5A4331; font-weight:800; }
.ask-bubble span{ display:block; font-size:11.5px; color:#A0836A; margin-top:2px; }

/* ================= text input ================= */
div[data-testid="stTextInput"]{ margin:0; padding-bottom:3px; }
div[data-testid="stTextInputRootElement"]{
  background:#FFFFFF !important;
  border:1.5px solid #EFDDC7 !important;
  border-radius:18px !important;
  min-height:52px;
  box-shadow:0 3px 10px -7px rgba(150,90,40,.45);
  transition:border-color .18s, box-shadow .18s;
}
div[data-testid="stTextInputRootElement"]:focus-within{
  border-color:var(--pri) !important;
  box-shadow:0 0 0 4px rgba(224,122,63,.13), 0 10px 22px -14px rgba(224,122,63,.7) !important;
}
div[data-testid="stTextInputRootElement"] input{
  font-size:14.5px !important; padding:13px 16px !important;
  color:var(--ink) !important; background:transparent !important;
}
div[data-testid="stTextInputRootElement"] input::placeholder{ color:#B7A28D; }

/* ================= buttons ================= */
[data-testid="stBaseButton-primary"]{
  min-height:54px !important;
  border-radius:18px !important;
  border:1px solid rgba(180,90,30,.22) !important;
  background:linear-gradient(135deg,#F0914F 0%,#E07A3F 55%,#D06A30 100%) !important;
  color:#fff !important;
  box-shadow:0 12px 24px -10px rgba(200,100,40,.68), inset 0 1px 0 rgba(255,255,255,.3) !important;
  transition:transform .16s, box-shadow .16s, filter .16s;
}
[data-testid="stBaseButton-primary"] p{
  color:#fff !important; font-size:16px !important; font-weight:900 !important;
  letter-spacing:.8px;
}
[data-testid="stBaseButton-primary"]:hover{
  transform:translateY(-1.5px);
  filter:brightness(1.03);
  box-shadow:0 16px 30px -10px rgba(200,100,40,.72), inset 0 1px 0 rgba(255,255,255,.32) !important;
}
[data-testid="stBaseButton-primary"]:active{ transform:scale(.985); }
div[data-testid="stElementContainer"]:has([data-testid="stBaseButton-primary"]){ padding-bottom:3px; }

[data-testid="stBaseButton-secondary"]{
  min-height:38px !important;
  border-radius:12px !important;
  background:#FFFDF9 !important;
  border:1.5px solid #EFDDC7 !important;
  color:#8A6A50 !important;
  box-shadow:0 2px 6px -4px rgba(150,90,40,.35) !important;
  transition:border-color .16s, background .16s, transform .16s;
}
[data-testid="stBaseButton-secondary"] p{
  color:#8A6A50 !important; font-size:12.5px !important; font-weight:800 !important;
}
[data-testid="stBaseButton-secondary"]:hover{
  border-color:#E3B78F !important; background:#FFF7EC !important; transform:translateY(-1px);
}
[data-testid="stBaseButton-secondary"]:hover p{ color:#C4602A !important; }
[data-testid="stBaseButton-secondary"]:active{ transform:scale(.985); }

/* ================= expander ================= */
[data-testid="stExpander"] details{
  background:#FFFDF9 !important;
  border:1px solid #F2E2CE !important;
  border-radius:16px !important;
  box-shadow:0 4px 12px -14px rgba(150,90,40,.6);
  overflow:hidden;
}
[data-testid="stExpander"] summary{
  background:transparent !important;
  padding:11px 14px !important;
  border-radius:16px !important;
  transition:background .16s;
}
[data-testid="stExpander"] summary:hover{ background:#FFF8EF !important; }
[data-testid="stExpander"] summary p{
  font-size:12.5px !important; font-weight:800 !important; color:#7A5F49 !important;
}
[data-testid="stExpander"] summary [data-testid="stIconMaterial"]{ color:#C08A5E; font-size:18px !important; }
[data-testid="stExpanderDetails"]{
  padding:2px 14px 10px !important;
  border-top:1px dashed #F2E3D1;
}
[data-testid="stExpander"] div[data-testid="stTextInputRootElement"]{
  min-height:40px; border-radius:12px !important;
}
[data-testid="stExpander"] div[data-testid="stTextInputRootElement"] input{
  padding:8px 12px !important; font-size:12.5px !important;
}

/* ================= widget labels & inputs ================= */
[data-testid="stWidgetLabel"] p{
  font-size:11.5px !important; font-weight:800; color:#8A6C52;
  letter-spacing:.3px;
}
[data-testid="stCheckbox"] label p{ font-size:12px !important; color:#7A5F49 !important; }
[data-testid="stCheckbox"]{ margin-top:-2px; }

/* radio -> segmented chips */
div[data-testid="stElementContainer"]:has([data-testid="stRadio"]){ width:100% !important; }
[data-testid="stRadio"]{ width:100% !important; }
[data-testid="stRadio"] div[role="radiogroup"]{
  display:flex; gap:4px; background:#F7EDE1; padding:4px;
  border-radius:13px; width:100% !important;
}
[data-testid="stRadio"] label[data-baseweb="radio"]{
  flex:1 1 0; justify-content:center; margin:0 !important;
  padding:6px 0 !important; border-radius:9px;
  transition:background .16s, box-shadow .16s;
}
[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child{ display:none !important; }
[data-testid="stRadio"] label[data-baseweb="radio"] p{
  font-size:12px !important; font-weight:700; color:#9A8470 !important; white-space:nowrap;
}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked){
  background:#FFFDFA; box-shadow:0 2px 6px -2px rgba(150,90,40,.28);
}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p{
  color:#C4602A !important; font-weight:900 !important;
}

/* ================= 滑动快选条 ================= */
.qb-head{ display:flex; align-items:baseline; gap:8px; margin:4px 0 2px; }
.qb-head .qb-t{ font-size:12px; font-weight:900; color:#B4612C; letter-spacing:.6px; }
.qb-head .qb-s, .qb-row .qb-s{ font-size:10.5px; color:#B7A08B; }
.qb-row{ display:flex; align-items:center; justify-content:space-between; margin:2px 0 0; }
.qb-row .qb-lab{ font-size:11.5px; font-weight:800; color:#8A6C52; letter-spacing:.3px; }
.qb-row .qb-val{ font-size:12.5px; font-weight:900; color:#C4602A; }
.qb-row .qb-bval{ font-size:23px; font-weight:900; color:#D06A30; line-height:1; letter-spacing:-.5px; }
.qb-row .qb-bval i{ font-style:normal; font-size:11px; font-weight:700; color:#A08770; margin-left:2px; }
.qb-ends{ display:flex; justify-content:space-between; font-size:9.5px; color:#C6B49E; padding:0 3px; margin-top:-3px; }
/* 档位标签行：等分网格居中，让每个档位正对滑杆刻度位置（当前档 .on 高亮） */
.qb-ticks{
  display:grid; grid-auto-flow:column; grid-auto-columns:1fr;
  text-align:center; padding:0 4px; margin-top:-2px;
}
.qb-ticks span{ font-size:10px; color:#B9A48D; font-weight:700; transition:color .15s; white-space:nowrap; }
.qb-ticks span.on{ color:#C4602A; font-weight:900; position:relative; }
.qb-ticks span.on::after{                            /* 当前档位：橙色小圆点标记（随滑杆位置走） */
  content:''; position:absolute; left:50%; bottom:-5px; transform:translateX(-50%);
  width:4px; height:4px; border-radius:50%; background:#E07A3F;
}
.qb-row-chips{ margin-top:8px; margin-bottom:1px; }

/* 场景 / 辣度 双列：每列一张内嵌小卡（标签在上 → 滑杆居中 → 刻度在下），
   列与列之间留 9px 米色空隙 + 1px 描边，刻度网格被列宽夹住，不会与另一列混行 */
div[data-testid="stHorizontalBlock"]:has(.qb-duo){
  gap:9px !important; align-items:stretch; margin-top:2px;
}
div[data-testid="stHorizontalBlock"]:has(.qb-duo) > div[data-testid="stColumn"]{
  min-width:0 !important; padding:7px 10px 7px;
  background:linear-gradient(180deg,#FFFDF9 0%,#FFF8EF 100%);
  border:1px solid #F3E3CE; border-radius:14px;
  box-shadow:0 2px 6px -5px rgba(150,90,40,.55);
}
div[data-testid="stHorizontalBlock"]:has(.qb-duo) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]{
  gap:4px;
}
div[data-testid="stHorizontalBlock"]:has(.qb-duo) .qb-row{ margin:0; }
div[data-testid="stHorizontalBlock"]:has(.qb-duo) .qb-ticks{ margin-top:-1px; padding:0 2px; }

/* slider —— 快选条滑杆：暖橙大 thumb / 奶油轨道，档位标签用自绘 .qb-ticks（默认刻度与气泡隐藏） */
[data-testid="stSlider"]{ margin:0; }
[data-testid="stSlider"] [data-testid="stWidgetLabel"]{ margin-bottom:1px; padding-bottom:0; }
[data-testid="stSlider"] [data-testid="stSliderThumbValue"],
[data-testid="stSlider"] [data-testid="stSliderTickBar"]{ display:none !important; }
[data-testid="stSlider"] [data-baseweb="slider"] > div > div{      /* 轨道（1.50 DOM：slider>div>div） */
  background:#F3E4CF !important; height:6px !important; border-radius:6px;
}
[data-testid="stSlider"] [role="slider"]{
  width:20px !important; height:20px !important; margin-top:3px;   /* 放大后补偿 thumb 锚点居中 */
  background:linear-gradient(145deg,#F59A55,#D96C2F) !important;
  border:2.5px solid #FFFFFF !important;
  box-shadow:0 3px 9px rgba(217,108,47,.5) !important;
  transition:transform .15s;
}
[data-testid="stSlider"] [role="slider"]:focus-visible{
  box-shadow:0 0 0 6px rgba(224,122,63,.2), 0 3px 9px rgba(217,108,47,.5) !important;
}

/* 忌口 chips —— 页面上唯一 8 列的横排块里的 checkbox，重绘成圆角药丸（点亮=暖橙填充） */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)){ gap:5px !important; }
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stColumn"]{ min-width:0 !important; }
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"]{ margin:0 !important; padding:0 !important; }
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label{
  display:flex !important; align-items:center; justify-content:center;
  min-height:32px; padding:5px 2px; cursor:pointer; gap:0 !important;
  background:#FFFFFF; border:1.5px solid #EFDDC7; border-radius:20px;
  box-shadow:0 2px 5px -4px rgba(150,90,40,.4);
  transition:background .15s, border-color .15s, box-shadow .15s, transform .12s;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label:hover{
  border-color:#E8B98F; transform:translateY(-1px);
}
/* 隐藏原生勾选框与 input（1.50 DOM：label 首子元素是方框 span，其后是隐藏 input） */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label > span:first-child,
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label > input{ display:none !important; }
/* 文字居中修正：方框 span 虽已隐藏，BaseWeb 仍在文字外层 div 上保留 7.5px 左内边距（勾选框占位），
   使文字整体右偏 3.75px —— 把这段占位改成左右各 3.75px 对称内边距（药丸总宽不变），
   再由 flex + text-align 双保险居中 */
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label > div{
  padding:0 3.75px !important;      /* 7.5px 占位左右均分：文字回到正中，药丸总宽与原设计一致 */
  display:flex !important; justify-content:center !important;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label > div > div[data-testid="stWidgetLabel"]{
  display:flex !important; justify-content:center !important;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label p{
  font-size:11px !important; font-weight:700; color:#8A6A50 !important;
  white-space:nowrap; margin:0; line-height:1.3; text-align:center;
  /* CJK 字形在 1.3 行高里视觉重心偏上约 1.75px：p 加 3.5px 上内边距，flex 居中会把盒子重新居中，
     字形随内边距下移 1.75px（盒子中心不动，chips 外框尺寸不变） */
  padding:3.5px 0 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label:has(input:checked){
  background:linear-gradient(135deg,#F59A55 0%,#E07A3F 55%,#D06A30 100%) !important;
  border-color:#D06A30;
  box-shadow:0 6px 12px -6px rgba(200,100,40,.65), inset 0 1px 0 rgba(255,255,255,.25);
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label:has(input:checked) p{ color:#fff !important; font-weight:900; }

/* selectbox / multiselect */
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child{
  background:#FFFDF9 !important;
  border:1.5px solid #EFDDC7 !important;
  border-radius:12px !important;
  min-height:40px;
  box-shadow:0 2px 6px -6px rgba(150,90,40,.5);
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:first-child:hover,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child:hover{
  border-color:#E3B78F !important;
}
[data-baseweb="tag"]{
  background:#FDEFE3 !important;
  border-radius:8px !important;
  border:1px solid #F7DCC1 !important;
}
[data-baseweb="tag"] span, [data-baseweb="tag"] div{ color:#B4612C !important; font-weight:700; }
[data-baseweb="popover"] [role="listbox"]{
  border-radius:14px !important;
  border:1px solid #F2E2CE !important;
  box-shadow:0 18px 40px -18px rgba(120,70,30,.4) !important;
}

/* ================= caption / meta / alert ================= */
[data-testid="stCaptionContainer"] p{
  font-size:11px !important; color:#A8917B !important; line-height:1.65;
}
div[data-testid="stCaptionContainer"]{ color:#A8917B; }
[data-testid="stAlert"]{
  background:#FFF9EF !important;
  border:1px solid #F3E2C8 !important;
  border-radius:14px !important;
}
[data-testid="stAlertContainer"]{
  background:#FFF9EF !important;
  color:#8A6A50 !important;
  border-radius:14px !important;
}
[data-testid="stAlertContainer"] p,
[data-testid="stAlertContentInfo"]{ color:#8A6A50 !important; }
[data-testid="stAlertContainer"] svg{ color:#C08A5E !important; fill:#C08A5E !important; }
[data-testid="stAlert"] p{ font-size:12px !important; color:#8A6A50 !important; }
[data-testid="stSpinner"] p{ font-size:12px; color:#B4612C; }

/* ================= hint note ================= */
.hint{
  background:linear-gradient(180deg,#FFF9F1,#FFF6EB);
  border:1px solid #F4E4CF;
  border-left:3px solid #E8B27D;
  border-radius:4px 13px 13px 4px;
  padding:8px 11px;
  font-size:11.5px; line-height:1.7; color:#82694F;
  letter-spacing:.1px;
}

/* ================= parsed chips ================= */
.chips{
  background:#FFF9F0; border:1px solid #F4E4CF; border-radius:16px;
  padding:11px 12px 10px; margin:0;
  animation:serve .35s ease backwards;
}
.chips-head{
  display:flex; align-items:center; gap:5px;
  font-size:10.5px; font-weight:900; color:#B4612C; letter-spacing:.6px;
  margin-bottom:7px;
}
.chips-row{ display:flex; flex-wrap:wrap; gap:5px; }
.chips .chip{
  font-size:11.5px; color:#7D624A; background:#fff;
  border:1px solid #F0DFC9; border-radius:9px; padding:3px 8px; line-height:1.4;
}
.chips .chip:first-child{
  background:#FDEEE0; border-color:#F7D6B6; color:#B4612C; font-weight:800;
}
.chips-src{ margin-top:7px; font-size:10px; color:#B7A08B; }

/* ================= 三色听懂回执（✅ 你说的 / 📌 我先默认的 / 🙁 管不了的） ================= */
.heard{
  background:#FFF9F0; border:1px solid #F4E4CF; border-radius:16px;
  padding:11px 12px 9px; margin:0;
  animation:serve .35s ease backwards;
}
.heard-head{
  display:flex; align-items:center; gap:5px;
  font-size:10.5px; font-weight:900; color:#B4612C; letter-spacing:.6px;
  margin-bottom:6px;
}
.heard-head .heard-src{ font-weight:600; color:#C4A88C; letter-spacing:0; }
.heard-row{
  display:flex; align-items:baseline; gap:8px;
  padding:3.5px 0; font-size:12px; line-height:1.65;
}
.heard-row + .heard-row{ border-top:1px dashed #F4E4CF; }
.heard-row .hk{
  flex:0 0 92px; font-size:10.5px; font-weight:900; letter-spacing:.3px;
  white-space:nowrap;
}
.heard-row .hv{ flex:1; color:#5C4432; }
.heard-row.ok .hk{ color:#3E8E5A; }
.heard-row.ok .hv{ color:#4A6B44; font-weight:600; }
.heard-row.df .hk{ color:#C07A28; }
.heard-row.df .hv{ color:#8A6B4E; }
.heard-row.no .hk{ color:#A85B4E; }
.heard-row.no .hv{ color:#8A6B4E; }

/* ================= solve meta ================= */
/* 数字精简：主视觉只留「N 道菜符合你的条件」一句（加大加粗），
   缓存命中/耗时等实现细节收纳进 ⓘ 悬停小字（移动端点按也能借 title 提示露出） */
.solve-meta{
  display:inline-flex; align-items:center; gap:7px;
  font-size:14px; font-weight:800; color:#5C4432; background:#FBF4E9;
  border:1px solid #F3E4D2; border-radius:20px; padding:7px 14px;
  margin:2px 0 4px; line-height:1.5;
}
.solve-meta .meta-info{
  font-size:11px; font-weight:700; color:#B99B7D; cursor:help; user-select:none;
}

/* ================= empty state ================= */
.empty{
  margin:14px 0 4px; padding:26px 18px 24px;
  border-radius:20px; border:1.5px dashed #F0DCC4;
  background:linear-gradient(180deg,#FFFCF7,#FFF7EC);
  text-align:center;
}
.empty-art{ display:flex; justify-content:center; margin-bottom:12px; }
.empty-art span{
  width:38px; height:38px; border-radius:50%; background:#fff;
  border:1px solid #F4E2CB; display:grid; place-items:center; font-size:19px;
  box-shadow:0 5px 12px -7px rgba(150,90,40,.55); margin-left:-7px;
}
.empty-art span:first-child{ margin-left:0; }
.empty-t{ font-size:14.5px; font-weight:900; color:#5C4432; letter-spacing:.3px; }
.empty-s{ font-size:11.5px; color:#A5896F; margin-top:6px; line-height:1.7; }

/* ================= section title ================= */
.section-title{
  display:flex; align-items:center; gap:8px;
  font-size:17px; font-weight:900; letter-spacing:.4px; color:#33261C;
  margin:18px 0 8px;
}
.section-title::before{
  content:''; width:4px; height:16px; border-radius:3px;
  background:linear-gradient(180deg,#F09A5B,#DD7436); flex:0 0 4px;
}

/* ================= weekly stats ================= */
.stat-grid{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:0; padding:4px 0; }
.stat{
  display:flex; align-items:center; gap:9px;
  background:#fff; border:1px solid #F2E2CE; border-radius:16px;
  padding:11px 12px;
  box-shadow:0 6px 14px -14px rgba(150,90,40,.75);
}
.stat .si{
  width:34px; height:34px; flex:0 0 34px; border-radius:11px;
  display:grid; place-items:center; font-size:16px; background:#FFF3E5;
}
.stat:nth-child(2) .si{ background:#EDF7EA; }
.stat:nth-child(3) .si{ background:#FFF6DC; }
.stat:nth-child(4) .si{ background:#FDEDE6; }
.stat .num{ font-size:21px; font-weight:900; color:#33261C; line-height:1.05; letter-spacing:-.3px; }
.stat .lab{ font-size:10.5px; color:#9A8470; margin-top:2px; }

/* ================= heatmap ================= */
.heat{ display:grid; grid-template-columns:repeat(7,1fr); gap:5px; margin:0; padding:4px 0; }
.heat .hc{
  border-radius:12px; padding:8px 2px 7px; text-align:center;
  background:#F6EEE3; color:#B9A48D;
  border:1px solid rgba(224,122,63,.06);
  transition:transform .16s;
}
.heat .hc:hover{ transform:translateY(-2px); }
.heat .hc b{ display:block; font-size:11.5px; font-weight:800; }
.heat .hc span{ display:block; font-size:9px; opacity:.82; margin-top:2px; white-space:nowrap; }
.heat .hc em{ display:block; font-size:10px; font-style:normal; margin-top:3px; font-weight:800; }

/* ================= timeline ================= */
.tl{ position:relative; margin:6px 0 12px; padding-left:18px; }
.tl::before{
  content:''; position:absolute; left:6px; top:12px; bottom:12px; width:2px;
  background:linear-gradient(180deg,#F6D8B9,#F8EBDC); border-radius:2px;
}
.tl-item{ position:relative; margin-bottom:9px; }
.tl-dot{
  position:absolute; left:-17px; top:14px; width:10px; height:10px;
  border-radius:50%; background:#E07A3F; border:2.5px solid #fff;
  box-shadow:0 0 0 1px #F0D6B8; z-index:2;
}
.tl-dot.c{ background:#E9A93F; }
.tl-card{
  background:#fff; border:1px solid #F2E2CE; border-radius:14px; padding:10px 12px;
  box-shadow:0 6px 14px -14px rgba(150,90,40,.8);
  transition:transform .16s, box-shadow .16s;
}
.tl-card:hover{ transform:translateY(-1.5px); box-shadow:0 10px 20px -14px rgba(150,90,40,.8); }
.tl-top{ display:flex; align-items:center; gap:6px; font-size:10.5px; color:#A08770; flex-wrap:wrap; }
.tl-top b{ font-size:11.5px; color:#6E5340; }
.tl-top .tk{ font-weight:800; color:#9A6B12; }
.tl-items{ font-size:12.5px; color:#4A3627; margin-top:5px; line-height:1.55; overflow-wrap:anywhere; }
.tl-kv{ display:flex; gap:8px; margin-top:6px; font-size:11.5px; color:#B4612C; font-weight:900; }
.tl-kv span{ color:#9A8470; font-weight:600; }

/* ================= comments ================= */
.cmt{
  display:flex; gap:10px; background:#fff; border:1px solid #F2E2CE;
  border-radius:16px; padding:12px; margin:8px 0;
  box-shadow:0 6px 16px -16px rgba(150,90,40,.9);
  transition:transform .16s, box-shadow .16s;
}
.cmt:hover{ transform:translateY(-1.5px); box-shadow:0 12px 22px -16px rgba(150,90,40,.85); }
.cmt-ava{
  width:38px; height:38px; flex:0 0 38px; border-radius:50%;
  background:linear-gradient(150deg,#FFF1E0,#FFE2C6);
  display:grid; place-items:center; font-size:19px; border:1px solid #F7DFC5;
}
.cmt-main{ min-width:0; flex:1; }
.cmt-top{ display:flex; align-items:center; gap:8px; }
.cmt-top b{ font-size:12.5px; color:#4A3627; }
.cmt-top .stars{ margin-left:auto; font-size:10.5px; }
.cmt-txt{ font-size:13px; color:#5B4534; line-height:1.62; margin-top:5px; overflow-wrap:anywhere; }
.cmt-tags{ margin-top:7px; }
.tag{
  display:inline-block; background:#FBF0E2; color:#9C7350; font-size:10.5px;
  border-radius:20px; padding:2px 9px; border:1px solid #F5E5D2;
}
.stars{ color:#F2A33C; font-size:12px; letter-spacing:1.5px; }
.stars .off{ color:#EADCCB; }

/* ================= about ================= */
.about-list{ display:flex; flex-direction:column; gap:9px; margin-top:10px; }
.ab-card{
  display:flex; gap:11px; background:#fff; border:1px solid #F2E2CE;
  border-radius:16px; padding:12px 13px;
  box-shadow:0 6px 16px -16px rgba(150,90,40,.9);
}
.ab-ico{
  width:34px; height:34px; flex:0 0 34px; border-radius:11px;
  display:grid; place-items:center; font-size:17px; background:#FFF3E5;
}
.ab-card:nth-child(2) .ab-ico{ background:#F3F0E8; }
.ab-card:nth-child(3) .ab-ico{ background:#FFF6DC; }
.ab-card:nth-child(4) .ab-ico{ background:#EDF7EA; }
.ab-card:nth-child(5) .ab-ico{ background:#F0EEF9; }
.ab-card:nth-child(6) .ab-ico{ background:#FDEDE6; }
.ab-card:nth-child(7) .ab-ico{ background:#EAF3F6; }
.ab-card:nth-child(8) .ab-ico{ background:#FFF3E5; }
.ab-card:nth-child(9) .ab-ico{ background:#EDF7EA; }
.ab-card:nth-child(10) .ab-ico{ background:#F3F0E8; }
.ab-t{ font-size:13px; font-weight:900; color:#4A3627; letter-spacing:.3px; }
.ab-p{ font-size:12.2px; color:#6E5744; line-height:1.78; margin-top:4px; overflow-wrap:anywhere; }
.ab-p b{ color:#3F2C1E; font-weight:900; }

/* ================= meal card ================= */
.meal-card{
  position:relative; background:#fff; border:1px solid #F0DFC9;
  border-radius:22px; padding:15px 15px 14px; margin:16px 0 8px;
  box-shadow:0 12px 28px -20px rgba(150,90,40,.65), 0 2px 0 rgba(255,255,255,.9) inset;
  animation:serve .55s cubic-bezier(.2,.7,.3,1) backwards;
  overflow:hidden;
}
.meal-card.featured{
  border-color:rgba(224,122,63,.42);
  background:linear-gradient(180deg,#FFFDF9 0%,#FFFFFF 46%);
  box-shadow:0 18px 38px -20px rgba(196,96,42,.6), 0 0 0 1px rgba(224,122,63,.10), 0 2px 0 rgba(255,255,255,.9) inset;
}
.meal-card.featured::before{
  content:''; position:absolute; top:0; left:16px; right:16px; height:4px;
  border-radius:0 0 4px 4px;
  background:linear-gradient(90deg,#F8C08E,#E07A3F 55%,#D06A30);
}
.meal-card:hover{
  transform:translateY(-2px);
  box-shadow:0 20px 40px -22px rgba(150,90,40,.7);
  transition:transform .2s, box-shadow .2s;
}
@keyframes serve{ from{opacity:0; transform:translateY(14px) scale(.985);} to{opacity:1; transform:none;} }
.mc-head{ display:flex; align-items:center; gap:10px; }
.mc-idx{
  width:30px; height:30px; flex:0 0 30px; border-radius:10px;
  display:grid; place-items:center; font-size:15px; font-weight:900;
  background:#FFF2E4; color:#C4602A; border:1px solid #F7DCC1;
}
.featured .mc-idx{
  background:linear-gradient(145deg,#F9A661,#E07A3F); color:#fff;
  border-color:transparent; box-shadow:0 6px 12px -6px rgba(200,100,40,.7);
}
.mc-headl{ flex:1; min-width:0; }
.mc-l1{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.mc-l1 b{ font-size:12px; color:#8A6C52; font-weight:900; letter-spacing:.3px; }
.mc-l2{
  font-size:13px; color:#4A3627; font-weight:900; margin-top:4px;
  display:flex; align-items:center; gap:4px; min-width:0;
}
.mc-l2 span{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.pill{ font-size:10px; padding:2px 8px; border-radius:20px; font-weight:800; line-height:1.5; letter-spacing:.2px; }
.pill-ok{ background:#E9F5E4; color:#3F7C33; }
.pill-soft{ background:#FDF0DA; color:#A8741A; }
.pill-hard{ background:#FBE3DF; color:#B44436; }
.pill-self{ background:#EDF1FA; color:#3B5C9E; }
.pill-tag{ background:#F3EDFB; color:#6B4C9E; border:1px solid #E7DCF6; }
.mc-tag{ flex:0 0 auto; align-self:flex-start; margin-top:1px; }
.mc-wins{
  display:flex; flex-wrap:wrap; gap:5px;
  margin:10px 0 2px; padding-top:9px; border-top:1px dashed #F3E6D5;
}
.mc-wins span{
  font-size:10.5px; color:#8F6C4D; background:#FBF3E7;
  border:1px solid #F4E6D3; border-radius:8px; padding:2px 7px; line-height:1.5;
}
.mc-dishes{ margin-top:3px; }
.dish{
  display:flex; align-items:center; gap:8px; padding:7px 1px;
  border-bottom:1px dashed #F5EADC; font-size:13.2px;
}
.dish:last-child{ border-bottom:none; }
.d-e{ width:20px; flex:0 0 20px; text-align:center; font-size:13px; }
.d-n{ flex:1; min-width:0; color:#42301F; font-weight:600; overflow-wrap:anywhere; line-height:1.4; }
.d-w{
  font-size:9.5px; color:#3B5C9E; background:#EDF1FA;
  border-radius:6px; padding:1px 5px; flex:0 0 auto; font-weight:700;
}
.d-w-set{ color:#3E7D32; background:#E7F4E4; }
.d-p{ font-size:10.5px; color:#C0642B; font-weight:800; flex:0 0 auto; white-space:nowrap; }
.d-g{ font-size:11.5px; color:#9C8470; font-weight:800; white-space:nowrap; }
.tier-line{
  display:flex; gap:6px; align-items:center;
  font-size:11px; color:#8B6B4A; background:#FBF3E7;
  border:1px solid #F3E5D2; border-radius:10px; padding:6px 9px;
  margin-top:8px; line-height:1.5;
}
.mc-stats{
  display:grid; grid-template-columns:1.35fr 1fr 1fr 1fr;
  margin-top:11px; background:#FFFBF5;
  border:1px solid #F3E4D0; border-radius:14px; overflow:hidden;
}
.ms{ padding:9px 4px 8px; text-align:center; border-left:1px solid #F6EADB; }
.ms:first-child{ border-left:none; background:linear-gradient(180deg,#FFF3E5,#FFF8EE); }
.ms .v{ display:block; font-size:14px; font-weight:900; color:#4A3627; letter-spacing:-.2px; white-space:nowrap; }
.ms.price .v{ font-size:19px; color:#D06A30; }
.ms .v i{ font-style:normal; font-size:9px; font-weight:700; color:#A08770; margin-left:3px; }
.ms .k{ display:block; font-size:9.5px; color:#A08770; margin-top:3px; letter-spacing:.3px; }
.mc-bars{
  margin-top:11px; padding-top:9px; border-top:1px dashed #F3E6D5;
  display:flex; flex-direction:column; gap:6px;
}
.bar-row{ display:grid; grid-template-columns:40px 1fr 26px; align-items:center; gap:8px; }
.bar-k{ font-size:10.5px; color:#8F7863; font-weight:700; letter-spacing:.2px; }
.bar-track{ height:5px; border-radius:4px; background:#F4E6D6; overflow:hidden; }
.bar-track i{
  display:block; height:100%; border-radius:4px;
  background:linear-gradient(90deg,#F3B07C,#E07A3F);
}
.bar-v{
  font-size:10.5px; color:#B4612C; font-weight:800; text-align:right;
  font-variant-numeric:tabular-nums;
}
.bar-note{
  margin-top:2px; font-size:9px; color:#B7A08B; letter-spacing:.2px;
  text-align:right; line-height:1.5;
}
.mc-ai{ display:flex; gap:8px; margin-top:11px; align-items:flex-start; }
.ai-ava{
  width:28px; height:28px; flex:0 0 28px; border-radius:50%;
  background:linear-gradient(150deg,#FFF0DE,#FFDDBB);
  display:grid; place-items:center; font-size:14px; border:1px solid #F8DFC2;
}
.ai-bub{
  flex:1; min-width:0; background:#FFF7EC; border:1px solid #F5E6D2;
  border-radius:4px 14px 14px 14px; padding:8px 11px 9px;
}
.ai-name{ display:block; font-size:9.5px; font-weight:900; color:#B4612C; letter-spacing:.5px; margin-bottom:3px; }
.ai-txt{ font-size:12px; color:#6B5442; line-height:1.65; overflow-wrap:anywhere; }
.mc-relax{
  display:flex; gap:6px; align-items:flex-start; margin-top:9px;
  background:#FFF8E3; border:1px solid #F2DCA8; border-radius:10px;
  padding:7px 9px; font-size:10.8px; color:#9A6B12; line-height:1.55;
}
.mc-relax .rl-ico{ flex:0 0 auto; font-size:11px; line-height:1.5; }

/* tighten the action row right under a plan card */
div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"]{
  margin-top:-2px; margin-bottom:16px;
}
div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stHorizontalBlock"]{
  gap:.4rem;
}
[data-testid="stHorizontalBlock"]{ gap:.5rem; }

/* ================= mobile ================= */
@media (max-width:480px){
  [data-testid="stMainBlockContainer"]{
    width:calc(100vw - 16px) !important;
    margin:8px auto 12px !important;
    min-height:calc(100vh - 20px);
    padding:0 12px 42px !important;
    border-radius:27px;
  }
  .hero{ margin:0 -12px 10px; padding:22px 14px 13px; border-radius:26px 26px 20px 20px; }
  .hero-mark{ width:46px; height:46px; flex-basis:46px; font-size:24px; border-radius:15px; }
  .hero .logo{ font-size:23px; letter-spacing:1px; }
  .hero-tag{ font-size:10.5px; }
  .data-badges{ gap:5px; margin-top:12px; }
  .data-badges span{ font-size:10px; padding:3px 8px; }
  .stTabs [data-baseweb="tab"] p{ font-size:11.5px !important; }
  .stTabs [data-baseweb="tab"]{ height:36px; }
  .stat{ padding:10px; gap:8px; }
  .stat .num{ font-size:19px; }
  .stat .si{ width:31px; height:31px; flex-basis:31px; font-size:15px; }
  .heat{ gap:4px; }
  .heat .hc{ padding:7px 1px 6px; border-radius:10px; }
  .heat .hc span{ font-size:8px; }
  .meal-card{ padding:13px 13px 12px; border-radius:20px; }
  .dish{ font-size:12.8px; gap:7px; }
  .ms .v{ font-size:13px; }
  .ms.price .v{ font-size:17px; }
  .ai-txt{ font-size:11.5px; }
  .hint{ font-size:11px; line-height:1.68; padding:8px 10px; }
  div[data-testid="stTextInputRootElement"] input::placeholder{ font-size:13px; }

  /* 快选条手机适配：字号收紧、chips 触控高度保持 ≥32px、不横溢 */
  .heard-row{ flex-wrap:wrap; }
  .heard-row .hk{ flex:0 0 auto; }
  .heard-row .hv{ flex:1 1 100%; padding-left:24px; }
  .qb-head .qb-s, .qb-row .qb-s{ font-size:10px; }
  .qb-row .qb-bval{ font-size:20px; }
  .qb-ticks{ padding:0 8px; }
  .qb-ticks span{ font-size:9.5px; }
  /* 场景 / 辣度：手机上改回上下堆叠，各占满宽，保证滑杆与刻度不挤 */
  div[data-testid="stHorizontalBlock"]:has(.qb-duo){ flex-direction:column !important; gap:8px !important; }
  div[data-testid="stHorizontalBlock"]:has(.qb-duo) > div[data-testid="stColumn"]{
    width:100% !important; flex:0 0 auto !important; padding:7px 11px 7px;
  }
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)){ gap:4px !important; }
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label{ min-height:32px; padding:5px 0; }
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label p{ font-size:10.5px !important; padding-top:2.5px !important; }  /* 10.5px 字号下字形偏心更小，补偿同样按比例收紧 */

  /* 方案卡操作行：手机上保持两按钮并排 + 放纵餐整行 */
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stHorizontalBlock"]{
    flex-direction:row !important; flex-wrap:wrap !important; gap:6px !important;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stColumn"]{
    width:auto !important; min-width:0 !important;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-child(1),
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-child(2){
    flex:1 1 40% !important;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-child(3){
    flex:1 1 100% !important;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-child(3) [data-testid="stCheckbox"]{
    width:100%; background:#FFF9F0; border:1px solid #F4E4CF; border-radius:12px;
    padding:8px 11px;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stColumn"]:nth-child(3) div[data-testid="stElementContainer"]:has([data-testid="stCheckbox"]){
    width:100% !important;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"]{
    margin-bottom:10px;
  }
  div[data-testid="stElementContainer"]:has(.meal-card) + div[data-testid="stLayoutWrapper"] [data-testid="stCheckbox"] label p{
    font-size:11.5px !important;
  }
}

/* ================= 四宫格「估算」角标 ================= */
.mc-stats{ position:relative; }
.ms-est{
  position:absolute; top:0; right:0; z-index:1;
  font-size:8.5px; font-weight:800; letter-spacing:.6px; line-height:1.5;
  color:#A8741A; background:#FDF0DA; border-left:1px solid #F3DDB4; border-bottom:1px solid #F3DDB4;
  padding:0 5px 0 6px; border-radius:0 0 0 8px; cursor:help;
}

/* ================= 决策小票：🧾 这顿怎么配出来的 ================= */
[data-testid="stMarkdownContainer"]:has(> .rcpt),
[data-testid="stMarkdownContainer"]:has(> .chal-banner),
[data-testid="stMarkdownContainer"]:has(> .twin),
[data-testid="stMarkdownContainer"]:has(> .chal-intro),
[data-testid="stMarkdownContainer"]:has(> .chal-say){ margin-bottom:0 !important; }
[data-testid="stExpander"]:has(.rcpt) details{
  background:linear-gradient(180deg,#FFF9EF 0%,#FFF5E6 100%) !important;
  border:1.5px dashed #EBC9A0 !important;
}
[data-testid="stExpander"]:has(.rcpt) summary p{ color:#B4612C !important; }
.rcpt{ color:#5C4432; font-variant-numeric:tabular-nums; padding:0 0 2px; }
.rc-sec{ padding:9px 0 8px; border-top:1px dashed #EED7BB; }
.rc-sec:first-child{ border-top:none; padding-top:4px; }
.rc-h{
  display:flex; align-items:center; gap:7px; margin-bottom:6px;
  font-size:12px; font-weight:900; color:#B4612C; letter-spacing:.5px;
}
.rc-no{
  width:18px; height:18px; flex:0 0 18px; border-radius:50%;
  display:grid; place-items:center; font-size:10px; font-weight:900; color:#fff;
  background:linear-gradient(145deg,#F59A55,#D96C2F);
}
.rc-chips{ display:flex; flex-wrap:wrap; gap:5px; }
.rc-chips span{
  font-size:11.5px; color:#7D624A; background:#fff; line-height:1.45;
  border:1px solid #F0DFC9; border-radius:9px; padding:2px 8px;
}
.rc-chips span:first-child{ background:#FDEEE0; border-color:#F7D6B6; color:#B4612C; font-weight:800; }
.rc-note{ margin-top:6px; font-size:10.5px; color:#A8917B; line-height:1.6; overflow-wrap:anywhere; }
.rc-line{ display:flex; align-items:baseline; gap:6px; font-size:12px; line-height:1.55; padding:1.5px 0; }
.rc-line .rc-l{ flex:0 1 auto; min-width:0; color:#6E5744; overflow-wrap:anywhere; }
.rc-line i{ flex:1 1 10px; min-width:10px; border-bottom:1.5px dotted #E3C29C; transform:translateY(-3px); }
.rc-line b{ flex:0 0 auto; font-weight:900; color:#4A3627; white-space:nowrap; }
.rc-line em{ flex:0 0 44px; text-align:right; font-style:normal; font-size:10.5px; color:#C08A5E; white-space:nowrap; }
.rc-sub{ font-size:10px; color:#B39A80; margin:-1px 0 2px 10px; line-height:1.5; }
.rc-line.rc-sum{ margin-top:4px; padding-top:5px; border-top:1px solid #F1DDC4; }
.rc-line.rc-sum .rc-l, .rc-line.rc-sum b{ color:#C4602A; font-weight:900; }
.rc-check{ display:flex; align-items:center; gap:9px; }
.rc-check b{
  flex:0 0 auto; font-size:16px; font-weight:900; color:#3F7C33; white-space:nowrap;
  background:#E9F5E4; border-radius:10px; padding:2px 9px;
}
.rc-check.warn b{ color:#B44436; background:#FBE3DF; }
.rc-check.none b{ color:#9A8470; background:#F3ECE2; }
.rc-check span{ font-size:11.5px; color:#6E5744; line-height:1.55; min-width:0; }
.rc-why{ font-size:12px; color:#5B4534; line-height:1.72; overflow-wrap:anywhere; }
.rc-foot{
  text-align:center; font-size:9.5px; color:#C2AA90; letter-spacing:1.2px;
  padding-top:7px; border-top:1px dashed #EED7BB;
}

/* ================= 拆台模式：给评委的刁难卡 ================= */
[data-testid="stExpander"]:has(.chal-intro) [data-testid="stBaseButton-secondary"]{
  min-height:44px !important; justify-content:flex-start !important;
  background:linear-gradient(180deg,#FFFDF9,#FFF4E6) !important;
  border:1.5px dashed #E9C39A !important;
}
[data-testid="stExpander"]:has(.chal-intro) [data-testid="stBaseButton-secondary"] p{
  font-size:13px !important; color:#7A4A26 !important; text-align:left;
}
.chal-intro{
  background:#FFF6EA; border:1px solid #F4E4CF; border-radius:12px;
  padding:7px 10px; font-size:11px; line-height:1.65; color:#82694F; margin-top:4px;
}
.chal-say{ font-size:10.5px; color:#A08770; line-height:1.5; margin:-5px 3px 6px; overflow-wrap:anywhere; }
.chal-banner{
  display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  background:linear-gradient(90deg,#FFF1DF,#FFF7EE); border:1px solid #F3D3AE;
  border-radius:14px; padding:8px 12px; font-size:12px; color:#8A4F22; line-height:1.5;
}
.chal-banner b{ color:#C4602A; }
.chal-banner .t{
  margin-left:auto; font-weight:900; color:#C4602A; white-space:nowrap;
  font-variant-numeric:tabular-nums;
}
.twin{ background:#FFFBF5; border:1px solid #F3E4D0; border-radius:14px; padding:9px 10px 10px; }
.twin-g{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.twin-col{ background:#fff; border:1px solid #F0DFC9; border-radius:11px; padding:7px 9px; min-width:0; }
.twin-h{
  display:flex; justify-content:space-between; gap:6px; margin-bottom:3px;
  font-size:11px; font-weight:900; color:#8A6C52;
}
.twin-h span{ color:#C4602A; font-variant-numeric:tabular-nums; white-space:nowrap; }
.twin-row{
  display:flex; justify-content:space-between; gap:6px; padding:2px 0;
  font-size:11.5px; color:#4A3627; border-top:1px dashed #F5EADC;
  font-variant-numeric:tabular-nums;
}
.twin-row code{
  font-family:ui-monospace,Consolas,"Courier New",monospace; font-size:11px;
  color:#6B4C9E; background:#F3EDFB; border-radius:5px; padding:0 4px;
}
.twin-ok, .twin-bad{
  margin-top:8px; border-radius:10px; padding:5px 10px; text-align:center;
  font-size:12px; font-weight:900; line-height:1.5;
}
.twin-ok{ color:#3F7C33; background:#E9F5E4; }
.twin-bad{ color:#B44436; background:#FBE3DF; }
@media (max-width:480px){
  .rc-line{ font-size:11.5px; }
  .rc-line em{ flex-basis:38px; }
  .twin-g{ gap:6px; }
  .twin-row{ font-size:10.5px; }
}
</style>
"""

CIRC = '①②③④⑤'
CAT_EMOJI = {'主食': '🍚', '荤菜': '🍗', '半荤': '🍖', '素菜': '🥬', '汤': '🥣', '饮品': '🥤'}
# 四宫格「估算」角标的悬停说明（title 属性：只用全角引号，不含半角双引号）
EST_TITLE = ('价格为实采菜价（称重菜＝单价×建议克数）；热量/蛋白质/油脂按同一套算式估算'
             '（麦当劳为官方公示值），克重与油克系数待实测，仅供参考、非医疗建议。'
             '算式见「关于 · 这个数字怎么来的」')

WIN_EMOJI = {
    '粤式风味': '🥟', '大众餐': '🍛', '水饺鲜生': '🥟', '南昌拌粉': '🍜',
    '重庆小面': '🌶️', '匠心热卤饭': '🍖', '牛东家牛肉饭': '🍲', '煲仔饭': '🍚',
    '淮南牛肉汤': '🥣', '麻辣香锅': '🌶️', '麦当劳': '🍔', '土耳其烤肉': '🥙',
}


def dish_emoji(name, cat=None):
    for kw, e in [('水饺', '🥟'), ('汤圆', '🍡'), ('鱼', '🐟'), ('虾', '🍤'), ('鸡', '🍗'),
                  ('牛', '🥩'), ('猪', '🥩'), ('肉', '🍖'), ('豆腐', '🧈'), ('粉', '🍜'),
                  ('面', '🍜'), ('饭', '🍚'), ('堡', '🍔'), ('冰淇淋', '🍦'), ('新地', '🍦'),
                  ('圆筒', '🍦'), ('咖啡', '☕'), ('可乐', '🥤'), ('蛋', '🥚'), ('汤', '🥣'), ('粥', '🥣')]:
        if kw in name:
            return e
    if cat and cat in CAT_EMOJI:
        return CAT_EMOJI[cat]
    return '🍽️'


def hint_html(text):
    return f'<div class="hint">{text}</div>'


def heard_receipt_html(rc):
    """三色听懂回执：✅ 你说的（origin=user）· 📌 我先默认的（origin=default）·
    🙁 这个我还管不了（葱姜蒜等闭集外忌口，没有则整行不显示）。产品语言、零算法词；
    文本全部 HTML 转义。rc 结构见 app.parsed_receipt_of。"""
    e = html.escape

    def row(cls, ico, key, val):
        return (f'<div class="heard-row {cls}"><span class="hk">{ico} {key}</span>'
                f'<span class="hv">{val}</span></div>')

    rows = []
    if rc.get('user'):
        rows.append(row('ok', '✅', '你说的', ' · '.join(e(x) for x in rc['user'])))
    if rc.get('dflt'):
        rows.append(row('df', '📌', '我先默认的', ' · '.join(e(x) for x in rc['dflt'])))
    if rc.get('unsupported'):
        words = '、'.join(e(w) for w in rc['unsupported'])
        rows.append(row('no', '🙁', '这个我还管不了',
                        f'{words}——菜品档案没标到这么细，怕漏不能装懂'))
    if not rows:
        return ''
    src = e(rc.get('src') or '')
    src_html = f'<span class="heard-src">（{src}）</span>' if src else ''
    return f'<div class="heard"><div class="heard-head">🤖 听懂啦{src_html}</div>{"".join(rows)}</div>'


def plan_card(p, reason, idx):
    status_cls = {'推荐': 'pill-ok', '放宽版': 'pill-soft', '建议': 'pill-hard'}.get(p['status'], 'pill-soft')
    self_pill = '<span class="pill pill-self">按克自选</span>' if p['label'] == '自选' else ''
    tier = p.get('tier')

    def _dish_tag(it):
        """只标「套餐」（套餐档位内的菜）；加菜/普通菜不标标签，改为行尾显示单价。"""
        if tier and it['pricing'] == '套餐':
            return '<span class="d-w d-w-set">套餐</span>'
        return '<span class="d-w">称重</span>' if it['pricing'] == '称重' else ''

    def _dish_price(it):
        """行尾单价：套餐内菜不单标价（价格在档位行），其余菜显示各自的实付价。"""
        if tier and it['pricing'] == '套餐':
            return ''
        price = it.get('price')
        if price is None:
            return ''
        return f'<span class="d-p">¥{price:g}</span>'

    dishes = ''.join(
        f'<div class="dish"><span class="d-e">{dish_emoji(it["name"], it.get("cat"))}</span>'
        f'<span class="d-n">{it["name"]}</span>'
        + _dish_tag(it)
        + _dish_price(it)
        + f'<span class="d-g">{it["grams"]:g}g</span></div>'
        for it in p['items'])
    tier_html = ''
    if tier:
        t = tier
        rice = f' · 含米饭{t["rice_g"]:g}g' if t['mode'] in ('含米饭', '米饭+1元') else ''
        extras = [it for it in p['items'] if it['pricing'] != '套餐']
        extra_txt = ''
        if extras:
            names = '、'.join(it['name'] for it in extras)
            extra_wins = '、'.join(sorted({it['win'] for it in extras}))
            extra_txt = f' ｜ 加菜：{names}（{extra_wins}）'
        tier_html = (f'<div class="tier-line"><span>🍱</span><span>{t["n_meat"]}荤{t["n_veg"]}素档 '
                     f'{t["price"]:g}元{rice}{extra_txt}</span></div>')
    relax = ''
    if p.get('relax'):
        cn = {'槽_主': '主食', '槽_荤': '荤菜', '槽_素': '素菜', '热量下': '热量下限', '热量上': '热量上限',
              '蛋白': '蛋白', '油': '油', '素量': '素菜量', '耗时': '耗时'}
        relax = ('<div class="mc-relax"><span class="rl-ico">⚠️</span><span>诚实披露：本餐放宽了 '
                 + '、'.join(cn.get(k, k) for k in p['relax']) + '，以现场为准</span></div>')
    tag = p.get('tag') or ''
    tag_pill = f'<span class="pill pill-tag mc-tag">🏷 {tag}</span>' if tag else ''
    bars = p.get('bars')
    bars_html = ''
    if isinstance(bars, (list, tuple)) and len(bars) == 3:
        rows = ''
        for name, raw in zip(('口味', '营养', '性价比'), bars):
            try:
                v = int(round(float(raw)))
            except (TypeError, ValueError):
                continue
            v = max(0, min(100, v))
            rows += (f'<div class="bar-row"><span class="bar-k">{name}</span>'
                     f'<span class="bar-track"><i style="width:{v}%"></i></span>'
                     f'<span class="bar-v">{v}</span></div>')
        if rows:
            bars_html = (f'<div class="mc-bars">{rows}'
                         '<div class="bar-note">三维为本次候选池内相对位置 · 满分 100</div></div>')
    wins = ''.join(f'<span>{w}</span>' for w in p['wins'])
    feat = ' featured' if idx == 0 else ''
    return f"""<div class="meal-card{feat}" style="animation-delay:{idx * 0.12:.2f}s">
 <div class="mc-head"><div class="mc-idx">{idx + 1}</div>
  <div class="mc-headl"><div class="mc-l1"><b>第{idx + 1}套</b>
   <span class="pill {status_cls}">{p['status']}</span>{self_pill}</div>
   <div class="mc-l2">📍<span>{p['cant'][0] if p.get('cant') else '校内'}</span></div></div>
  {tag_pill}</div>
 <div class="mc-wins">{wins}</div>
 <div class="mc-dishes">{dishes}</div>{tier_html}
 <div class="mc-stats">
  <div class="ms price"><span class="v">¥{p['PI']:g}</span><span class="k">价格</span></div>
  <div class="ms"><span class="v">{p['E']:g}<i>kcal</i></span><span class="k">热量</span></div>
  <div class="ms"><span class="v">{p['Q']:g}<i>g</i></span><span class="k">蛋白质</span></div>
  <div class="ms"><span class="v">{p['O']:g}<i>g</i></span><span class="k">油脂</span></div>
  <span class="ms-est" title="{EST_TITLE}">估算</span>
 </div>{bars_html}
 <div class="mc-ai"><div class="ai-ava">🤖</div>
  <div class="ai-bub"><span class="ai-name">干饭小助手</span>
   <div class="ai-txt">{html.escape(reason)}</div></div></div>{relax}</div>"""


def comment_card(win, stars, tag, txt):
    ava = WIN_EMOJI.get(win, '🍽️')
    star_html = ''.join('<span>★</span>' if i < stars else '<span class="off">★</span>' for i in range(5))
    return (f'<div class="cmt"><div class="cmt-ava">{ava}</div><div class="cmt-main">'
            f'<div class="cmt-top"><b>{win}</b><span class="stars">{star_html}</span></div>'
            f'<div class="cmt-txt">{txt}</div>'
            f'<div class="cmt-tags"><span class="tag">{tag}</span></div></div></div>')


# ---------------- 决策小票 / 拆台模式 ----------------
SPICE_CN = ['不辣', '微辣', '能吃辣']

# 出餐自检 17 项：复用 engine/run_master.py 的断言（check_plan 逐套 + check_top3 三套整体），
# 按违规信息前缀归成产品语言；前 6 项是小票主行展示的大项。
SELF_CHECKS = [
    ('预算', ('预算超支',)),
    ('忌口', ('忌口命中',)),
    ('辣度', ('辣度超限',)),
    ('热量', ('能量出带',)),
    ('同一食堂', ('跨食堂',)),
    ('售罄', ('售罄窗口',)),
    ('供应时段', ('时段不符',)),
    ('蛋白', ('蛋白不足',)),
    ('油脂', ('油超上限',)),
    ('减脂不油炸', ('减脂含油炸',)),
    ('现做≤1道', ('现做>1',)),
    ('同名菜不重复', ('同名菜重复',)),
    ('克重与计价', ('称重克重出带', '称重价不符', '克重与主表不符')),
    ('套餐档位', ('档位基数不符', '套餐价未按档位入账')),
    ('米饭入账', ('米饭未入', '米饭热量未入账')),
    ('三套不重样', ('Top3 签名重复',)),
    ('窗口口味分散', ('内容通道>2', '同窗口>2')),
]
SPREAD_CHECK = '窗口口味分散'


def sig_code(sig):
    """方案签名 → 6 位短码（同一方案无论现场算还是读出来，短码都一样）。"""
    blob = json.dumps(sig, ensure_ascii=False, sort_keys=True, default=sorted)
    return hashlib.sha1(blob.encode('utf-8')).hexdigest()[:6].upper()


def self_check(idx, req, tops, quota=True):
    """出餐自检（运行时）：对本次展示的方案逐套跑 run_master.check_plan、整体跑 check_top3，
    违规信息按 SELF_CHECKS 前缀归到 17 项。quota=False（随机配 / 换一批本就不设分散配额）
    或方案含「为凑满三套降级补位」时，分散项记为不适用（skipped），不计入分母。
    返回 dict(total, passed, failed=[项], skipped=[项], extra=[未归类违规], n=方案数)。"""
    import core
    import run_master
    tops = list(tops or [])
    req = dict(req, taboo=set(req.get('taboo') or ()))
    scen = core.resolve(req['scenario'], req.get('lazy', False))
    msgs = []
    for p in tops:
        try:
            msgs += run_master.check_plan(idx, req, scen, p)
        except (KeyError, TypeError, ValueError) as e:      # 方案与主表对不上：如实记异常，不崩
            msgs.append(f'数据对不上 {e!r}')
    if tops:
        hashable = [dict(p, sig=json.dumps(p['sig'], ensure_ascii=False, sort_keys=True, default=sorted))
                    for p in tops]                          # 缓存读出的 sig 是 list，转成可哈希
        msgs += run_master.check_top3(req, dict(top3=hashable))
    skipped = [SPREAD_CHECK] if (not quota or any(p.get('degraded') for p in tops)) else []
    failed = [name for name, pfx in SELF_CHECKS
              if name not in skipped and any(m.startswith(pfx) for m in msgs)]
    known = tuple(pf for _, pfx in SELF_CHECKS for pf in pfx)
    extra = [m for m in msgs if not m.startswith(known)]
    total = len(SELF_CHECKS) - len(skipped)
    return dict(total=total, passed=total - len(failed), failed=failed, skipped=skipped,
                extra=extra, n=len(tops))


TABOO_ORDER = ['猪', '牛', '羊', '海鲜', '蛋', '奶', '花生', '芝麻', '麸质', '香菜', '内脏']


def taboo_list(req):
    """忌口按常用顺序排（猪牛羊…内脏），闭集外的排最后。"""
    tb = set(req.get('taboo') or ())
    return [t for t in TABOO_ORDER if t in tb] + sorted(tb - set(TABOO_ORDER))


def _cn_count(n):
    return {1: '一', 2: '两', 3: '三'}.get(n, str(n))


def step_labels(req):
    """小票「做了什么筛选」每一步的产品语言标签（键与 core.prefilter_trace 的 step key 对应）。"""
    import core
    taboo = taboo_list(req)
    spice = SPICE_CN[max(0, min(2, int(req.get('spice_max', 2))))]
    return dict(
        period=f"{req['period']}餐 {req['asof']} 在售",
        taboo=(f"去忌口（{'/'.join(taboo)}）" if len(taboo) <= 4 else f'去忌口（{len(taboo)} 项）')
        if taboo else '去忌口（没忌口）',
        spice=f'去超辣（只要{spice}）',
        budget=f"去超预算（单道就超 {float(req['B']):g} 元）",
        fried='减脂：不吃油炸',
        lazy=f"懒人：步行+排队+出餐 ≤{core.PRM['T_LAZY']:g} 分钟",
        other='其他条件')


def bottleneck_text(req, trace):
    """诚实页一句话诊断：筛到 0 道时指出卡在哪一步；还剩菜却凑不出整餐时如实说。"""
    if trace['alive'] == 0:
        worst = max(trace['steps'], key=lambda s: s['cut'], default=None)
        if worst and worst['cut']:
            label = step_labels(req).get(worst['key'], worst['label'])
            return f'这回卡在「{label}」这一步：筛掉 {worst["cut"]} 道，一道不剩。'
        return '这回筛到最后一道菜都不剩。'
    return f'筛完还剩 {trace["alive"]} 道，但凑不出一顿过得了自检的整餐。'


def receipt_html(req, src, trace, check, mode='fixed', n_plans=0, elapsed=None, avoid_n=0, twin=None):
    """决策小票：①听懂了什么 ②做了什么筛选 ③出餐自检 ④为什么是这几套——产品语言、零算法词。
    数字全部来自这一次的真实计算（trace=core.prefilter_trace，check=self_check）；文本一律转义。
    mode：fixed 按条件配 / random 随机抽条件 / reshuffle 再换一批 / challenge 刁难卡 / twin 同句连点两次。"""
    import core
    e = html.escape
    taboo = taboo_list(req)
    spice = SPICE_CN[max(0, min(2, int(req.get('spice_max', 2))))]
    t_lazy = core.PRM['T_LAZY']
    chips = [req['scenario'], f"≤{float(req['B']):g} 元", f"{req['period']}餐 {req['asof']}",
             req['anchor'], f'辣度：{spice}', ('忌：' + '/'.join(taboo)) if taboo else '没忌口']
    if req.get('lazy'):
        chips.append(f'懒人 ≤{t_lazy:g} 分钟')
    chips_html = ''.join(f'<span>{e(str(c))}</span>' for c in chips)

    labels = step_labels(req)
    lines = [f'<div class="rc-line"><span class="rc-l">全部实采菜品</span><i></i>'
             f'<b>{int(trace["total"])} 道</b><em></em></div>']
    for s in trace['steps']:
        lines.append(f'<div class="rc-line"><span class="rc-l">{e(labels.get(s["key"], s["label"]))}</span>'
                     f'<i></i><b>{int(s["left"])}</b><em>−{int(s["cut"])}</em></div>')
        if s.get('note'):
            lines.append(f'<div class="rc-sub">{e(s["note"])}</div>')
    lines.append(f'<div class="rc-line rc-sum"><span class="rc-l">剩下可选</span><i></i>'
                 f'<b>{int(trace["alive"])} 道</b><em></em></div>')

    n_cn = _cn_count(n_plans)
    if not check or not check.get('n'):
        chk = ('<div class="rc-check none"><b>未出餐</b><span>这次一套都没配出来，没有可检的方案——'
               '宁可不出，也不出错的。</span></div>')
    else:
        ok = not check['failed'] and not check['extra']
        badge = f"{check['passed']}/{check['total']} {'✓' if ok else '⚠'}"
        big = '·'.join(name for name, _ in SELF_CHECKS[:6])
        if ok:
            body = f"{big} 等 {check['total']} 项，{n_cn}套逐项过"
        else:
            bad = check['failed'] + (['数据对不上'] if check['extra'] else [])
            body = '未通过：' + '、'.join(bad) + '（如实显示，不遮掩）'
        rest = '·'.join(name for name, _ in SELF_CHECKS[6:] if name not in check['skipped'])
        note = f'其余各项：{rest}'
        if check['skipped']:
            why_skip = '随机挑的这批本就不设分散要求' if mode in ('random', 'reshuffle') else '为凑满三套主动放宽'
            note += f"；「{'、'.join(check['skipped'])}」{why_skip}，不计入"
        chk = (f'<div class="rc-check{"" if ok else " warn"}"><b>{e(badge)}</b><span>{e(body)}</span></div>'
               f'<div class="rc-note">{e(note)}</div>')

    alive = int(trace['alive'])
    if n_plans == 0:
        head = '为什么一套都没有'
        if alive == 0:
            worst = max(trace['steps'], key=lambda s: s['cut'], default=None)
            where = (f"（卡在「{labels.get(worst['key'], worst['label'])}」这一步）"
                     if worst and worst['cut'] else '')
            why = f'筛到最后一道菜都不剩{where}。'
        else:
            why = f'剩下的 {alive} 道凑不出一顿过得了自检的整餐。'
        why += '我不硬凑，也绝不偷偷放宽忌口和预算——换个条件再来。'
    else:
        head = f'为什么是这{n_cn}套'
        if mode == 'twin' and twin:
            t = ' / '.join(f"{r['elapsed']:g} 秒" for r in twin.get('runs', []))
            why = (f'同一句话现场连算两遍（{t}），两遍的{n_cn}套逐套一致——同条件可复现。想看别的组合，点下方「再换一批」。'
                   if twin.get('same') else f'同一句话现场连算两遍（{t}），两遍结果不一致——如实摆在上面，不遮掩。')
        elif mode == 'challenge':
            why = (f'刁难卡现场实算 {float(elapsed or 0):g} 秒得出（不读预存结果）；同样条件再算一遍还是这{n_cn}套，'
                   '「同句连点两次」卡可当场验。想看别的组合，点下方「再换一批」。')
        elif mode == 'random':
            why = (f'这次的条件是随机抽的；在这组条件下挑了{n_cn}套彼此不重样的。'
                   '想按固定条件配就拖一下快选条，想换一批点「再换一批」。')
        elif mode == 'reshuffle':
            why = f'这批是同一条件下随机换的{n_cn}套，每次点「再换一批」都不一样。'
        else:
            why = (f'从剩下的 {alive} 道里，挑口味、营养、价钱最能兼顾、彼此又不重样的{n_cn}套'
                   + ('，并避开你近 7 天打卡吃过的组合' if avoid_n else '')
                   + f'；同样的条件再配一次还是这{n_cn}套（可复现）。想看别的组合，点下方「再换一批」。')
    sec = lambda no, title, body: (f'<div class="rc-sec"><div class="rc-h"><span class="rc-no">{no}</span>'
                                   f'{e(title)}</div>{body}</div>')
    return ('<div class="rcpt">'
            + sec(1, '听懂了什么', f'<div class="rc-chips">{chips_html}</div>'
                                  f'<div class="rc-note">来源：{e(src or "—")}</div>')
            + sec(2, '做了什么筛选', ''.join(lines))
            + sec(3, '出餐自检', chk)
            + sec(4, head, f'<div class="rc-why">{e(why)}</div>')
            + '<div class="rc-foot">— 本小票按这一次的真实计算生成 —</div></div>')


# 拆台模式：给评委的刁难卡（题面走与用户完全相同的一句话解析；点卡＝no_cache 现场实算）
CHALLENGES = [
    dict(key='b5', ico='💸', title='预算 5 元', say='5块钱，中午吃饱', test='预算是硬上限，绝不超支'),
    dict(key='taboo', ico='🚫', title='忌口叠满', say='不吃猪牛羊海鲜蛋奶花生芝麻麸质香菜内脏，20块',
         test='11 项忌口一次全开'),
    dict(key='night', ico='🌙', title='夜宵 23:00', say='晚上11点，宿舍区，想吃夜宵，20块',
         test='过了售罄时点的窗口不推'),
    dict(key='lazy', ico='🛋️', title='懒人 + 现做', say='赶时间，宿舍区，中午12点，想吃现做的热乎饭，20块',
         test='步行+排队+现做出餐算进 15 分钟；「想吃现做」听不懂就不硬猜'),
    dict(key='sold', ico='⏰', title='售罄时段', say='中午1点半，20块', test='13:30 多数窗口已过售罄时点'),
    dict(key='twin', ico='🔁', title='同句连点两次', say='减脂，18块，不吃香菜', twin=True,
         test='现场连算两遍，并排比对方案签名'),
]
CHALLENGE_BY_KEY = {c['key']: c for c in CHALLENGES}


def challenge_intro_html():
    return ('<div class="chal-intro">点任意一张＝<b>不读预存结果</b>、现场实算并显示耗时；配不出就进诚实页。'
            '刁难卡按纯条件算（不带你的打卡记录），方便复现对照。</div>')


def challenge_say_html(c):
    return f'<div class="chal-say">「{html.escape(c["say"])}」· {html.escape(c["test"])}</div>'


def _secs(x):
    x = float(x or 0)
    return '<0.01s' if x < 0.01 else f'{x:.2f}s'


def challenge_banner_html(ch):
    runs = ch.get('runs') or []
    t = ' / '.join(_secs(r['elapsed']) for r in runs)
    label = f'现场实算 {len(runs)} 遍 {t}' if len(runs) > 1 else f'现场实算 {t}'
    return (f'<div class="chal-banner"><span>{html.escape(ch["ico"])} 刁难卡 <b>{html.escape(ch["title"])}</b>'
            f' · 不读预存结果</span><span class="t">{html.escape(label)}</span></div>')


def twin_html(ch):
    """同句连点两次：两遍现场实算的方案签名并排（短码 + 价格），底部给一致/不一致结论。"""
    cols = ''
    for i, r in enumerate(ch.get('runs') or []):
        rows = ''.join(f'<div class="twin-row"><span>{CIRC[j]} ¥{float(pr):g}</span>'
                       f'<code>{html.escape(code)}</code></div>' for j, (code, pr) in enumerate(r['plans']))
        cols += (f'<div class="twin-col"><div class="twin-h">第 {i + 1} 遍<span>{_secs(r["elapsed"])}</span></div>'
                 f'{rows or "<div class=twin-row><span>（配不出）</span></div>"}</div>')
    verdict = ('<div class="twin-ok">✓ 两遍的方案签名逐套一致 · 同条件可复现</div>' if ch.get('same')
               else '<div class="twin-bad">✗ 两遍结果不一致（如实显示）</div>')
    return f'<div class="twin"><div class="twin-g">{cols}</div>{verdict}</div>'


# ---------------- 关于 / 诚实边界 ----------------
def about_cards(n_dishes, n_windows, n_std):
    """关于页卡片（图标, 标题, 正文 HTML）。正文只含本文件写死的文案与整数，无外部输入。"""
    return [
        ('🍚', '数据', f'{n_dishes} 道菜、{n_windows} 个窗口、6 个食堂区，全部实地采集人工转录；'
                     f'标准菜名 {n_std} 个，营养按「主料构成 × 食物成分表」可复现算式计算。'),
        ('⚖️', '称重自选', '仅水饺鲜生（1.88 元/50g，荤素同价）按克建模，其余称重窗口不建模。'),
        ('🚧', '待实测标注', '拥挤等待、步行时长、油克系数、售罄时点为 AI 参数，主表来源列均标「待实测」；'
                        '菜品克重标「AI估计待实测」。我们保留标注，不伪装成实测值。'),
        ('🥗', '营养置信', '麦当劳为官方公示级；其余为估算级，数值供参考，<b>不构成医疗建议</b>。'),
        ('🌙', '诚实降级', '条件太苛刻时给「放宽版 / 建议」并写明放宽项；配不出就说配不出，'
                       '并给「预算 +3 元 / 去掉忌口」一键重试——忌口与预算绝不偷偷放宽。'),
        ('🔒', '隐私', '位置只到食堂锚点粒度；打卡记录只存在运行决策机的这台机器上'
                     '（云端演示若磁盘不可写，就只留在你这次会话里），不上传第三方。'),
        ('🧠', 'AI 链路', '自然语言 → 结构化需求 → 整餐搭配 → 一句人话解释。'
                        '无 API Key 时自动切换规则解析，功能不断线。'),
        ('📏', '周报达标口径', '周报「热量达标率」：落在场景能量带内算达标，并在能量带上限外另设 '
                          '<b>+150kcal 宽容带</b>（下限不放宽）——临界多吃一口不判失败。'),
        ('📊', '三维分数口径', '方案卡三维分数（口味 / 营养 / 性价比）是该方案在<b>本次候选池内的相对位置</b>，'
                          '满分 100；换了条件候选池就变了，<b>跨条件不可直接比较</b>。'),
        ('⚡', '解释从哪来', '随机配与「再换一批」的解释由<b>规则模板</b>生成（不调用大模型，以保住 1–2 秒体验）；'
                        '首次配饭的解析与解释才走大模型（无 Key 时全部规则兜底）。'),
        ('🔢', '这个数字怎么来的', '方案卡四宫格里，<b>价格是实采菜价</b>（称重菜＝单价 × 建议克数）；'
                              '热量 / 蛋白质 / 油脂对每道菜都用<b>同一套算式</b>：标准菜名 → 主料构成 × '
                              '《中国食物成分表》→ 按烹饪方式与用油系数修正（麦当劳的热量 / 蛋白用官方公示值，'
                              '油脂不单列计入）。'
                              '克重与油克系数在主表来源列标「待实测」，所以这几个数带「估算」角标——'
                              '<b>仅供参考，非医疗建议</b>。'),
        ('🧾', '决策小票', '每次出餐，三张方案卡上方都有「🧾 这顿怎么配出来的」：听懂了什么、一步步筛掉了多少菜、'
                        '出餐自检过了几项、为什么是这三套——小票上的数都是这一次的真实计算。'),
        ('🧪', '给评委的刁难卡', '「配饭」页「🧪 给评委的刁难卡」共 6 张：预算 5 元 / 忌口叠满 / 夜宵 23:00 / '
                            '懒人+现做 / 售罄时段 / 同句连点两次。点卡即<b>不读预存结果、现场实算并显示耗时</b>；'
                            '配不出就进诚实页；同句连点两次会并排比对两遍的方案签名。'),
    ]


def about_html(n_dishes, n_windows, n_std):
    cards = ''.join(f'<div class="ab-card"><div class="ab-ico">{ico}</div><div>'
                    f'<div class="ab-t">{t}</div><div class="ab-p">{p}</div></div></div>'
                    for ico, t, p in about_cards(n_dishes, n_windows, n_std))
    return f'<div class="about-list">{cards}</div>'


# ---------------- 打卡与周报 ----------------
def _read_json(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return None


def load_checkins():
    """打卡数据：本机文件优先；不存在时回落种子（云端首开周报不空白）；
    只读文件系统上写不进去时，回落到仅本会话（见 save_checkin）。"""
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
        if get_script_run_ctx() is not None:
            import streamlit as st
            fb = st.session_state.get('_checkins_session')
            if fb is not None:
                return fb
    except Exception:
        pass
    if os.path.exists(CHECKIN_PATH):
        data = _read_json(CHECKIN_PATH)
        if isinstance(data, list):
            return data
    if os.path.exists(SEED_PATH):                    # 云端：checkins.json 不存在 → 用种子
        data = _read_json(SEED_PATH)
        if isinstance(data, list):
            return data
    return []


def _atomic_write_json(path, obj):
    """tmp + os.replace 原子写（参考 engine/cache.py 的 put 做法）。
    Windows 多进程下目标文件可能被短暂占用，重试几次；失败抛 OSError。"""
    tmp = path + f'.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.2)
    try:
        os.remove(tmp)
    except OSError:
        pass
    raise OSError(f'atomic replace failed: {path}')


def save_checkin(entry):
    """追加一条打卡。原子写；写失败（如云端只读文件系统）降级为仅本会话，不报错。"""
    arr = list(load_checkins())
    arr.append(entry)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        _atomic_write_json(CHECKIN_PATH, arr)
    except OSError:
        try:                                          # 只读 FS：仅本会话可见，评委会话互不污染
            from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
            if get_script_run_ctx() is not None:
                import streamlit as st
                st.session_state['_checkins_session'] = arr
        except Exception:
            pass


def clear_checkins():
    """清空打卡：优先写空列表文件（否则种子会再次顶上），并清掉会话级兜底。"""
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
        if get_script_run_ctx() is not None:
            import streamlit as st
            st.session_state.pop('_checkins_session', None)
    except Exception:
        pass
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        _atomic_write_json(CHECKIN_PATH, [])
    except OSError:
        try:
            os.remove(CHECKIN_PATH)                   # 连写空文件都不行 → 至少试着删掉
        except OSError:
            pass


def demo_week(monday=None):
    """「填入示例一周」演示数据（与 data/seed_checkins.json 同源；对齐到本周周一）。"""
    monday = monday or (date.today() - timedelta(days=date.today().weekday()))
    demo = [(0, '午', '减脂', 14.0, 604.7, '正常'), (0, '晚', '均衡', 15.5, 745.3, '正常'),
            (1, '午', '减脂', 11.76, 632.0, '正常'), (1, '晚', '均衡', 16.0, 788.0, '正常'),
            (2, '午', '省钱', 10.5, 640.0, '正常'), (2, '晚', '增肌', 20.9, 833.6, '正常'),
            (3, '午', '减脂', 13.76, 746.9, '正常'), (3, '晚', '均衡', 18.5, 763.1, '正常'),
            (4, '午', '均衡', 14.5, 665.9, '正常'), (4, '晚', '均衡', 27.9, 660.5, '放纵'),
            (5, '午', '省钱', 12.0, 590.0, '放纵')]
    out = []
    for off, per, scen, price, kcal, kind in demo:
        d = (monday + timedelta(days=off)).isoformat()
        out.append(dict(date=d, ts=d + 'T12:30:00', period=per, scenario=scen,
                        price=price, kcal=kcal, protein=35.0, oil=6.0,
                        items=['示例搭配（演示）'], wins=['粤式风味'], kind=kind))
    return out


def week_stats(logs, scenario_bands=None):
    """本周（周一起）聚合：N餐/正常/放纵/热量达标率/花费 + 近7天热力图。"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week = [l for l in logs if l.get('date') >= monday.isoformat()]
    n = len(week)
    cheat = sum(1 for l in week if l.get('kind') == '放纵')
    normal = n - cheat
    cost = round(sum(l.get('price', 0) for l in week), 2)
    inband = 0
    for l in week:
        band = (scenario_bands or {}).get(l.get('scenario'), (400, 900))
        if band[0] <= l.get('kcal', 0) <= band[1] + 150:
            inband += 1
    rate = round(100 * inband / n) if n else 0
    days = []
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        dl = [l for l in week if l['date'] == d]
        days.append(dict(date=d, n=len(dl), kcal=sum(l.get('kcal', 0) for l in dl),
                         weekday='一二三四五六日'[i]))
    return dict(n=n, normal=normal, cheat=cheat, cheat_left=max(0, 3 - cheat),
                cost=cost, rate=rate, days=days)


# ---------------- 预置评论（演示样例，非真实用户数据） ----------------
COMMENTS = [
    ('粤式风味', 5, '减脂友好', '蒸水蛋+剁椒蒸鱼是本命组合，12块两荤一素还含饭，减脂期食堂之光。'),
    ('粤式风味', 4, '出餐快', '即取不用等，下课冲过去两分钟搞定，清蒸南瓜甜糯。'),
    ('大众餐', 4, '分量足', '按份打菜阿姨手不抖，酸菜鱼给得实在，就是饭点要排队。'),
    ('大众餐', 3, '口味稳', '咖喱鱼蛋有点咸，配米饭刚好，不知道吃啥时的安全牌。'),
    ('水饺鲜生', 5, '按克精算', '荤素同价1.88元/50g，多拿肉不多花钱只多热量，健身党狂喜。'),
    ('水饺鲜生', 4, '现煮要等', '三鲜水饺现煮大概等4分钟，皮滑馅足，值得。'),
    ('南昌拌粉', 5, '性价比', '经典素拌粉9块钱吃到撑，卤豆泡2块必加，卤香很正。'),
    ('南昌拌粉', 4, '地方味', '江西辣鸡爪拌粉是真的辣，嗜辣星人冲，不吃辣慎点。'),
    ('重庆小面', 4, '出餐快', '小面小份7块，加份杂酱4块，11块钱的快乐。'),
    ('重庆小面', 3, '辣度预警', '老麻抄手麻到嘴唇跳舞，建议先从清汤抄手入门。'),
    ('匠心热卤饭', 5, '招牌', '金牌猪脚饭15块，猪脚炖得软糯脱骨，卤汁拌饭一绝。'),
    ('匠心热卤饭', 4, '加料自由', '卤蛋1块5、卤海带2块，加料便宜，预算紧也能吃好。'),
    ('牛东家牛肉饭', 4, '蛋白足', '招牌牛肉饭15.8，牛肉给得足，黑椒味比番茄味更下饭。'),
    ('牛东家牛肉饭', 3, '略油腻', '香辣大鸡排饭鸡排够大，但油炸的减脂期还是算了。'),
    ('煲仔饭', 4, '锅巴香', '香菇滑鸡煲仔饭有锅巴！就是要等8分钟，赶时间别点。'),
    ('煲仔饭', 4, '广式味', '腊肠煲仔饭甜口正宗，配2块钱的时令青蔬刚好解腻。'),
    ('淮南牛肉汤', 4, '汤鲜', '牛肉汤免费续，冬天来一碗整个人都暖了，粉丝量足。'),
    ('麻辣香锅', 3, '预算易超', '拿的时候爽，称重的时候哭，建议先定预算再夹菜。'),
    ('麦当劳', 4, '夜宵救星', '晚自习后的1+1随心配，20块出头，苹果片是最后的倔强。'),
    ('土耳其烤肉', 4, '肉量大', '烤肉饭肉给得豪横，男生增肌餐常客，女生建议两人一份。'),
]
