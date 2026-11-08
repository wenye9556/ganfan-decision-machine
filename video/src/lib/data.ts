import captionsJson from '../../public/data/captions.json';
import plansJson from '../../public/data/plans.json';
import statsJson from '../../public/data/stats.json';
import weekJson from '../../public/data/week.json';
import narrJson from '../../narration.json';

export interface CharCap { t: string; s: number; e: number }
export interface SceneCap {
  id: string; start: number; end: number; audio: string; duration: number; chars: CharCap[];
}
export interface MealItem { name: string; win: string; pricing: string; grams: number; price: number; cat: string }
export interface MealPlan {
  items: MealItem[]; tier: null | { n_meat: number; n_veg: number; price: number; mode: string; rice_g: number };
  E: number; Q: number; O: number; PI: number; C: number; status: string; label: string;
  wins: string[]; cant: string[]; relax: Record<string, number>; tag?: string;
}

export const CAPS = captionsJson as SceneCap[];
export const PLANS = plansJson as unknown as Record<string, { top3: MealPlan[]; reasons: string[] }>;
export const STATS = statsJson;
export const WEEK = weekJson;
export const NARR = narrJson as unknown as { id: string; name: string; start: number; end: number; text: string }[];

export const FPS = 30;
export const sec = (s: number) => Math.round(s * FPS);
export const capOf = (id: string) => CAPS.find((c) => c.id === id)!;

/** 画面切点统一比旁白句起点提前的秒数（语音落在画面上，而非画面追语音） */
export const CUE_LEAD = 0.25;

/** 按去掉标点后的句首前缀找旁白句，返回句起点秒数（幕内时间，来自 captions 字级时间）。
 *  用于把切镜/换卡帧号从旁白数据算出来，替代手写魔法数。找不到即抛错（构建期暴露）。 */
export const sentStartByPrefix = (capId: string, prefix: string): number => {
  const ss = sentencesOf(capOf(capId));
  const plain = (s: Sentence) => s.display.map((d) => d.ch).join('').replace(/[。！？；!?;，、,.：:\s　]/g, '');
  const hit = ss.find((s) => plain(s).startsWith(prefix));
  if (!hit) throw new Error(`sentStartByPrefix: 未找到句子 ${capId} "${prefix}"`);
  return hit.s;
};

/** 切点帧号 = 句起点 - CUE_LEAD */
export const cutFrameByPrefix = (capId: string, prefix: string): number =>
  Math.round((sentStartByPrefix(capId, prefix) - CUE_LEAD) * FPS);

/** 当前时刻已说到的字数（用于逐字高亮） */
export const spokenCount = (cap: SceneCap, tSec: number) => {
  let n = 0;
  for (const c of cap.chars) {
    if (tSec >= c.s - 0.06) n++;
    else break;
  }
  return n;
};

export const fullText = (cap: SceneCap) => cap.chars.map((c) => c.t).join('');

/** 按句读拆分字幕：edge-tts 字级流不含标点，故用旁白原文切句，
 * 并把每个无标点字对齐回字级时间轴；标点跟随前一字高亮。 */
export interface Sentence { display: { ch: string; ci: number | null }[]; s: number; e: number }
export const sentencesOf = (cap: SceneCap): Sentence[] => {
  const raw = NARR.find((n) => n.id === cap.id)!.text;
  const parts = raw.match(/[^。！？；!?;]+[。！？；!?;]?/g) || [raw];
  const out: Sentence[] = [];
  let gi = 0;
  for (const p of parts) {
    const display: { ch: string; ci: number | null }[] = [];
    let first: CharCap | undefined;
    let last: CharCap | undefined;
    for (const ch of p) {
      if ('。！？；!?;，、,.：: 　'.includes(ch)) {
        display.push({ ch, ci: null });
        continue;
      }
      const cc = cap.chars[gi];
      if (cc) {
        first = first || cc;
        last = cc;
      }
      display.push({ ch, ci: cc ? gi : null });
      gi++;
    }
    out.push({ display, s: first ? first.s : 0, e: last ? last.e : 0 });
  }
  return out;
};

export const currentSentence = (cap: SceneCap, tSec: number): Sentence => {
  const ss = sentencesOf(cap);
  for (const s of ss) {
    if (tSec < s.e + 0.45) return s;
  }
  return ss[ss.length - 1];
};
