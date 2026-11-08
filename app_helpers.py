# -*- coding: utf-8 -*-
"""app_helpers.py —— 干饭决策机 Streamlit UI：样式 / 卡片 / 打卡周报 / 预置评论"""
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
.qb-row-chips{ margin-top:7px; }

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
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label p{
  font-size:11px !important; font-weight:700; color:#8A6A50 !important;
  white-space:nowrap; margin:0; line-height:1.3; text-align:center;
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
  .qb-head .qb-s, .qb-row .qb-s{ font-size:10px; }
  .qb-row .qb-bval{ font-size:20px; }
  .qb-ticks{ padding:0 8px; }
  .qb-ticks span{ font-size:9.5px; }
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)){ gap:4px !important; }
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label{ min-height:32px; padding:5px 0; }
  div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(8)) div[data-testid="stCheckbox"] label p{ font-size:10.5px !important; }

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
</style>
"""

CIRC = '①②③④⑤'
CAT_EMOJI = {'主食': '🍚', '荤菜': '🍗', '半荤': '🍖', '素菜': '🥬', '汤': '🥣', '饮品': '🥤'}

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


def plan_card(p, reason, idx):
    status_cls = {'推荐': 'pill-ok', '放宽版': 'pill-soft', '建议': 'pill-hard'}.get(p['status'], 'pill-soft')
    self_pill = '<span class="pill pill-self">按克自选</span>' if p['label'] == '自选' else ''
    dishes = ''.join(
        f'<div class="dish"><span class="d-e">{dish_emoji(it["name"], it.get("cat"))}</span>'
        f'<span class="d-n">{it["name"]}</span>'
        + ('<span class="d-w">称重</span>' if it['pricing'] == '称重' else '')
        + f'<span class="d-g">{it["grams"]:g}g</span></div>'
        for it in p['items'])
    tier = ''
    if p.get('tier'):
        t = p['tier']
        rice = f' · 含米饭{t["rice_g"]:g}g' if t['mode'] in ('含米饭', '米饭+1元') else ''
        tier = (f'<div class="tier-line"><span>🍱</span><span>{t["n_meat"]}荤{t["n_veg"]}素档 '
                f'{t["price"]:g}元{rice}</span></div>')
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
 <div class="mc-dishes">{dishes}</div>{tier}
 <div class="mc-stats">
  <div class="ms price"><span class="v">¥{p['PI']:g}</span><span class="k">价格</span></div>
  <div class="ms"><span class="v">{p['E']:g}<i>kcal</i></span><span class="k">热量</span></div>
  <div class="ms"><span class="v">{p['Q']:g}<i>g</i></span><span class="k">蛋白质</span></div>
  <div class="ms"><span class="v">{p['O']:g}<i>g</i></span><span class="k">油脂</span></div>
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
