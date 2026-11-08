import React from 'react';
import { Composition } from 'remotion';
import { ABPreview, GanFan } from './GanFan';

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="GanFan"
      component={GanFan}
      durationInFrames={123 * 30}
      fps={30}
      width={1920}
      height={1080}
    />
    {/* A/B 预览：S1 0–12s + S7 轮播 3s，对比 AI B-roll 插槽开关效果 */}
    <Composition
      id="ABPreview"
      component={ABPreview}
      durationInFrames={15 * 30}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
