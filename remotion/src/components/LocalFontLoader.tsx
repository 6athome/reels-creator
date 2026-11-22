import {createContext, type ReactNode, useContext, useEffect, useLayoutEffect, useState} from 'react';
import {staticFile, useDelayRender} from 'remotion';

export type LocalFont = {family: string; file: string; weight: string};
export type FontAliases = Record<string, Record<number, string>>;
const FontContext = createContext<FontAliases | null>(null);
const loadedFaces = new Map<string, Promise<void>>();

function loadFace(family: string, source: string, weight: string) {
  const key = JSON.stringify([family, source, weight]);
  const cached = loadedFaces.get(key);
  if (cached) return cached;

  const loading = new FontFace(family, source, {weight}).load().then((face) => {
    document.fonts.add(face);
  });
  loadedFaces.set(key, loading);
  return loading;
}

const systemCandidates = [
  {weight: 300, alias: 'Reels Korean Light', names: ['Malgun Gothic Semilight', 'MalgunGothic-Semilight']},
  {weight: 400, alias: 'Reels Korean Regular', names: ['Malgun Gothic', 'MalgunGothic']},
  {weight: 700, alias: 'Reels Korean Bold', names: ['Malgun Gothic Bold', 'MalgunGothic-Bold']},
];

export function LocalFontLoader({fonts, children}: {fonts: LocalFont[]; children: ReactNode}) {
  const key = JSON.stringify(fonts);
  const [loaded, setLoaded] = useState<{key: string; aliases: FontAliases; handle: number} | null>(null);
  const {delayRender, continueRender} = useDelayRender();

  useEffect(() => {
    let cancelled = false;
    const handle = delayRender('Loading Korean font faces');
    const configured: LocalFont[] = JSON.parse(key);
    const aliases: FontAliases = {};
    const tasks = configured.map(async ({family, file, weight}) => {
      try {
        await loadFace(family, `url(${JSON.stringify(staticFile(file))})`, weight);
      } catch (error) {
        console.warn(`Could not load font ${family} from ${file}`, error);
      }
    });
    const systemTasks = systemCandidates.map(async ({weight, alias, names}) => {
      try {
        await loadFace(alias, names.map((name) => `local(${JSON.stringify(name)})`).join(', '), '100 1000');
        (aliases['Malgun Gothic'] ??= {})[weight] = alias;
      } catch {
        // A different platform can resolve its own Korean system fallback.
      }
    });
    void Promise.all([...tasks, ...systemTasks]).then(() => {
      if (!cancelled) setLoaded({key, aliases, handle});
    });
    return () => {
      cancelled = true;
      continueRender(handle);
    };
  }, [key, delayRender, continueRender]);

  useLayoutEffect(() => {
    if (loaded?.key === key) continueRender(loaded.handle);
  }, [loaded, key, continueRender]);

  return <FontContext.Provider value={loaded?.key === key ? loaded.aliases : null}>{children}</FontContext.Provider>;
}

export function useLocalFontAliases() {
  return useContext(FontContext);
}
