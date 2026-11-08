import React from 'react';
import { Composition } from 'remotion';
import { ABPreview, AB_S1, AB_S7, GanFan } from './GanFan';
import { NARR, sec } from './lib/data';

/** 成片总帧数 = Series 各幕帧数之和（幕起止以 narration.json 为准，幕长校准后自动同步；当前 122.2s = 3666 帧） */
const TOTAL = NARR.reduce((n, sc) => n + sec(sc.end - sc.start), 0);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="GanFan"
      component={GanFan}
      durationInFrames={TOTAL}
      fps={30}
      width={1920}
      height={1080}
    />
    {/* A/B 预览：S1 全段（0–11.2s）+ S7 轮播 3s，对比 AI B-roll 插槽开关效果 */}
    <Composition
      id="ABPreview"
      component={ABPreview}
      durationInFrames={AB_S1 + AB_S7}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
