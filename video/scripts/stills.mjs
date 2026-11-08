// stills.mjs —— 一次打包，批量抽帧生成审片剧照表（123s 时间轴，共 3690 帧）
// 用法: node scripts/stills.mjs   （渲染授权门前置：给用户审剧照；可传过滤词如 node scripts/stills.mjs S4 S6）
// 幕起止自动读 narration.json；帧号 = 幕起点 + 表内偏移秒，不再手写绝对帧
import { bundle } from '@remotion/bundler';
import { getCompositions, renderStill } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const BROWSER = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const FPS = 30;
const ROOT = path.resolve();
const OUT = path.resolve('out/stills');
fs.mkdirSync(OUT, { recursive: true });

// 每幕 2 张关键帧：[剧照名, 相对幕起点的偏移秒]（偏移按各幕内容时刻标定）
const SHOTS = [
  ['S1a_痛_弹幕', 3.0], ['S1b_痛_719', 10.0],
  ['S2a_转折_打字', 3.0], ['S2b_转折_chips', 9.0],
  ['S3a_上菜_第一套', 2.8], ['S3b_上菜_总结', 18.2],
  ['S4a_懂你_忌口', 2.6], ['S4b_懂你_周报', 10.0],
  ['S5a_靠谱_数据墙', 3.0], ['S5b_靠谱_建议卡', 13.3],
  ['S6a_价值_三卡', 3.4], ['S6b_价值_动效', 9.6],
  ['S7a_收尾_团队', 1.5], ['S7b_收尾_尾板', 15.3],
];

const NARR = JSON.parse(fs.readFileSync(path.join(ROOT, 'narration.json'), 'utf8'));
const frameOf = (name, off) => {
  const sc = NARR.find((s) => s.id === name.slice(0, 2));
  if (!sc) throw new Error(`narration.json 缺幕 ${name.slice(0, 2)}`);
  return Math.min(Math.round((sc.start + off) * FPS), Math.round(sc.end * FPS) - 1);  // 不许超总帧
};

// 全量运行（未传过滤词）时清掉旧剧照，保证目录里恰好是本次 14 张；带过滤词只补渲个别
const filter = process.argv.slice(2);
if (!filter.length) {
  for (const old of fs.readdirSync(OUT)) {
    if (old.toLowerCase().endsWith('.png')) fs.unlinkSync(path.join(OUT, old));
  }
}

console.log('打包中（首次约 3 分钟）…');
const serveUrl = await bundle('src/index.ts');
const comps = await getCompositions(serveUrl, { browserExecutable: BROWSER });
const composition = comps.find((c) => c.id === 'GanFan');
console.log('composition:', composition.id, composition.durationInFrames, '帧');

for (const [name, off] of SHOTS) {
  if (filter.length && !filter.some((f) => name.startsWith(f))) continue;
  const frame = frameOf(name, off);
  const output = path.join(OUT, name + '.png');
  await renderStill({
    composition, serveUrl, output, frame,
    browserExecutable: BROWSER, imageFormat: 'png',
  });
  console.log('✓', name, 'frame', frame);
}
console.log('全部剧照 →', OUT);
