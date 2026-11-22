import {AbsoluteFill, Img, staticFile} from 'remotion';
import type {Preset, TextStyle} from '../stylePresets';
import {TextLayer} from './TextLayer';

export type CoverContent = {
  text: Record<string, string>;
  overrides?: Record<string, Partial<Omit<TextStyle, 'id'>>>;
  background: {color: string; photo?: string; objectPosition?: string; shade?: string};
};

export function ReelCover({preset, content}: {preset: Preset; content: CoverContent}) {
  const {background} = content;
  return <AbsoluteFill style={{background: background.color}}>
    {background.photo ? <Img src={(background.photo.startsWith('http://127.0.0.1:') ? background.photo : staticFile(background.photo))} style={{
      width: '100%', height: '100%', objectFit: 'cover', objectPosition: background.objectPosition,
    }} /> : null}
    {background.shade ? <AbsoluteFill style={{background: background.shade}} /> : null}
    {preset.layers.map((layer) => <TextLayer key={layer.id} coverCanvas={preset.canvas}
      style={{...layer, ...content.overrides?.[layer.id]}}
      text={content.text[layer.id] ?? ''} />)}
  </AbsoluteFill>;
}
