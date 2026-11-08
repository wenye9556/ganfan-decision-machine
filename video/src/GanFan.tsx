import React from 'react';
import { AbsoluteFill, Audio, Series, staticFile, useCurrentFrame } from 'remotion';
import { NARR, capOf, sec } from './lib/data';
import { S1Pain, S2Turn } from './scenes/ScenesA';
import { S3Serve, S4Care, S5Trust } from './scenes/ScenesB';
import { S6Value, S7CarouselView, S7End } from './scenes/ScenesC';

const SCENES: Record<string, React.FC> = {
  S1: S1Pain, S2: S2Turn, S3: S3Serve, S4: S4Care, S5: S5Trust, S6: S6Value, S7: S7End,
};

export const GanFan: React.FC = () => (
  <AbsoluteFill style={{ background: '#1A0C04' }}>
    <Series>
      {NARR.map((sc) => {
        const Scene = SCENES[sc.id];
        return (
          <Series.Sequence key={sc.id} durationInFrames={sec(sc.end - sc.start)}>
            <Scene />
            <Audio src={staticFile(capOf(sc.id).audio)} />
          </Series.Sequence>
        );
      })}
    </Series>
  </AbsoluteFill>
);

/** S7 轮播段单独取景（ABPreview 用）：s7Frame 从 S7 内 6s 起算，与成片同状态 */
const S7CarouselForPreview: React.FC = () => {
  const f = useCurrentFrame();
  return <S7CarouselView frame={f} s7Frame={6 * 30 + f} genFrom={0} />;
};

/** A/B 预览（无声）：S1 全段（0–11.2s，帧数随 narration 幕长同步）+ S7 轮播段 3s。
 *  供 AI B-roll 素材放入前后对比：`npx remotion render src/index.ts ABPreview out/ab.mp4` */
const S1_SC = NARR.find((sc) => sc.id === 'S1')!;
export const AB_S1 = sec(S1_SC.end - S1_SC.start);
export const AB_S7 = sec(3);
export const ABPreview: React.FC = () => (
  <AbsoluteFill style={{ background: '#1A0C04' }}>
    <Series>
      <Series.Sequence durationInFrames={AB_S1}>
        <S1Pain />
      </Series.Sequence>
      <Series.Sequence durationInFrames={AB_S7}>
        <S7CarouselForPreview />
      </Series.Sequence>
    </Series>
  </AbsoluteFill>
);
