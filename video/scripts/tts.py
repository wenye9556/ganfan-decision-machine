# -*- coding: utf-8 -*-
"""tts.py —— edge-tts 逐幕旁白 + 字级字幕（卡拉OK）
用法: python video/scripts/tts.py
产出: video/public/assets/audio/S{n}.mp3 + video/public/data/captions.json
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
    caps = []
    for sc in NARR:
        caps.append(await synth(sc))
    json.dump(caps, open(os.path.join(DOUT, 'captions.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('captions →', os.path.join(DOUT, 'captions.json'))


if __name__ == '__main__':
    asyncio.run(main())
