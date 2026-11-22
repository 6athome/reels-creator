import caption from '../../config/presets/eunpanchi-signature.json';
import bold from '../../config/presets/bold-hook.json';
import story from '../../config/presets/storytelling.json';
import playful from '../../config/presets/playful-impact.json';

export type SafeArea = {left: number; top: number; right: number; bottom: number};
type Background = {mode: string; color: string; opacity: number; paddingXPx: number; paddingYPx: number; borderRadiusPx: number};
type Shadow = {xPx: number; yPx: number; blurPx: number; color: string; opacity: number};
type Stroke = {widthPx: number; color: string; opacity: number};
export type TextStyle = {
  id: string;
  position: {x: number; y: number; anchor: string};
  maxWidthPx: number;
  textAlign: string;
  fontFamilies: string[];
  fontSizePx: number;
  fontWeight: number;
  fallbackFontWeight?: number;
  color: string;
  lineHeightPx: number;
  letterSpacingPx: number;
  maxLines: number;
  background: Background | null;
  shadow: Shadow | null;
  stroke: Stroke | null;
  lineGapPx: number;
  appearance: string;
  alternateColors?: string[];
};
export type Preset = {
  schemaVersion: number;
  id: string;
  kind: string;
  canvas: {width: number; height: number; fps: number};
  safeArea: SafeArea;
  photoShade?: string;
  layers: TextStyle[];
};

export const signaturePreset: Preset = caption;
export const coverPresets = {bold, story, playful} satisfies Record<string, Preset>;
