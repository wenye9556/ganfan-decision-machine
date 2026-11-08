import React from 'react';
import { AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame } from 'remotion';
import { cutFrameByPrefix, PLANS, WEEK } from '../lib/data';
import { Caption, C, FONT, GenBroll, genHas, Grain, Nutri, PhotoBg, SceneTitle, Tag, fadeUp, pop } from '../lib/kit';

const PHOTOS = ['assets/photos/B-W01_土耳其烤肉.jpg', 'assets/photos/B-W03_韩式拌饭螺蛳粉.jpg',
  'assets/photos/B-W04_麻辣香锅.jpg'];

/* 切镜帧号由旁白句起点（captions 字级时间）计算，画面比语音提前 CUE_LEAD=0.25s：
 *  第二套 7.546s→219（原 219，一致）/ 第三套 12.789s→376（原 375，提前量 0.29→0.26s 更准）
 *  总结「想增肌」17.176s→508（原阈值 507） */
const S3_CUT2 = cutFrameByPrefix('S3', '第二套');   // 219
const S3_CUT3 = cutFrameByPrefix('S3', '第三套');   // 376
const S3_SUM = cutFrameByPrefix('S3', '想增肌');    // 508
const S3_SUM_HEAD = 20;  // 总结镜头入场动画预置帧数（切换瞬间即接近成形，沿旧 507-487 惯例）

/* S4 周报画面提前于「本周十一餐…」句起点（7.164s）0.25s 切入：
 *  207 帧（原 240=8.0s，晚了一句开头），内部动画以切点为 0 起算 */
const S4_CUT = cutFrameByPrefix('S4', '本周');      // 207

/** 单套方案：UI 卡截图上菜 + 程序化营养标签（每镜可命名元素≥8） */
const ServeOne: React.FC<{ idx: number; frame: number }> = ({ idx, frame }) => {
  const plan = PLANS['减脂'].top3[idx];
  const reason = PLANS['减脂'].reasons[idx];
  const f = frame;
  return (
    <AbsoluteFill>
      <PhotoBg src={PHOTOS[idx]} frame={f} dim={0.68} blur={5} />
      <Grain />
      <div style={{ position: 'absolute', top: 60, width: '100%', textAlign: 'center' }}>
        <SceneTitle main={`第${'一二三'[idx]}套 · 上菜`} sub={plan.cant[0] + ' · ' + plan.wins.join(' / ')} frame={f} />
      </div>
      <div style={{
        position: 'absolute', left: 120, top: 300, width: 520, borderRadius: 30, overflow: 'hidden',
        boxShadow: '0 30px 90px rgba(0,0,0,.55)', border: '6px solid rgba(255,240,220,.9)',
        transform: `translateY(${(1 - pop(f, 30, 4)) * 120}px) rotate(${(1 - pop(f, 30, 4)) * -4}deg)`,
        opacity: pop(f, 30, 4),
      }}>
        <Img src={staticFile(`assets/ui/plan${idx + 1}.png`)} style={{ width: '100%' }} />
      </div>
      <div style={{ position: 'absolute', left: 760, top: 330, width: 1000 }}>
        <div style={{ ...fadeUp(f, 10) }}>
          <Tag bg={plan.status === '推荐' ? 'rgba(158,212,138,.18)' : 'rgba(255,178,94,.18)'}
            color={plan.status === '推荐' ? C.green : C.orange} fs={32}>
            {plan.status}{plan.label === '自选' ? ' · 按克自选' : ''}
          </Tag>
          <Tag fs={32}>{plan.tag || '均衡搭配'}</Tag>
        </div>
        <div style={{ marginTop: 26 }}>
          {plan.items.map((it, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', fontFamily: FONT,
              fontSize: 44, color: C.cream, fontWeight: 700, padding: '12px 4px',
              borderBottom: '1px dashed rgba(255,220,180,.25)', ...fadeUp(f, 16 + i * 5),
            }}>
              <span>{it.name}</span>
              <span style={{ color: C.soft, fontSize: 34 }}>{it.grams}g{it.pricing === '称重' ? ' · 称重' : ''}</span>
            </div>
          ))}
        </div>
        {plan.tier && (
          <div style={{ fontFamily: FONT, fontSize: 32, color: C.orange, marginTop: 18, ...fadeUp(f, 40) }}>
            🍱 {plan.tier.n_meat}荤{plan.tier.n_veg}素档 {plan.tier.price}元 · 含米饭{plan.tier.rice_g}g
          </div>
        )}
        <div style={{ marginTop: 26, ...fadeUp(f, 46) }}>
          <Nutri price={plan.PI} kcal={plan.E} prot={plan.Q} oil={plan.O} dark fs={32} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const S3Serve: React.FC = () => {
  const f = useCurrentFrame();
  if (f >= S3_SUM) {
    const lf = f - (S3_SUM - S3_SUM_HEAD);  // 总结镜头本地帧（切换瞬间动画已接近成形）
    return (
      <AbsoluteFill style={{ background: 'linear-gradient(150deg,#3A1E0E,#201006)' }}>
        {/* AI 食欲图接入：总结镜头底改用 AI 餐盘俯拍（蒸汽暖光与全片一致，blur+压暗罩保字幕可读） */}
        <PhotoBg src="assets/photos/GEN_S3_餐盘俯拍.jpg" frame={lf} dim={0.75} blur={4} />
        {/* AI B-roll 插槽 S3_SUM（约 39.1–48.2s 总结镜头底）：Sequence from 归零视频起点 */}
        {genHas('S3_SUM') && (
          <Sequence from={S3_SUM} layout="none">
            <GenBroll slot="S3_SUM" overlay={0.55} />
          </Sequence>
        )}
        <Grain />
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          <SceneTitle main="想增肌，想省钱" sub="也都各有三套 · 价格 / 热量 / 蛋白 / 油克，标得明明白白" frame={lf} />
          <div style={{ display: 'flex', marginTop: 60 }}>
            {['🥗 减脂', '💪 增肌', '🪙 省钱', '🍚 均衡'].map((s, i) => (
              <div key={i} style={{ transform: `scale(${pop(lf, 30, 8 + i * 8)})`, margin: '0 18px' }}>
                <Tag fs={52}>{s}</Tag>
              </div>
            ))}
          </div>
        </AbsoluteFill>
        <Caption capId="S3" frame={f} />
      </AbsoluteFill>
    );
  }
  const idx = f < S3_CUT2 ? 0 : (f < S3_CUT3 ? 1 : 2);
  const base = idx === 0 ? 0 : (idx === 1 ? S3_CUT2 : S3_CUT3);
  return (
    <AbsoluteFill>
      <ServeOne idx={idx} frame={f - base} />
      <Caption capId="S3" frame={f} />
    </AbsoluteFill>
  );
};

/** S4 懂你：忌口温柔退场 → 打卡周报 → 评论标签（周报切入对齐「本周十一餐…」句起点） */
export const S4Care: React.FC = () => {
  const f = useCurrentFrame();
  if (f < S4_CUT) {
    const gone = ['香菜拌牛肉', '香菜丸子汤', '香菜拌豆腐'];
    const keep = ['清蒸鲈鱼', '冬菇蒸鸡', '白灼时蔬'];
    return (
      <AbsoluteFill style={{ background: 'linear-gradient(160deg,#33200F,#1D0E05)' }}>
        <Grain />
        <div style={{ position: 'absolute', top: 84, width: '100%' }}>
          <SceneTitle main="你说不吃香菜" sub="它就一片香菜都不撒" frame={f} />
        </div>
        {/* 列表上移+紧凑化：6 项总高收进 890px 内，避开底部字幕（y=940），不再重叠/截断 */}
        <div style={{ position: 'absolute', left: 300, top: 318, width: 1320 }}>
          {[...gone, ...keep].map((n, i) => {
            const isGone = i < 3;
            const leave = isGone ? interpolate(f, [50 + i * 14, 80 + i * 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) : 0;
            return (
              <div key={i} style={{
                fontFamily: FONT, fontSize: 44, padding: '14px 28px', margin: '10px 0',
                borderRadius: 20, background: isGone ? 'rgba(120,60,40,.25)' : 'rgba(158,212,138,.12)',
                color: isGone ? '#C9A18C' : C.cream, fontWeight: 700,
                opacity: 1 - leave * 0.92, transform: `translateX(${leave * 160}px) rotate(${leave * 6}deg)`,
                filter: isGone ? `blur(${leave * 3}px)` : 'none', ...fadeUp(f, 6 + i * 4),
              }}>
                {isGone ? '🐷 ' : '🥬 '}{n}{isGone && <span style={{ fontSize: 28, marginLeft: 24 }}>温柔退场</span>}
              </div>
            );
          })}
        </div>
        <Caption capId="S4" frame={f} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: 'linear-gradient(150deg,#2E1B0C,#1B0D04)' }}>
      <Grain />
      <div style={{ position: 'absolute', top: 70, width: '100%' }}>
        <SceneTitle main="打卡、周报，它都记着" sub="放纵餐不拦你，只帮你记着" frame={f - S4_CUT} />
      </div>
      <div style={{ position: 'absolute', left: 130, top: 340, display: 'flex', gap: 26 }}>
        {[[WEEK.n, '本周打卡(餐)'], [WEEK.normal, '正常餐'], [`${WEEK.cheat}/3`, '放纵餐'], [WEEK.cheat_left, '配额剩余'], [`${WEEK.rate}%`, '热量达标']].map(([v, lab], i) => (
          <div key={i} style={{
            width: 300, background: 'rgba(255,246,234,.06)', border: '1.5px solid rgba(255,200,150,.28)',
            borderRadius: 26, padding: '34px 0', textAlign: 'center', ...fadeUp(f - S4_CUT, 8 + i * 6),
          }}>
            <div style={{ fontFamily: FONT, fontSize: 84, fontWeight: 900, color: C.orange }}>{v}</div>
            <div style={{ fontFamily: FONT, fontSize: 30, color: C.soft, marginTop: 10 }}>{lab}</div>
          </div>
        ))}
      </div>
      <div style={{ position: 'absolute', left: 130, top: 640, display: 'flex', gap: 18 }}>
        {WEEK.days.map((d, i) => (
          <div key={i} style={{
            width: 216, height: 200, borderRadius: 22, textAlign: 'center', paddingTop: 26,
            background: `rgba(224,122,63,${d.n ? 0.25 + Math.min(0.6, d.kcal / 2400) : 0.06})`,
            border: '1px solid rgba(255,200,150,.22)', ...fadeUp(f - S4_CUT, 40 + i * 4),
          }}>
            <div style={{ fontFamily: FONT, fontSize: 34, color: C.cream, fontWeight: 800 }}>周{d.weekday}</div>
            <div style={{ fontFamily: FONT, fontSize: 56, color: C.orange, fontWeight: 900, marginTop: 12 }}>{d.n}</div>
            <div style={{ fontFamily: FONT, fontSize: 26, color: C.soft }}>餐 · {d.kcal}kcal</div>
          </div>
        ))}
      </div>
      <div style={{ position: 'absolute', top: 880, width: '100%', textAlign: 'center', ...fadeUp(f - S4_CUT, 74) }}>
        <Tag fs={30}>「按克精算，健身党狂喜」</Tag><Tag fs={30}>「猪脚饭软糯脱骨」</Tag><Tag fs={30}>「9块钱吃到撑」</Tag>
      </div>
      <Caption capId="S4" frame={f} y={980} size={40} />
    </AbsoluteFill>
  );
};

const WALL = ['清蒸南瓜', '剁椒蒸鱼', '酸菜鱼', '蒸水蛋', '冬菇蒸鸡', '咖喱鱼蛋', '红烧豆腐', '韭菜鸡蛋水饺',
  '三鲜肉水饺', '时令青蔬', '卤豆泡', '卤海带', '金牌猪脚饭', '招牌牛肉饭', '香菇滑鸡煲仔饭', '广式腊肠煲仔饭',
  '老南昌素拌粉', '牛肉拌粉', '重庆小面', '老麻抄手', '清汤抄手', '鸡丝拌面', '番茄鸡蛋面', '红烧牛肉面',
  '土豆泥炸酱面', '淮南牛肉汤', '土耳其烤肉饭', '麻辣香锅', '韩式拌饭', '苹果片', '板烧鸡腿堡', '麦咖啡',
  '黑椒肥牛煲仔饭', '番茄酥肉拌粉', '排骨拌粉', '卤鸡腿', '玉米肠', '新地', '圆筒冰淇淋', '莲藕饭'];

/** S5 靠谱：真实数据墙 + 诚实降级彩蛋 */
export const S5Trust: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / 30;
  if (t < 12) {
    return (
      <AbsoluteFill style={{ background: 'linear-gradient(160deg,#301C0C,#1A0C04)' }}>
        <Grain />
        <div style={{ position: 'absolute', top: 64, width: '100%' }}>
          <SceneTitle main="都是一份一份采回来的" sub="真菜名 · 真价格 · 真窗口" frame={f} />
        </div>
        <div style={{ position: 'absolute', left: 130, top: 300, display: 'flex', gap: 40 }}>
          {[[719, '道真实菜'], [26, '个窗口'], [6, '个食堂区']].map(([v, lab], i) => (
            <div key={i} style={{ textAlign: 'center', ...fadeUp(f, 8 + i * 8) }}>
              <div style={{ fontFamily: FONT, fontSize: 150, fontWeight: 900, color: C.orange }}>
                {Math.round(interpolate(f, [10 + i * 8, 60 + i * 8], [0, v as number], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }))}
              </div>
              <div style={{ fontFamily: FONT, fontSize: 40, color: C.soft }}>{lab}</div>
            </div>
          ))}
        </div>
        <div style={{ position: 'absolute', left: 100, top: 600, width: 1720, height: 300, overflow: 'hidden' }}>
          {[0, 1, 2].map((row) => (
            <div key={row} style={{
              display: 'flex', whiteSpace: 'nowrap',
              transform: `translateX(${-f * (row % 2 ? -1.6 : 1.6) - row * 200}px)`,
            }}>
              {[...WALL.slice(row * 13, row * 13 + 13), ...WALL.slice(row * 13, row * 13 + 13)].map((n, i) => (
                <span key={i} style={{
                  fontFamily: FONT, fontSize: 34, color: 'rgba(255,230,205,.75)', margin: '12px 16px',
                  background: 'rgba(255,200,150,.07)', padding: '10px 24px', borderRadius: 14,
                  border: '1px solid rgba(255,200,150,.16)',
                }}>{n}</span>
              ))}
            </div>
          ))}
        </div>
        <Caption capId="S5" frame={f} y={960} size={40} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: 'linear-gradient(150deg,#2C190B,#190C04)' }}>
      <Grain />
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        <SceneTitle main="夜宵没得选的时候" sub="它会说「建议」，而不是硬塞给你一个答案" frame={f - 360} />
        <div style={{
          marginTop: 60, background: '#FFFBF3', borderRadius: 30, padding: '40px 60px',
          width: 1150, boxShadow: '0 30px 80px rgba(0,0,0,.5)', ...fadeUp(f - 360, 16),
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <span style={{ background: '#FBE3DF', color: '#B44436', borderRadius: 999, padding: '8px 26px', fontSize: 34, fontWeight: 800, fontFamily: FONT }}>建议</span>
            <span style={{ fontFamily: FONT, fontSize: 38, color: C.ink, fontWeight: 800 }}>校内饭店 · 麦当劳</span>
          </div>
          <div style={{ fontFamily: FONT, fontSize: 34, color: '#7A6350', marginTop: 26, lineHeight: 1.7 }}>
            主食与荤菜槽位已放宽 · 供给有限，如实相告<br />
            说实话的搭子，才配替你拿主意。
          </div>
        </div>
      </AbsoluteFill>
      <Caption capId="S5" frame={f} />
    </AbsoluteFill>
  );
};
