import {useMemo} from 'react';
import type {TextStyle} from '../stylePresets';
import {useLocalFontAliases} from './LocalFontLoader';

const graphemes = new Intl.Segmenter('ko', {granularity: 'grapheme'});
const characters = (text: string) => Array.from(graphemes.segment(text), ({segment}) => segment);
const translucent = (color: string, opacity: number) =>
  `color-mix(in srgb, ${color} ${opacity * 100}%, transparent)`;

function wrap(text: string, width: number, limit: number, measure: (value: string) => number) {
  const result: string[] = [];
  let missingGlyphWidth = false;
  for (const paragraph of text.trim().split(/\r?\n/u)) {
    const units = characters(paragraph.trim());
    if (!units.length) result.push('');
    while (units.length) {
      let end = 0;
      while (end < units.length && measure(units.slice(0, end + 1).join('')) <= width) end++;
      if (end > 0 && end < units.length && !/\s/u.test(units[end])) {
        let space = end - 1;
        while (space > 0 && !/\s/u.test(units[space])) space--;
        if (space > 0) end = space;
      }
      if (end === 0) {
        missingGlyphWidth = true;
        result.push('…');
        units.shift();
      } else {
        result.push(units.splice(0, end).join('').trimEnd());
      }
      while (units.length && /\s/u.test(units[0])) units.shift();
      if (result.length > limit) break;
    }
    if (result.length > limit) break;
  }

  if (result.length <= limit) return {lines: result, overflow: missingGlyphWidth};
  const kept = result.slice(0, limit);
  const tail = characters(kept[limit - 1].trimEnd());
  while (tail.length && measure(`${tail.join('')}…`) > width) tail.pop();
  kept[limit - 1] = `${tail.join('').trimEnd()}…`;
  return {lines: kept, overflow: true};
}

export function TextLayer({style, text, opacity = 1, coverCanvas}: {
  style: TextStyle; text: string; opacity?: number; coverCanvas?: {width: number; height: number};
}) {
  const aliases = useLocalFontAliases();
  const requestedFallback = style.fallbackFontWeight ?? style.fontWeight;
  const weight = requestedFallback <= 350 ? 300 : requestedFallback >= 600 ? 700 : 400;
  const systemFace = aliases?.['Malgun Gothic']?.[weight];
  const family = style.fontFamilies.flatMap((name) => {
    if (name === 'Malgun Gothic' && systemFace) return [JSON.stringify(systemFace), JSON.stringify(name)];
    if (name === 'sans-serif') return systemFace ? [JSON.stringify(systemFace), '"Malgun Gothic"', name] : [name];
    return [JSON.stringify(name)];
  }).join(', ');
  const bg = style.background;
  const paddingX = bg?.paddingXPx ?? 0;
  const paddingY = bg?.paddingYPx ?? 0;
  const {x, y} = style.position;
  const width = coverCanvas ? Math.min(style.maxWidthPx, 2 * Math.min(x, coverCanvas.width - x) - 2) : style.maxWidthPx;
  const height = coverCanvas ? 2 * Math.min(y, coverCanvas.height - y) - 2 : Infinity;
  const ready = aliases !== null;
  const {lines, fontSize} = useMemo(() => {
    if (!ready || !text.trim()) return {lines: [], fontSize: style.fontSizePx};
    const context = document.createElement('canvas').getContext('2d');
    if (!context) throw new Error('Could not measure reel text');
    context.letterSpacing = `${style.letterSpacingPx}px`;
    const minimum = coverCanvas ? Math.min(style.fontSizePx, Math.ceil(Math.max(43, style.fontSizePx * 0.48))) : style.fontSizePx;
    for (let size = style.fontSizePx; size >= minimum; size = Math.max(minimum, size - 2)) {
      context.font = `${style.fontWeight} ${size}px ${family}`;
      const layout = wrap(text, width - 2 * paddingX - 1, style.maxLines,
        (value) => context.measureText(value).width);
      const totalHeight = layout.lines.length * (style.lineHeightPx * size / style.fontSizePx + 2 * paddingY)
        + (layout.lines.length - 1) * style.lineGapPx;
      if (!coverCanvas || (!layout.overflow && totalHeight <= height)) return {lines: layout.lines, fontSize: size};
      if (size === minimum) break;
    }
    throw new Error(`Cover text does not fit layer "${style.id}". Shorten the wording or adjust its width and line breaks.`);
  }, [ready, text, family, style.fontWeight, style.fontSizePx, style.letterSpacingPx, style.maxLines,
    style.lineHeightPx, style.lineGapPx, style.id, paddingX, paddingY, width, height, coverCanvas]);
  if (!lines.length) return null;

  const {shadow, stroke, position} = style;
  return <div lang="ko" style={{
    position: 'absolute', left: position.x, top: position.y, translate: '-50% -50%',
    width, display: 'flex', flexDirection: 'column', opacity,
    alignItems: style.textAlign === 'left' ? 'flex-start' : style.textAlign === 'right' ? 'flex-end' : 'center',
    gap: style.lineGapPx, fontFamily: family, fontSize, fontWeight: style.fontWeight,
    letterSpacing: style.letterSpacingPx, color: style.color,
  }}>
    {lines.map((line, index) => <div key={index} style={{
      whiteSpace: 'pre', maxWidth: '100%', overflow: 'visible', boxSizing: 'border-box',
      lineHeight: `${style.lineHeightPx * fontSize / style.fontSizePx}px`, padding: `${paddingY}px ${paddingX}px`,
      borderRadius: bg?.borderRadiusPx, backgroundColor: bg ? translucent(bg.color, bg.opacity) : undefined,
      textShadow: shadow ? `${shadow.xPx}px ${shadow.yPx}px ${shadow.blurPx}px ${translucent(shadow.color, shadow.opacity)}` : undefined,
      WebkitTextStroke: stroke ? `${stroke.widthPx}px ${translucent(stroke.color, stroke.opacity)}` : undefined,
      paintOrder: 'stroke fill',
    }}>{line || '\u00a0'}</div>)}
  </div>;
}
