import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

export function EnvironmentSmoke() {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const progress = (frame + 1) / durationInFrames;

  return (
    <AbsoluteFill style={{
      backgroundColor: '#101827',
      color: '#F8FAFC',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'sans-serif',
      fontSize: 64,
      fontWeight: 700,
    }}>
      REELS CREATOR · TEST
      <div style={{
        position: 'absolute',
        bottom: 180,
        left: 90,
        width: 900 * progress,
        height: 12,
        backgroundColor: '#38BDF8',
      }} />
    </AbsoluteFill>
  );
}
