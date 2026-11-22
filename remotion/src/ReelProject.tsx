import {AbsoluteFill, Html5Audio, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import fontSettings from '../../config/local-fonts.json';
import {LocalFontLoader} from './components/LocalFontLoader';
import {ReelCover, type CoverContent} from './components/ReelCover';
import {ReelsSafeAreaOverlay} from './components/ReelsSafeAreaOverlay';
import {SignatureCaption, type CaptionCue} from './components/SignatureCaption';
import {coverPresets, signaturePreset, type TextStyle} from './stylePresets';

type StyleOverride = Partial<Pick<TextStyle, 'fontFamilies' | 'fontSizePx' | 'fontWeight' | 'color' | 'lineGapPx' | 'lineHeightPx' | 'maxWidthPx'>> & {
  x?: number;
  y?: number;
  backgroundColor?: string;
  backgroundOpacity?: number;
  paddingXPx?: number;
  paddingYPx?: number;
};
type Clip = {
  assetId: string;
  sourceStart: number;
  sourceEnd: number;
  timelineStartFrame: number;
  durationFrames: number;
  fit: 'cover' | 'contain' | 'blur';
  objectPosition?: string;
  useSourceAudio: boolean;
  motion: 'none' | 'push-in' | 'pan-left' | 'pan-right';
};
type CoverId = 'bold-hook' | 'storytelling' | 'playful-impact';
type Plan = {
  fps: number;
  resolution: {width: number; height: number};
  clips: Clip[];
  mediaAssets: {id: string; kind: 'image' | 'video'}[];
  captions: (CaptionCue & {style: StyleOverride})[];
  cover: {preset: CoverId; text: Record<string, string>; objectPosition?: string; overrides?: Record<string, StyleOverride>};
  audioSettings: {sourceVolume: number; musicVolume: number; fadeOutFrames: number};
};

export type ReelProjectProps = {
  plan?: Plan;
  assetPaths?: Record<string, string>;
  coverPath?: string;
  musicPath?: string | null;
  captionColors?: StyleOverride;
  personalStyle?: {
    caption?: StyleOverride;
    cover?: {preset?: CoverId; layers?: Record<string, StyleOverride>};
  };
};

export function reelMetadata({props}: {props: ReelProjectProps}) {
  if (!props.plan) return {};
  const {fps, resolution, clips} = props.plan;
  return {...resolution, fps, durationInFrames: clips.reduce((sum, clip) => sum + clip.durationFrames, 0)};
}

function overrideStyle(layer: TextStyle, changes: StyleOverride = {}): TextStyle {
  const {x, y, backgroundColor, backgroundOpacity, paddingXPx, paddingYPx, ...rest} = changes;
  const bg = layer.background;
  return {
    ...layer, ...rest,
    position: {...layer.position, x: x ?? layer.position.x, y: y ?? layer.position.y},
    background: bg ? {
      ...bg, color: backgroundColor ?? bg.color, opacity: backgroundOpacity ?? bg.opacity,
      paddingXPx: paddingXPx ?? bg.paddingXPx, paddingYPx: paddingYPx ?? bg.paddingYPx,
    } : null,
  };
}

function ReelClip({clip, source, kind, volume}: {
  clip: Clip;
  source: string;
  kind: 'image' | 'video';
  volume: (frame: number) => number;
}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = Math.max(0, Math.min(1, frame / Math.max(1, clip.durationFrames - 1)));
  const direction = clip.motion === 'pan-left' ? -1 : 1;
  const isPan = clip.motion === 'pan-left' || clip.motion === 'pan-right';
  const scale = isPan ? 1.08 : clip.motion === 'push-in' ? 1 + 0.07 * progress : 1;
  const translate = isPan ? `${direction * (progress - 0.5) * 5}% 0` : undefined;
  const style = {
    width: '100%', height: '100%',
    objectFit: clip.fit === 'blur' ? 'contain' as const : clip.fit,
    objectPosition: clip.objectPosition,
  };
  const blurred = {...style, position: 'absolute' as const, inset: 0, objectFit: 'cover' as const,
    filter: 'blur(44px) brightness(0.56)', scale: '1.12'};
  const foreground = {...style, position: 'relative' as const, zIndex: 1};
  const trimBefore = Math.round(clip.sourceStart * fps);
  const trimAfter = Math.round(clip.sourceEnd * fps);
  return <AbsoluteFill style={{backgroundColor: '#101318', overflow: 'hidden', isolation: 'isolate'}}>
    {clip.fit === 'blur' ? kind === 'image'
      ? <Img src={source} style={blurred} />
      : <OffthreadVideo src={source} trimBefore={trimBefore} trimAfter={trimAfter} muted style={blurred} />
      : null}
    {kind === 'image' ? <Img src={source} style={{...foreground, scale: String(scale), translate}} /> :
      <OffthreadVideo src={source} trimBefore={trimBefore}
        trimAfter={trimAfter} muted={!clip.useSourceAudio}
        volume={volume} style={foreground} />}
  </AbsoluteFill>;
}

export function ReelTimeline({plan, assetPaths = {}, musicPath, personalStyle, captionColors}: ReelProjectProps) {
  const {durationInFrames, fps} = useVideoConfig();
  if (!plan) return <AbsoluteFill style={{backgroundColor: '#101318'}} />;
  const {audioSettings} = plan;
  const layer = signaturePreset.layers[0];
  const assetKinds = new Map(plan.mediaAssets.map(({id, kind}) => [id, kind]));
  const fadeLength = Math.min(durationInFrames, audioSettings.fadeOutFrames);
  const fade = (frame: number) => fadeLength === 0 ? 1 :
    Math.max(0, Math.min(1, (durationInFrames - 1 - frame) / fadeLength));

  return <LocalFontLoader fonts={fontSettings.fonts}>
    {plan.clips.map((clip) => <Sequence key={clip.timelineStartFrame} from={clip.timelineStartFrame}
      durationInFrames={clip.durationFrames} premountFor={fps}>
      <ReelClip source={staticFile(assetPaths[clip.assetId])} kind={assetKinds.get(clip.assetId)!} clip={clip}
        volume={(frame) => audioSettings.sourceVolume * fade(frame + clip.timelineStartFrame)} />
    </Sequence>)}
    {musicPath ? <Html5Audio src={staticFile(musicPath)} loop loopVolumeCurveBehavior="extend"
      volume={(frame) => audioSettings.musicVolume * fade(frame)} /> : null}
    {plan.captions.map((cue) => <SignatureCaption key={cue.startFrame} cue={cue}
      style={overrideStyle(layer, {...captionColors, ...personalStyle?.caption, ...cue.style})} />)}
    <ReelsSafeAreaOverlay area={signaturePreset.safeArea} />
  </LocalFontLoader>;
}

const covers = {
  'bold-hook': coverPresets.bold,
  'storytelling': coverPresets.story,
  'playful-impact': coverPresets.playful,
};

export function ProjectCover({plan, coverPath, personalStyle}: ReelProjectProps) {
  if (!plan) return <AbsoluteFill style={{backgroundColor: '#101318'}} />;
  if (!coverPath) throw new Error('Choose a cover photo or video frame before rendering.');
  const preset = covers[plan.cover.preset];
  const saved = personalStyle?.cover;
  const layers = !saved?.preset || saved.preset === plan.cover.preset ? saved?.layers : undefined;
  const content: CoverContent = {
    text: plan.cover.text,
    background: {
      color: '#211A22', photo: coverPath, objectPosition: plan.cover.objectPosition,
      shade: Object.keys(plan.cover.text).length ? preset.photoShade : undefined,
    },
    overrides: Object.fromEntries(preset.layers.map((layer) => [
      layer.id, overrideStyle(layer, {...layers?.[layer.id], ...plan.cover.overrides?.[layer.id]}),
    ])),
  };
  return <LocalFontLoader fonts={fontSettings.fonts}>
    <ReelCover preset={preset} content={content} />
    <ReelsSafeAreaOverlay area={preset.safeArea} />
  </LocalFontLoader>;
}
