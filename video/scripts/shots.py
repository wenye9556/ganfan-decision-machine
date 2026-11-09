# -*- coding: utf-8 -*-
"""shots.py —— Playwright 截取 Streamlit UI 素材（Remotion 混合管线的"录屏"兜底）
前置: streamlit run app.py (8502) 已启动
用法: python video/scripts/shots.py
注意: Streamlit 的滚动容器是 stAppViewContainer（body 不滚），
      full_page=True 截不到整页——本脚本按目标区域手动滚到顶部/结果区再截。
"""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'public', 'assets', 'ui')
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as pw:
    try:
        br = pw.chromium.launch(channel='chrome')
    except Exception:
        br = pw.chromium.launch(channel='msedge')
    page = br.new_page(viewport=dict(width=520, height=1050), device_scale_factor=2)

    MAIN = 'section[data-testid="stMain"]'   # Streamlit 1.51 的真正滚动容器

    def to_top():
        """滚回页面顶部（stMain 独立滚动容器 + window 双保险）。"""
        page.evaluate("""() => {
            const c = document.querySelector('section[data-testid="stMain"]');
            if (c) c.scrollTo(0, 0);
            window.scrollTo(0, 0);
        }""")
        page.wait_for_timeout(500)

    def scroll_into(js_find_obj, offset=90):
        """把 js_find_obj() 返回的元素滚到视口（补偿 sticky 标签栏约 70px + 余量）。"""
        page.evaluate(f"""() => {{
            const el = ({js_find_obj})();
            if (el) el.scrollIntoView({{ block: 'start' }});
            const c = document.querySelector('section[data-testid="stMain"]');
            if (c) c.scrollBy(0, -{offset});
        }}""")
        page.wait_for_timeout(500)

    page.goto('http://localhost:8502', wait_until='networkidle')
    page.wait_for_timeout(2500)
    to_top()
    page.screenshot(path=os.path.join(OUT, 'home.png'))
    print('home ✓', flush=True)

    page.get_by_placeholder('没想法？不输入也行——点「一键配饭」随机抽组条件配三套').fill('减脂，18块，不吃香菜')
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    to_top()
    page.screenshot(path=os.path.join(OUT, 'nl_input.png'))
    page.get_by_role('button', name='🍽️ 一键配饭').click()
    page.wait_for_selector('.meal-card', timeout=90000)
    page.wait_for_timeout(1500)
    cards = page.locator('.meal-card')
    n = cards.count()
    print('cards:', n, flush=True)
    for i in range(min(3, n)):
        cards.nth(i).screenshot(path=os.path.join(OUT, f'plan{i+1}.png'))
    # 结果页：从第一张方案卡开始（顶部即结果区）
    scroll_into("() => document.querySelector('.meal-card')", offset=130)
    page.screenshot(path=os.path.join(OUT, 'result_full.png'))
    print('plans ✓', flush=True)

    page.get_by_role('button', name='✅ 打卡这餐').first.click()
    page.wait_for_timeout(1200)
    page.get_by_role('tab', name='📅 周报').click()
    page.wait_for_timeout(4800)   # 等「已打卡」toast 自动消失
    to_top()
    page.screenshot(path=os.path.join(OUT, 'week.png'))
    print('week ✓', flush=True)

    page.get_by_role('tab', name='💬 评价').click()
    page.wait_for_timeout(800)
    to_top()
    page.screenshot(path=os.path.join(OUT, 'comments.png'))
    page.get_by_role('tab', name='📖 关于').click()
    page.wait_for_timeout(800)
    to_top()
    page.screenshot(path=os.path.join(OUT, 'honest.png'))

    # 随机流程：空输入 → 随机抽条件 + 明示 + 再换一批入口
    page.get_by_role('tab', name='🍚 配饭').click()
    page.wait_for_timeout(800)
    page.get_by_placeholder('没想法？不输入也行——点「一键配饭」随机抽组条件配三套').fill('')
    page.get_by_role('button', name='🍽️ 一键配饭').click()
    page.wait_for_selector('text=本次随机条件', timeout=90000)
    page.wait_for_timeout(1200)
    scroll_into("""() => [...document.querySelectorAll('.hint')]
        .find(e => e.textContent.includes('本次随机条件'))""", offset=100)
    page.screenshot(path=os.path.join(OUT, 'random_flow.png'))
    print('random_flow ✓', flush=True)
    br.close()
print('UI 素材全部截取 →', OUT)
