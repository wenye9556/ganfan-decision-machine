import React from 'react';
import { AbsoluteFill, Img, interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame } from 'remotion';
import { capOf, currentSentence, SceneCap } from './data';
import genManifest from '../../public/assets/gen/manifest.json';

/** AI B-roll 插槽清单（构建期 import，渲染确定性；运行时不 fetch）。
 *  manifest 为空数组 [] 时 genHas 恒为 false，成片与无插槽版逐帧等价。 */
export interface GenClip { slot: string; file: string }
const GEN = genManifest as GenClip[];
export const genHas = (slot: string): boolean => GEN.some((g) => g.slot === slot);

/** AI B-roll：manifest 声明了该插槽则播视频（静音、cover 填充、与现片一致的暖色调压暗罩）。
 *  未声明时渲染 null，场景保持原有实现。调用方需保证挂载时序（必要时用 <Sequence from=…> 归零视频起点）。 */
export const GenBroll: React.FC<{ slot: string; overlay?: number }> = ({ slot, overlay = 0.4 }) => {
  const hit = GEN.find((g) => g.slot === slot);
  if (!hit) return null;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <OffthreadVideo
        src={staticFile(hit.file)}
        muted
        style={{
          width: '100%', height: '100%', objectFit: 'cover',
          filter: 'saturate(1.12) brightness(1.02)',
        }}
      />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(30,12,4,${overlay * 0.6}), rgba(30,12,4,${overlay}))` }} />
    </AbsoluteFill>
  );
};

export const C = {
  bg: '#2A160C', cream: '#FFF6EA', orange: '#FFB25E', deep: '#E07A3F',
  ink: '#3E2F25', soft: '#F3DFC4', green: '#9ED48A', card: '#FFFBF3',
};

export const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif';

export const fadeUp = (frame: number, start: number, dur = 18) => ({
  opacity: interpolate(frame, [start, start + dur], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
  transform: `translateY(${interpolate(frame, [start, start + dur], [34, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })}px)`,
});

export const pop = (frame: number, fps: number, start: number) =>
  spring({ frame: Math.max(0, frame - start), fps, config: { damping: 14, stiffness: 130 } });

/** 暖色照片底 + Ken Burns 缓推 + 暖色压暗罩，美食永远是主角 */
export const PhotoBg: React.FC<{ src: string; frame: number; dim?: number; zoom?: number; blur?: number }> = ({
  src, frame, dim = 0.55, zoom = 0.10, blur = 0,
}) => (
  <AbsoluteFill style={{ background: C.bg }}>
    <Img
      src={staticFile(src)}
      style={{
        width: '100%', height: '100%', objectFit: 'cover',
        transform: `scale(${1 + (frame / 900) * zoom}) translateX(${Math.sin(frame / 240) * 12}px)`,
        filter: `saturate(1.12) brightness(1.02) blur(${blur}px)`,
      }}
    />
    <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(30,12,4,${dim * 0.6}), rgba(30,12,4,${dim}))` }} />
  </AbsoluteFill>
);

export const Grain: React.FC = () => (
  <AbsoluteFill
    style={{
      backgroundImage: 'radial-gradient(rgba(255,200,150,0.05) 1px, transparent 1px)',
      backgroundSize: '26px 26px', pointerEvents: 'none',
    }}
  />
);

/** 逐句显示 + 句内逐字高亮卡拉OK字幕（长句自动换行，绝不截断） */
export const Caption: React.FC<{ capId: string; frame: number; y?: number; size?: number }> = ({
  capId, frame, y = 940, size = 46,
}) => {
  const cap = capOf(capId);
  const t = frame / 30;
  const sent = currentSentence(cap, t);
  const text = sent.display.map((d) => d.ch).join('');
  const fs = text.length > 30 ? size - 6 : size;
  let lastCi = -1;
  return (
    <div style={{
      position: 'absolute', left: 160, right: 160, top: y, textAlign: 'center',
      fontFamily: FONT, fontSize: fs, fontWeight: 700, lineHeight: 1.5,
      textShadow: '0 2px 14px rgba(0,0,0,.65)', letterSpacing: 1,
    }}>
      {sent.display.map((d, i) => {
        if (d.ci !== null) lastCi = d.ci;
        const ref = d.ci !== null ? d.ci : lastCi;
        const on = ref >= 0 && !!cap.chars[ref] && t >= cap.chars[ref].s - 0.06;
        return <span key={i} style={{ color: on ? C.orange : 'rgba(255,246,234,0.42)', transition: 'color .08s' }}>{d.ch}</span>;
      })}
    </div>
  );
};

export const Tag: React.FC<{ children: React.ReactNode; bg?: string; color?: string; fs?: number }> = ({
  children, bg = 'rgba(255,178,94,0.16)', color = C.orange, fs = 30,
}) => (
  <span style={{
    display: 'inline-block', background: bg, color, borderRadius: 999,
    padding: '8px 22px', fontSize: fs, fontWeight: 700, fontFamily: FONT, margin: '0 8px',
    border: `1px solid ${color}33`,
  }}>{children}</span>
);

/** 营养成分表式小标签（数字=餐盘的注释） */
export const Nutri: React.FC<{ price: number; kcal: number; prot: number; oil: number; dark?: boolean; fs?: number }> = ({
  price, kcal, prot, oil, dark = false, fs = 30,
}) => {
  const cells: [string, string][] = [[`${price}`, '元'], [`${kcal}`, 'kcal'], [`${prot}g`, '蛋白'], [`${oil}g`, '油']];
  return (
    <div style={{
      display: 'flex', border: `2px solid ${dark ? '#7A5232' : '#E4CDAF'}`, borderRadius: 16,
      overflow: 'hidden', fontFamily: FONT, background: dark ? 'rgba(20,10,4,.55)' : '#FFFBF4',
    }}>
      {cells.map(([v, lab], i) => (
        <div key={i} style={{
          flex: 1, textAlign: 'center', padding: '12px 6px',
          borderLeft: i ? `1.5px solid ${dark ? '#7A5232' : '#E4CDAF'}` : 'none',
        }}>
          <div style={{ fontSize: fs + 6, fontWeight: 800, color: dark ? C.cream : C.ink }}>{v}</div>
          <div style={{ fontSize: fs - 8, color: dark ? C.soft : '#9A8578', marginTop: 2 }}>{lab}</div>
        </div>
      ))}
    </div>
  );
};

export const Logo: React.FC<{ size?: number; color?: string }> = ({ size = 64, color = C.cream }) => (
  <div style={{ fontFamily: FONT, fontSize: size, fontWeight: 800, color, letterSpacing: 2 }}>
    🍚 干饭决策机
  </div>
);

/** 幕标题（三层信息之中景） */
export const SceneTitle: React.FC<{ main: string; sub?: string; frame: number; color?: string }> = ({
  main, sub, frame, color = C.cream,
}) => (
  <div style={{ textAlign: 'center', fontFamily: FONT }}>
    <div style={{ fontSize: 76, fontWeight: 800, color, lineHeight: 1.3, ...fadeUp(frame, 4) }}>{main}</div>
    {sub && <div style={{ fontSize: 36, color: C.soft, marginTop: 22, ...fadeUp(frame, 12) }}>{sub}</div>}
  </div>
);
