const {createRequire} = require('node:module');
const {readFileSync, existsSync, readdirSync} = require('node:fs');
const {resolve, join} = require('node:path');

const fromCli = createRequire(require.resolve('@remotion/cli/package.json'));
const {bundle} = fromCli('@remotion/bundler');
const {openBrowser, renderMedia, renderStill, selectComposition} = fromCli('@remotion/renderer');

function installedBrowser(directory) {
  if (!existsSync(directory)) return undefined;
  for (const entry of readdirSync(directory, {withFileTypes: true})) {
    const child = join(directory, entry.name);
    if (entry.isDirectory()) {
      const result = installedBrowser(child);
      if (result) return result;
    }
    if (/^chrome-headless-shell(?:\.exe)?$/.test(entry.name) && !entry.isDirectory() && existsSync(child)) return child;
  }
}

async function main() {
  const [work, output, explicitBrowser] = process.argv.slice(2);
  const cache = resolve(__dirname, 'node_modules/.remotion');
  const windowsBrowser = join(cache, 'chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe');
  const browserExecutable = explicitBrowser || process.env.REELS_BROWSER ||
    (process.platform === 'win32' && existsSync(windowsBrowser) ? windowsBrowser : installedBrowser(cache));
  if (!browserExecutable || !existsSync(browserExecutable)) {
    throw new Error('Use --browser or REELS_BROWSER with an installed Chromium, or prepare the Remotion browser first.');
  }
  const {expectAudio, coverOnly, ...inputProps} = JSON.parse(readFileSync(join(work, 'props.json'), 'utf8'));
  const serveUrl = await bundle({
    entryPoint: resolve(__dirname, 'src/index.ts'),
    publicDir: join(work, 'public'),
    outDir: join(work, 'bundle'),
  });
  const puppeteerInstance = await openBrowser('chrome', {browserExecutable});
  const options = {serveUrl, puppeteerInstance, inputProps, timeoutInMilliseconds: 90000};
  try {
    console.log('[remotion] cover PNG');
    const cover = await selectComposition({...options, id: 'ReelProjectCover'});
    await renderStill({...options, composition: cover, imageFormat: 'png',
      output: join(output, 'cover.png'), overwrite: false});
    if (coverOnly) return;
    const video = await selectComposition({...options, id: 'ReelProject'});
    let reported = -1;
    console.log('[remotion] MP4 ' + video.durationInFrames + ' frames');
    await renderMedia({
      ...options, composition: video, codec: inputProps.plan.renderSettings.codec,
      concurrency: inputProps.plan.renderSettings.concurrency, muted: !expectAudio,
      outputLocation: join(output, 'reel.mp4'), overwrite: false,
      onProgress({renderedFrames}) {
        const progress = Math.floor(renderedFrames / video.durationInFrames * 4);
        if (progress > reported) {
          reported = progress;
          console.log('[remotion] ' + renderedFrames + '/' + video.durationInFrames);
        }
      },
    });
  } finally {
    await puppeteerInstance.close({silent: true});
  }
}

main().catch((error) => {
  console.error('[remotion] ' + error.stack);
  process.exitCode = 1;
});
