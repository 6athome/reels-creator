import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import fontSettings from '../../config/local-fonts.json';
import {LocalFontLoader, type LocalFont} from './components/LocalFontLoader';
import {ReelCover, type CoverContent} from './components/ReelCover';
import {ReelsSafeAreaOverlay} from './components/ReelsSafeAreaOverlay';
import {SignatureCaption} from './components/SignatureCaption';
import {coverPresets, signaturePreset, type SafeArea, type TextStyle} from './stylePresets';

const fonts: LocalFont[] = fontSettings.fonts;
const photo = 'demo/test-backdrop.jpg';
const singleLine = '너무 영롱하지 않나요?';
const twoLines = '잘 어울릴 것 같아서 산토스 뒤몽\n가죽스트랩 중 고민이었는데요';
const longLine = '매장에 도착해서 여러 시계를 하나씩 비교해 보고 어떤 선물이 가장 잘 어울릴지 오래 고민했어요';

function DemoBackdrop({zoom = 1}: {zoom?: number}) {
  return <AbsoluteFill style={{background: '#383139', overflow: 'hidden'}}>
    <Img src={staticFile(photo)} style={{width: '100%', height: '100%', objectFit: 'cover', scale: String(zoom)}} />
  </AbsoluteFill>;
}

export type CaptionDemoProps = {captionStyle?: TextStyle; guideArea?: SafeArea};

function SignatureScene({captionStyle, guideArea, diagnostic}: CaptionDemoProps & {diagnostic: boolean}) {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  return <LocalFontLoader fonts={fonts}>
    <DemoBackdrop zoom={interpolate(frame, [0, durationInFrames - 1], [1, 1.09])} />
    <SignatureCaption style={captionStyle} cue={{text: singleLine, startFrame: 12, endFrame: 3 * fps}} />
    <SignatureCaption style={captionStyle} cue={{text: twoLines, startFrame: 3 * fps, endFrame: 6 * fps}} />
    <SignatureCaption style={captionStyle} cue={{text: longLine, startFrame: 6 * fps, endFrame: 9 * fps + 15, fadeFrames: 6}} />
    <ReelsSafeAreaOverlay area={guideArea ?? signaturePreset.safeArea} diagnostic={diagnostic} />
  </LocalFontLoader>;
}

export function SignatureDemo(props: CaptionDemoProps) {
  return <SignatureScene {...props} diagnostic={false} />;
}

export function SafeAreaDiagnostic() {
  return <SignatureScene diagnostic />;
}

const coverContent: Record<keyof typeof coverPresets, CoverContent> = {
  bold: {
    text: {title: '인테리어 비용\n공제될까요?', subtitle: '인테리어할 때 꼭 챙겨둘 것'},
    background: {color: 'linear-gradient(165deg, #9A5640 0%, #472C29 100%)'},
  },
  story: {
    text: {title: '남편 몰래\n시계를 샀어요'},
    background: {color: '#211A22', photo, objectPosition: 'center'},
  },
  playful: {
    text: {'lead-1': '평범한 건', 'lead-2': '싫은', 'lead-3': '신혼부부의', keyword: '주방'},
    background: {color: 'linear-gradient(160deg, #9E7C65 0%, #695046 100%)'},
  },
};
type CoverDemoProps = {variant: keyof typeof coverPresets; content?: CoverContent; guideArea?: SafeArea};
export function CoverDemo({variant, content, guideArea}: CoverDemoProps) {
  const preset = coverPresets[variant];
  return <LocalFontLoader fonts={fonts}>
    <ReelCover preset={preset} content={content ?? coverContent[variant]} />
    <ReelsSafeAreaOverlay area={guideArea ?? preset.safeArea} />
  </LocalFontLoader>;
}
