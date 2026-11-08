import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { Caption, C, FONT, GenBroll, genHas, Grain, Logo, Nutri, PhotoBg, SceneTitle, Tag, fadeUp, pop } from '../lib/kit';

/** S1 痛：下课人流 + 窗口纠结 + 脑内弹幕 + 719 计数 */
export const S1Pain: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  const photo = t < 6 ? 'assets/photos/B-W04_麻辣香锅.jpg' : 'assets/photos/B-W02_淮南牛肉汤_汤粉屏.jpg';
  const danmu = [
    { txt: '会胖吗…', x: 150, y: 180, at: 0.6 },
    { txt: '太贵了吧', x: 1240, y: 240, at: 2.4 },
    { txt: '上次那家好难吃', x: 220, y: 660, at: 4.4 },
    { txt: '又要排队？', x: 1180, y: 620, at: 6.6 },
    { txt: '到底吃啥啊', x: 700, y: 130, at: 8.4 },
  ];
  const count = Math.round(interpolate(f, [20, 90], [0, 719], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  return (
    <AbsoluteFill>
      {/* AI B-roll 插槽 S1_BG：manifest 声明即换视频底（S1 自 0s 起，视频从 0 播放），否则实拍 Ken Burns */
      genHas('S1_BG') ? <GenBroll slot="S1_BG" overlay={0.62} /> : <PhotoBg src={photo} frame={f} dim={0.62} />}
      <Grain />
      {danmu.map((d, i) => {
        const local = f - d.at * 30;
        if (local < 0) return null;
        return (
          <div key={i} style={{
            position: 'absolute', left: d.x, top: d.y, fontFamily: FONT, fontSize: 44, fontWeight: 700,
            color: 'rgba(255,230,205,.92)', background: 'rgba(60,26,10,.55)', padding: '14px 30px',
            borderRadius: 20, border: '1px solid rgba(255,190,140,.35)',
            opacity: interpolate(local, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
            transform: `translateY(${-local * 1.1}px) rotate(${i % 2 ? 3 : -4}deg)`,
          }}>{d.txt}</div>
        );
      })}
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', top: 60 }}>
        <div style={{ fontFamily: FONT, textAlign: 'center' }}>
          <div style={{ fontSize: 58, color: C.soft, ...fadeUp(f, 8) }}>饿着的人，不该做</div>
          <div style={{ fontSize: 200, fontWeight: 900, color: C.orange, lineHeight: 1.1, ...fadeUp(f, 16) }}>
            {count}<span style={{ fontSize: 70, color: C.cream }}> 道</span>
          </div>
          <div style={{ fontSize: 66, color: C.cream, fontWeight: 800, ...fadeUp(f, 24) }}>选择题</div>
        </div>
      </AbsoluteFill>
      <Caption capId="S1" frame={f} />
    </AbsoluteFill>
  );
};

/** S2 转折：一句话输入 → 结构化 chips 亮起（NL Agent 链路首次亮相） */
export const S2Turn: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  const sentence = '减脂，18块，不吃猪';
  const typed = sentence.slice(0, Math.min(sentence.length, Math.floor(t * 5)));
  const chips = ['🥗 减脂', '💰 18 元', '🚫 不吃猪'];
  return (
    <AbsoluteFill style={{ background: 'linear-gradient(160deg,#3A1E0E,#1F0F06)' }}>
      <Grain />
      <div style={{ position: 'absolute', top: 84, width: '100%', textAlign: 'center' }}>
        <SceneTitle main="现在，只要说一句话" sub="它听得懂人话" frame={f} />
      </div>
      {/* 手机框：真实 UI 截图 + 程序化打字层 */}
      <div style={{
        position: 'absolute', left: 150, top: 330, width: 400, height: 620, borderRadius: 44,
        background: '#FFFCF7', border: '10px solid #100804', overflow: 'hidden',
        boxShadow: '0 30px 80px rgba(0,0,0,.5)', transform: `scale(${0.94 + pop(f, 30, 6) * 0.06})`,
      }}>
        <Img src={staticFile('assets/ui/home.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'top' }} />
      </div>
      <div style={{ position: 'absolute', left: 660, top: 380, width: 1060 }}>
        <div style={{
          background: '#FFF7EE', borderRadius: 26, padding: '34px 40px', fontFamily: FONT,
          fontSize: 52, color: C.ink, fontWeight: 700, minHeight: 120,
          boxShadow: '0 16px 50px rgba(0,0,0,.35)', border: '2px solid #E9D6BE',
        }}>
          {typed}<span style={{ color: C.deep, opacity: Math.floor(f / 12) % 2 ? 0 : 1 }}>▍</span>
        </div>
        <div style={{ marginTop: 36, display: 'flex' }}>
          {chips.map((c, i) => (
            <div key={i} style={{
              transform: `scale(${pop(f, 30, 66 + i * 12)})`, marginRight: 22,
              background: 'rgba(255,178,94,.14)', border: '2px solid rgba(255,178,94,.6)',
              color: C.orange, borderRadius: 999, padding: '16px 34px', fontSize: 40,
              fontFamily: FONT, fontWeight: 700,
            }}>{c}</div>
          ))}
        </div>
        <div style={{ marginTop: 46, fontFamily: FONT, fontSize: 40, color: C.soft, ...fadeUp(f, 108) }}>
          整座食堂，开始为你一个人配菜 →
        </div>
      </div>
      <Caption capId="S2" frame={f} />
    </AbsoluteFill>
  );
};
