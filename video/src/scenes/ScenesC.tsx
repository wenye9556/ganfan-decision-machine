import React from 'react';
import { AbsoluteFill, interpolate, Sequence, useCurrentFrame } from 'remotion';
import { Caption, C, FONT, GenBroll, genHas, Grain, Logo, PhotoBg, SceneTitle, Tag, fadeUp, pop } from '../lib/kit';

/** S6 价值：学生 → 高校后勤 → 企业团餐
 *  原为三张静态卡撑 18.5s（QC 冻结重灾），现补三层动效保证每 2s 有视觉事件：
 *  背景纹理 = 实拍 Ken Burns 轮换交叉溶解 + 暖色光斑缓慢漂移；
 *  前景卡片 = 图标微动 + 三卡轮流暖光高亮；中景数据 = 卡内小数据条数字滚动。 */
const S6_PHOTOS = [
  'assets/photos/B-W01_土耳其烤肉.jpg',
  'assets/photos/B-W03_韩式拌饭螺蛳粉.jpg',
  'assets/photos/B-W04_麻辣香锅.jpg',
  'assets/photos/B-W02_淮南牛肉汤_汤粉屏.jpg',
];
const S6_ROT = 4.5;   // 每张实拍底停留秒数（18.5s ÷ 4 张）
const S6_FADE = 0.8;  // 交叉溶解时长

const S6_CARDS: { icon: string; title: string; lines: string[]; nums: [number | string, string][] }[] = [
  {
    icon: '🎓', title: '对学生',
    lines: ['把纠结还给下课的十分钟', '把坚持变成看得见的一周'],
    nums: [[10, '分钟课间'], [7, '天坚持']],
  },
  {
    icon: '🏫', title: '对食堂后勤',
    lines: ['哪些窗口排长队', '哪些菜总卖完，有了能看的数据'],
    nums: [[26, '个窗口'], [719, '道菜']],
  },
  {
    icon: '🏢', title: '对企业团餐',
    lines: ['同一套法子，搬到更多餐桌', '吃得好一点，可以很简单'],
    nums: [[1, '套法子'], ['∞', '更多餐桌']],
  },
];

export const S6Value: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  const pi = Math.min(S6_PHOTOS.length - 1, Math.floor(t / S6_ROT));
  const pLocal = Math.round((t - pi * S6_ROT) * 30);  // 每次换图 Ken Burns 重新起推
  const fade = pi >= S6_PHOTOS.length - 1 ? 0
    : interpolate(t - pi * S6_ROT, [S6_ROT - S6_FADE, S6_ROT], [0, 1],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: 'linear-gradient(155deg,#311C0D,#1A0D04)' }}>
      {/* AI B-roll 插槽 S6_BG（约 84.5–103s 全段底层循环 B-roll）：manifest 声明即换视频底
       *  （压暗罩加厚至 0.8，保证三张前景卡可读），空 manifest 时保持现有实拍 Ken Burns 轮换 */}
      {genHas('S6_BG') ? (
        <GenBroll slot="S6_BG" overlay={0.8} />
      ) : (
        <>
          {/* 背景纹理层：实拍 Ken Burns 轮换（下一张垫底、当前张淡出交叉溶解，压暗保证卡片可读） */}
          <PhotoBg src={S6_PHOTOS[Math.min(pi + 1, S6_PHOTOS.length - 1)]} frame={pLocal} dim={0.8} blur={5} zoom={0.14} />
        <AbsoluteFill style={{ opacity: 1 - fade }}>
          <PhotoBg src={S6_PHOTOS[pi]} frame={pLocal} dim={0.8} blur={5} zoom={0.14} />
        </AbsoluteFill>
        </>
      )}
      <Grain />
      {/* 暖色光斑：三个大光斑缓慢漂移 */}
      {[
        { x: 210, y: 720, r: 300, p: 0 }, { x: 1480, y: 220, r: 380, p: 2.1 }, { x: 920, y: 980, r: 340, p: 4.2 },
      ].map((s, i) => (
        <div key={i} style={{
          position: 'absolute', borderRadius: '50%',
          left: s.x + Math.sin(t * 0.35 + s.p) * 95,
          top: s.y + Math.cos(t * 0.27 + s.p * 1.3) * 70,
          width: s.r * 2, height: s.r * 2,
          background: 'radial-gradient(circle, rgba(255,178,94,.15), rgba(255,140,70,0) 65%)',
          filter: 'blur(28px)',
        }} />
      ))}
      <div style={{ position: 'absolute', top: 84, width: '100%' }}>
        <SceneTitle main="一台决策机，三份价值" frame={f} />
      </div>
      <div style={{ position: 'absolute', left: 120, top: 310, display: 'flex', gap: 44 }}>
        {S6_CARDS.map((c, i) => {
          const in0 = 10 + i * 9;  // 卡片错峰入场
          const glow = Math.max(0, Math.sin((t * Math.PI) / 2.5 - (i * Math.PI * 2) / 3)) ** 3;  // 三卡轮流高亮（周期 5s）
          return (
            <div key={i} style={{
              width: 520, height: 560, borderRadius: 34, padding: '42px 40px',
              background: 'rgba(255,246,234,.07)',
              border: `2px solid rgba(255,200,150,${0.25 + glow * 0.3})`,
              boxShadow: `0 26px 70px rgba(0,0,0,.45), 0 0 ${16 + glow * 44}px rgba(255,178,94,${0.08 + glow * 0.24})`,
              transform: `translateY(${(1 - pop(f, 30, in0)) * 90}px)`,
              opacity: pop(f, 30, in0),
            }}>
              <div style={{
                fontSize: 84,
                transform: `translateY(${Math.sin((f + i * 25) / 26) * 5}px) scale(${1 + Math.sin((f + i * 25) / 26) * 0.02})`,
              }}>{c.icon}</div>
              <div style={{ fontFamily: FONT, fontSize: 48, fontWeight: 800, color: C.orange, marginTop: 12 }}>{c.title}</div>
              {c.lines.map((l, j) => (
                <div key={j} style={{ fontFamily: FONT, fontSize: 30, color: C.cream, lineHeight: 1.65, marginTop: 12 }}>{l}</div>
              ))}
              {/* 中景数据层：小数据条，数字滚动到位 */}
              <div style={{ display: 'flex', gap: 14, marginTop: 22 }}>
                {c.nums.map(([v, lab], j) => {
                  const n0 = 46 + i * 8 + j * 6;
                  const num = typeof v === 'number'
                    ? Math.round(interpolate(f, [n0, n0 + 30], [0, v], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }))
                    : v;
                  return (
                    <div key={j} style={{
                      display: 'flex', alignItems: 'baseline', gap: 8,
                      background: 'rgba(255,178,94,.12)', border: '1.5px solid rgba(255,178,94,.45)',
                      borderRadius: 16, padding: '10px 18px',
                      transform: `scale(${pop(f, 30, n0)})`,
                    }}>
                      <span style={{ fontFamily: FONT, fontSize: 40, fontWeight: 900, color: C.orange }}>{num}</span>
                      <span style={{ fontFamily: FONT, fontSize: 25, color: C.soft }}>{lab}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      <Caption capId="S6" frame={f} />
    </AbsoluteFill>
  );
};

const S7_PHOTOS = ['assets/photos/B-W01_土耳其烤肉.jpg', 'assets/photos/B-W02_淮南牛肉汤_汤粉屏.jpg',
  'assets/photos/B-W03_韩式拌饭螺蛳粉.jpg', 'assets/photos/B-W04_麻辣香锅.jpg'];
const S7_CAR1 = 6 * 30;  // 轮播段在 S7 内的起点帧

/** S7 菜品轮播段内容（S7 内 6–14s；ABPreview 复用）。
 *  frame=轮播段内帧(0 起)；s7Frame=等效 S7 帧保持 PhotoBg 推镜连续；genFrom=GenBroll 的 Sequence from（归零视频起点）。 */
export const S7CarouselView: React.FC<{ frame: number; s7Frame: number; genFrom: number }> = ({ frame, s7Frame, genFrom }) => {
  const t = frame / 30;
  const idx = Math.min(3, Math.floor(t / 2));
  return (
    <AbsoluteFill>
      {/* AI B-roll 插槽 S7_CAROUSEL（109–117s 轮播段底）：声明即整段视频，否则四张实拍轮播 */
      genHas('S7_CAROUSEL') ? (
        <Sequence from={genFrom} durationInFrames={8 * 30} layout="none">
          <GenBroll slot="S7_CAROUSEL" overlay={0.3} />
        </Sequence>
      ) : (
        <PhotoBg src={S7_PHOTOS[idx]} frame={s7Frame} dim={0.3} zoom={0.16} />
      )}
      <div style={{
        position: 'absolute', left: 90, bottom: 90, fontFamily: FONT, fontSize: 54,
        fontWeight: 800, color: C.cream, textShadow: '0 3px 16px rgba(0,0,0,.7)',
      }}>好好吃饭，是正经事。</div>
    </AbsoluteFill>
  );
};

/** S7 收尾：团队致谢 → 菜品轮播 → 尾板=定位句+logo */
export const S7End: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  if (t < 6) {
    return (
      <AbsoluteFill style={{ background: 'linear-gradient(160deg,#2E1B0C,#190C04)' }}>
        <Grain />
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ ...fadeUp(f, 4) }}><Logo size={92} /></div>
          <div style={{ fontFamily: FONT, fontSize: 40, color: C.soft, marginTop: 44, ...fadeUp(f, 14) }}>
            MINMAX 黑客松 · 干饭决策机团队
          </div>
          <div style={{ fontFamily: FONT, fontSize: 32, color: 'rgba(255,230,205,.6)', marginTop: 22, ...fadeUp(f, 22) }}>
            实地采集 · 整餐搭配 · 一句话理解 · 诚实降级
          </div>
          <div style={{ marginTop: 60, ...fadeUp(f, 30) }}>
            <Tag fs={34}>感谢每一个认真干饭的人</Tag>
          </div>
        </AbsoluteFill>
        <Caption capId="S7" frame={f} />
      </AbsoluteFill>
    );
  }
  if (t < 14) {
    return <S7CarouselView frame={f - S7_CAR1} s7Frame={f} genFrom={S7_CAR1} />;
  }
  return (
    <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 35%, #4A2812, #1A0C04 75%)' }}>
      <Grain />
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ transform: `scale(${pop(f - 420, 30, 4)})` }}><Logo size={86} /></div>
        <div style={{
          fontFamily: FONT, fontSize: 84, fontWeight: 900, color: C.cream, textAlign: 'center',
          lineHeight: 1.6, marginTop: 70, ...fadeUp(f - 420, 16),
        }}>
          吃透整座食堂，<br />才敢替你<span style={{ color: C.orange }}>配三套饭</span>
        </div>
        <div style={{ fontFamily: FONT, fontSize: 36, color: C.soft, marginTop: 56, ...fadeUp(f - 420, 30) }}>
          饿着的人，不该做 719 道选择题
        </div>
        <div style={{ marginTop: 70, display: 'flex', gap: 20, ...fadeUp(f - 420, 40) }}>
          <Tag fs={30}>719 道真实菜</Tag><Tag fs={30}>26 个窗口</Tag><Tag fs={30}>一句话配餐</Tag>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
