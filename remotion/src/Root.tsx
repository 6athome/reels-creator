import {Composition, Still} from 'remotion';
import preset from '../../config/presets/default.json';
import {EnvironmentSmoke} from './components/EnvironmentSmoke';
import {CoverDemo, SafeAreaDiagnostic, SignatureDemo, type CaptionDemoProps} from './SignatureDemos';
import {signaturePreset} from './stylePresets';
import {ProjectCover, ReelTimeline, reelMetadata, type ReelProjectProps} from './ReelProject';

const {width, height, fps} = signaturePreset.canvas;
const portrait = {width, height};
const demoProps: CaptionDemoProps = {};
const projectProps: ReelProjectProps = {};

export function Root() {
  return <>
    <Composition
      id="EnvironmentSmoke"
      component={EnvironmentSmoke}
      durationInFrames={preset.canvas.fps * 2}
      fps={preset.canvas.fps}
      width={preset.canvas.width}
      height={preset.canvas.height}
    />
    <Composition id="SignatureDemo" component={SignatureDemo} {...portrait} fps={fps} durationInFrames={10 * fps} defaultProps={demoProps} />
    <Still id="BoldHookCover" component={CoverDemo} {...portrait} defaultProps={{variant: 'bold'}} />
    <Still id="StorytellingCover" component={CoverDemo} {...portrait} defaultProps={{variant: 'story'}} />
    <Still id="PlayfulImpactCover" component={CoverDemo} {...portrait} defaultProps={{variant: 'playful'}} />
    <Composition id="SafeAreaDiagnostic" component={SafeAreaDiagnostic} {...portrait} fps={fps} durationInFrames={10 * fps} />
    <Composition id="ReelProject" component={ReelTimeline} {...portrait} fps={fps} durationInFrames={1}
      calculateMetadata={reelMetadata} defaultProps={projectProps} />
    <Still id="ReelProjectCover" component={ProjectCover} {...portrait} defaultProps={projectProps} />
  </>;
}
