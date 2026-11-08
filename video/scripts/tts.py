# -*- coding: utf-8 -*-
"""tts.py —— edge-tts 逐幕旁白 + 字级字幕（卡拉OK）
用法: python video/scripts/tts.py          # 全部幕重合成
      python video/scripts/tts.py S1 S5    # 只重合成受影响幕，其余幕沿用现有音频与字级字幕
产出: video/public/assets/audio/S{n}.mp3 + video/public/data/captions.json
（captions 里每幕 start/end 一律以 narration.json 为准同步，幕长校准后无需全量重跑）
"""
import asyncio
import json
import os
import sys

import edge_tts

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
NARR = json.load(open(os.path.join(ROOT, 'narration.json'), encoding='utf-8'))
AOUT = os.path.join(ROOT, 'public', 'assets', 'audio')
DOUT = os.path.join(ROOT, 'public', 'data')
VOICE = 'zh-CN-XiaoxiaoNeural'
RATE = '+8%'


async def synth(scene):
    os.makedirs(AOUT, exist_ok=True)
    mp3 = os.path.join(AOUT, scene['id'] + '.mp3')
    comm = edge_tts.Communicate(scene['text'], VOICE, rate=RATE, boundary='WordBoundary')
    words = []
    with open(mp3, 'wb') as f:
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                f.write(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                words.append(dict(text=chunk['text'],
                                  start=chunk['offset'] / 1e7,
                                  end=(chunk['offset'] + chunk['duration']) / 1e7))
    # 词 → 字（词内均分，供逐字高亮）
    chars = []
    for w in words:
        txt = w['text']
        n = max(1, len(txt))
        step = (w['end'] - w['start']) / n
        for i, ch in enumerate(txt):
            chars.append(dict(t=ch, s=round(w['start'] + i * step, 3),
                              e=round(w['start'] + (i + 1) * step, 3)))
    dur = max((w['end'] for w in words), default=0)
    span = scene['end'] - scene['start']
    print(f"{scene['id']} {scene['name']}: 旁白 {dur:.1f}s / 幕长 {span}s"
          + ('  ⚠️ 超出幕长!' if dur > span - 0.5 else ''), flush=True)
    return dict(id=scene['id'], start=scene['start'], end=scene['end'],
                audio=f"assets/audio/{scene['id']}.mp3", duration=round(dur, 2), chars=chars)


async def main():
    os.makedirs(DOUT, exist_ok=True)
    cap_path = os.path.join(DOUT, 'captions.json')
    only = set(sys.argv[1:])
    unknown = only - {sc['id'] for sc in NARR}
    if unknown:
        sys.exit(f'未知幕号: {sorted(unknown)}')
    old = {}
    if only and os.path.exists(cap_path):
        old = {c['id']: c for c in json.load(open(cap_path, encoding='utf-8'))}
    caps = []
    for sc in NARR:
        if only and sc['id'] not in only and sc['id'] in old:
            span = sc['end'] - sc['start']
            kept = dict(old[sc['id']], start=sc['start'], end=sc['end'])
            print(f"{sc['id']} {sc['name']}: 沿用 旁白 {kept['duration']:.1f}s / 幕长 {span}s"
                  + ('  ⚠️ 超出幕长!' if kept['duration'] > span - 0.5 else ''), flush=True)
            caps.append(kept)
            continue
        caps.append(await synth(sc))
    json.dump(caps, open(cap_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('captions →', cap_path)


if __name__ == '__main__':
    asyncio.run(main())
