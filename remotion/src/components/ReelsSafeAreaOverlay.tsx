import {AbsoluteFill, useRemotionEnvironment} from 'remotion';
import type {SafeArea} from '../stylePresets';

export function ReelsSafeAreaOverlay({area, diagnostic = false}: {area: SafeArea; diagnostic?: boolean}) {
  const {isStudio} = useRemotionEnvironment();
  if (!diagnostic && !isStudio) return null;
  const {left, top, right, bottom} = area;
  const caution = 'rgba(247, 131, 108, 0.26)';
  return <AbsoluteFill aria-hidden style={{pointerEvents: 'none', fontFamily: 'Malgun Gothic, sans-serif', fontSize: 28, fontWeight: 700, color: '#FFFFFF'}}>
    <div style={{position: 'absolute', inset: `0 0 auto 0`, height: top, background: caution, padding: '48px 72px', boxSizing: 'border-box'}}>상단 주의 영역</div>
    <div style={{position: 'absolute', inset: `${bottom}px 0 0 0`, background: caution, padding: '34px 72px'}}>하단 주의 영역</div>
    <div style={{position: 'absolute', inset: `${top}px 0 auto ${right}px`, height: bottom - top, background: caution, writingMode: 'vertical-rl', padding: '32px 38px', boxSizing: 'border-box'}}>오른쪽 버튼 영역</div>
    <div style={{position: 'absolute', left, top, width: right-left, height: bottom-top, boxSizing: 'border-box',
      border: '4px dashed #61E0C2', padding: 18, color: '#61E0C2'}}>중앙 권장 텍스트 영역</div>
  </AbsoluteFill>;
}
