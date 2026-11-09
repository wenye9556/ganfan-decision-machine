# -*- coding: utf-8 -*-
"""deploy_backfill.py —— 部署回填自动化（只改文件 + git add，绝不 commit/push，主控统一提交）
用法: python deploy_backfill.py https://xxx.streamlit.app

动作：
1. 把 URL 回填 README.md（在线体验节 + 提交清单）、SUBMISSION.md（邮件草稿 + 自查表两处
   + 部署项打勾）、CHANGELOG.md（三处历史「待回填」状态行改「已回填」口径，保全仓 grep 清零）、
   bp/build_bp.py（第 7 页「待回填」占位）；
2. 重跑 bp/build_bp.py 重新生成 bp.html + 商业计划书 PDF（自动探测带 playwright 的解释器）；
3. git add 相关文件，打印「已回填待提交」；
4. 全仓 grep「待回填/部署后回填/【Streamlit Community Cloud 链接」校验清零，残留则列出并退出码 1。

幂等：目标文件已含本次 URL 时跳过该文件并提示（重复运行安全）。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PATTERNS = ['待回填', '部署后回填', '【Streamlit Community Cloud 链接']
SKIP_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', '.workbuddy', 'tmp_ui', 'out'}
SKIP_FILES = {'deploy_backfill.py'}          # 本脚本自带占位原文（替换表），不参与残留扫描
BIN_EXT = {'.png', '.jpg', '.jpeg', '.mp4', '.wav', '.pdf', '.xlsx', '.zip', '.psd', '.webp', '.ico', '.ttf'}

# (文件, [(旧文本, 新文本), ...])；{url} 为占位
REPLACES = [
    ('README.md', [
        ('部署方式（仓库已含全部依赖与数据，部署后回填链接）：',
         '**在线体验：{url}**（浏览器直接打开，无需账号）\n\n部署方式（仓库已含全部依赖与数据）：'),
        ('- [x] 可登录试用作品：Streamlit 链接（部署后回填）+ 本 README 运行说明，无需测试账号',
         '- [x] 可登录试用作品：Streamlit 链接 {url} + 本 README 运行说明，无需测试账号'),
    ]),
    ('SUBMISSION.md', [
        ('   体验链接：【Streamlit Community Cloud 链接，部署后回填】',
         '   体验链接：{url}'),
        ('- [x] 可登录试用作品：体验链接（部署后回填）+ 运行说明 + 无需测试账号',
         '- [x] 可登录试用作品：体验链接 {url} + 运行说明 + 无需测试账号'),
        ('- [ ] 部署：推 GitHub → share.streamlit.io 部署 app.py → 回填体验链接（本文件、README、BP 第 7 页）',
         '- [x] 部署：已上线 {url}（本文件、README、BP 第 7 页均已回填）'),
    ]),
    ('CHANGELOG.md', [
        ('第 7 页空链接改为「待回填」明确提示',
         '第 7 页空链接加部署提示占位（后由 deploy_backfill.py 回填）'),
        ('- ⚠️ **待回填**：第 7 页「在线体验」的 Streamlit 部署链接（部署后填入）',
         '- ✅ **已回填**：第 7 页「在线体验」的 Streamlit 部署链接已上线（README 第二节 / SUBMISSION 邮件草稿）'),
        ('9. **BP 第 8 页「在线体验」部署链接待回填**（外部依赖）：Streamlit 部署后填入真实 URL 即完成。',
         '9. ~~BP 第 8 页「在线体验」部署链接占位~~（外部依赖）：已由 deploy_backfill.py 自动回填真实 URL 完成。'),
    ]),
    (os.path.join('bp', 'build_bp.py'), [
        ('<p><span class="tag">待回填</span><b>在线体验：</b>部署后回填（提交邮件附链接）；',
         '<p><span class="tag">已上线</span><b>在线体验：</b>{url}（无需注册，打开即用）；'),
    ]),
]
GIT_ADD = ['README.md', 'SUBMISSION.md', 'CHANGELOG.md',
           'bp/build_bp.py', 'bp/bp.html', 'bp/干饭决策机_商业计划书.pdf']


def apply_file(path, pairs, url):
    """按精确文本替换；返回 (替换条数, 未命中旧文本列表)。
    幂等判定：文件已含本次 URL，或全部占位模式已消失（曾用别的 URL 回填过）→ (-1, []) 跳过。"""
    full = os.path.join(ROOT, path)
    s = open(full, encoding='utf-8').read()
    if url in s or not any(pat in s for pat in PATTERNS):
        return -1, []
    missed, n = [], 0
    for old, new in pairs:
        if old in s:
            s = s.replace(old, new.replace('{url}', url))
            n += 1
        else:
            missed.append(old[:40])
    if n:
        open(full, 'w', encoding='utf-8').write(s)
    return n, missed


def find_playwright_python():
    """按优先级探测能 import playwright 的解释器（.venv 无 playwright，BP 打印依赖它）。"""
    venv = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
    cands = [venv if os.path.exists(venv) else sys.executable,
             shutil.which('py'), shutil.which('python')]
    seen = set()
    for c in cands:
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            r = subprocess.run([c, '-c', 'import playwright'], capture_output=True, timeout=60)
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return None


def repo_grep():
    """全仓残留占位扫描（跳过二进制/依赖目录），返回 [(相对路径, 行号, 行内预览)]。"""
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in BIN_EXT or fn in SKIP_FILES:
                continue
            p = os.path.join(dirpath, fn)
            try:
                lines = open(p, encoding='utf-8', errors='ignore').read().splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if any(pat in line for pat in PATTERNS):
                    hits.append((os.path.relpath(p, ROOT), i, line.strip()[:70]))
    return hits


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith(('http://', 'https://')):
        print('用法: python deploy_backfill.py https://xxx.streamlit.app')
        sys.exit(2)
    url = sys.argv[1].strip()
    if not url.endswith('.streamlit.app') and '/'.join(url.split('/')[:3]).count('.') == 0:
        print(f'[警告] URL 不像 Streamlit Cloud 域名：{url}（仍然继续）')
    print(f'回填 URL: {url}')

    for path, pairs in REPLACES:
        n, missed = apply_file(path, pairs, url)
        if n == -1:
            print(f'  [跳过] {path} 已含该 URL（幂等）')
        elif n == len(pairs):
            print(f'  [OK] {path} {n}/{len(pairs)} 处回填')
        else:
            print(f'  [{"OK" if n else "!!"}] {path} {n}/{len(pairs)} 处回填'
                  + (f'，未命中: {missed}' if missed else ''))
            if not n:
                sys.exit(f'[失败] {path} 无任何占位命中，请人工检查')

    # 重跑 BP（自动探测带 playwright 的解释器）
    py = find_playwright_python()
    if not py:
        print('[!!] 未找到可用的 playwright 解释器，跳过 BP 重跑（bp.html/PDF 未更新）')
    else:
        print(f'重跑 build_bp.py（{py}）…')
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        r = subprocess.run([py, os.path.join(ROOT, 'bp', 'build_bp.py')],
                           capture_output=True, text=True, encoding='utf-8', env=env, timeout=600)
        tail = (r.stdout or '').strip().splitlines()[-2:]
        for t in tail:
            print('   ', t)
        if r.returncode != 0:
            print('   stderr:', (r.stderr or '').strip()[-300:])
            sys.exit('[失败] build_bp.py 重跑失败')

    # git add（不 commit 不 push，主控统一提交）
    r = subprocess.run(['git', 'add'] + GIT_ADD, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        print('[!!] git add 失败:', (r.stderr or '').strip())
    else:
        print('git add:', ', '.join(GIT_ADD))

    # 全仓校验占位清零
    hits = repo_grep()
    if hits:
        print(f'\n[!] 仍有 {len(hits)} 处占位残留：')
        for p, i, line in hits:
            print(f'   {p}:{i} {line}')
        sys.exit(1)
    print('\n已回填待提交')


if __name__ == '__main__':
    main()
