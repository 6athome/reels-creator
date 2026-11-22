import {useCurrentFrame} from 'remotion';
import {signaturePreset, type TextStyle} from '../stylePresets';
import {TextLayer} from './TextLayer';

export type CaptionCue = {text: string; startFrame: number; endFrame: number; fadeFrames?: number};

export function SignatureCaption({cue, style = signaturePreset.layers[0]}: {cue: CaptionCue; style?: TextStyle}) {
  const frame = useCurrentFrame();
  if (frame < cue.startFrame || frame >= cue.endFrame) return null;
  const fade = Math.max(0, Math.min(cue.fadeFrames ?? 0, Math.floor((cue.endFrame - cue.startFrame - 1) / 2)));
  const opacity = fade > 0 ? Math.min(1, (frame - cue.startFrame) / fade, (cue.endFrame - 1 - frame) / fade) : 1;
  return <TextLayer style={style} text={cue.text} opacity={opacity} />;
}
