// forked from design-sync lib/css.mjs — copyTokens supports a package-relative
// tokensGlob with NO tokens npm package (Beacon ships tokens as plain CSS in
// src/styles/tokens/, not as a dependency). Only copyTokens differs; every other
// export is verbatim. Relative import of ./common.mjs is repointed at the staged lib.

import { cpSync, existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { ls } from '../../.ds-sync/lib/common.mjs';

// Parse @font-face blocks from `cssPath` → resolve url() paths relative to
// `srcDir` → copy .woff2/.woff/.ttf/.otf to fonts/ → return rewritten rules.
export function extractFonts(cssPath, srcDir, { fontsOut, roots }) {
  const realOf = (p) => { try { return realpathSync(p); } catch { return null; } };
  const rootsReal = (Array.isArray(roots) ? roots : [roots]).map((r) => realOf(resolve(r)) ?? resolve(r));
  const insideRoots = (p) => rootsReal.some((root) => {
    const rel = relative(root, p);
    return rel !== '' && !rel.startsWith('..') && !isAbsolute(rel);
  });
  if (!existsSync(cssPath)) return [];
  const css = readFileSync(cssPath, 'utf8');
  const rules = [];
  for (const m of css.matchAll(/@font-face\s*\{([^}]+)\}/g)) {
    const body = m[1];
    const fam = body.match(/font-family\s*:\s*['"]?([^;'"\n]+)['"]?/)?.[1]?.trim();
    const urls = [...body.matchAll(/url\(\s*['"]?([^'")]+?\.(?:woff2?|ttf|otf))['"]?\s*\)/gi)].map((u) => u[1]);
    if (!fam || !urls.length) continue;
    let rewritten = body;
    for (const u of urls) {
      if (/^(https?:|data:)/.test(u)) continue; // CDN / inline — leave as-is
      const src = resolve(srcDir, u.replace(/^\.\//, ''));
      const real = realOf(src);
      if (!real || !insideRoots(real)) continue;
      const name = basename(src);
      mkdirSync(fontsOut, { recursive: true });
      cpSync(real, join(fontsOut, name));
      rewritten = rewritten.split(u).join(`./${name}`);
    }
    rules.push(`@font-face{${rewritten}}`);
  }
  return rules;
}

// Copy token CSS verbatim into OUT/tokens/. tokensGlob supports a single trailing
// `**` segment for deep recursion.
//
// FORK: when tokensPkg is set, base = node_modules/<tokensPkg> (upstream behavior).
// When it is unset but tokensGlob is provided, base = the package dir
// (dirname(nodeModules)) — so a plain-CSS DS that keeps tokens in src/ is supported
// without faking an npm package. Verbatim copy means no rot: the real source files
// are re-read every build.
export function copyTokens({ tokensPkg, tokensGlob, nodeModules, out }) {
  const tokenFiles = [];
  if (!tokensPkg && !tokensGlob) return tokenFiles;
  const baseDir = tokensPkg ? join(nodeModules, tokensPkg) : dirname(nodeModules);
  const version = tokensPkg
    ? JSON.parse(readFileSync(join(baseDir, 'package.json'), 'utf8')).version
    : 'src';
  if (tokensGlob) {
    const parts = tokensGlob.split('/');
    const pat = parts.pop();
    const rx = new RegExp('^' + pat.replace(/\./g, '\\.').replace(/\*/g, '.*') + '$');
    const deep = parts.includes('**');
    const base = join(baseDir, ...parts.filter((p) => p !== '**'));
    (function collect(d, rel = '') {
      if (!existsSync(d)) return;
      for (const e of ls(d, { withFileTypes: true })) {
        const r = rel ? `${rel}/${e.name}` : e.name;
        if (e.isDirectory() && deep) collect(join(d, e.name), r);
        else if (e.isFile() && rx.test(e.name)) {
          // Preserve subdir structure so @import './sub/x.css' inside a
          // copied file keeps resolving.
          mkdirSync(dirname(join(out, 'tokens', r)), { recursive: true });
          cpSync(join(d, e.name), join(out, 'tokens', r));
          tokenFiles.push(r);
        }
      }
    })(base);
  } else {
    for (const sub of ['dist/css', 'css', 'dist', '.']) {
      const d = join(baseDir, sub);
      if (!existsSync(d)) continue;
      for (const f of ls(d)) {
        if (f.endsWith('.css')) {
          cpSync(join(d, f), join(out, 'tokens', f));
          tokenFiles.push(f);
        }
      }
      if (tokenFiles.length) break;
    }
  }
  console.error(`  tokens: ${tokenFiles.length} files from ${tokensPkg ?? dirname(nodeModules)}@${version}`);
  return tokenFiles;
}

// _ds_bundle.css enters the styles.css closure; rewrite package-relative url()s in
// its @font-face blocks to the fonts/ copies (or drop dead ones).
export function rewriteBundleFontFaces({ out, bundleCss }) {
  const p = bundleCss ?? join(out, '_ds_bundle.css');
  let css;
  try { css = readFileSync(p, 'utf8'); } catch { return; }
  if (!/@font-face/i.test(css)) return;
  let dropped = 0, rewrote = 0;
  const next = css.replace(/@font-face\s*\{[^}]*\}/gi, (block) => {
    let b = block;
    for (const m of block.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/gi)) {
      const u = m[1];
      if (/^(?:https?:|data:|\.\/fonts\/)/.test(u)) continue;
      const name = basename(u.split(/[?#]/)[0]);
      if (existsSync(join(out, 'fonts', name))) { b = b.split(u).join(`./fonts/${name}`); rewrote++; }
    }
    if (/url\(\s*['"]?(?!https?:|data:|\.\/fonts\/)/i.test(b)) { dropped++; return '/* @ds-font-face-dropped: unresolvable src */'; }
    return b;
  });
  if (rewrote || dropped) {
    writeFileSync(p, next);
    console.error(`  _ds_bundle.css fonts: ${rewrote} url(s) rewritten to fonts/${dropped ? `, ${dropped} dead @font-face block(s) dropped` : ''}`);
  }
}

// styles.css — the styles entry point (an @import list). Rendered designs consume
// ONLY this file's transitive @import closure plus the JS bundle.
export function writeStylesCss({ out, tokenFiles, bundleCss, fontRules, remoteImports }) {
  let hasBundleCss = false;
  try {
    const css = readFileSync(bundleCss ?? join(out, '_ds_bundle.css'), 'utf8');
    hasBundleCss = css.trim().length > 0 && !css.startsWith('/* @ds-css-runtime');
  } catch { /* absent */ }
  const styleImports = [
    ...tokenFiles.map((f) => `@import "./tokens/${f}";`),
    ...(fontRules.length ? ['@import "./fonts/fonts.css";'] : []),
    ...remoteImports.map((u) => `@import url("${u}");`),
    ...(hasBundleCss ? ['@import "./_ds_bundle.css";'] : []),
  ];
  if (styleImports.length) {
    writeFileSync(join(out, 'styles.css'), styleImports.join('\n') + '\n');
    console.error(`  styles.css: ${styleImports.length} @import(s)${hasBundleCss ? ' (incl. _ds_bundle.css — component styles ship to designs via this closure)' : ''}`);
    return;
  }
  writeFileSync(
    join(out, 'styles.css'),
    '/* @ds-styles: runtime — this design system injects its styles at runtime (CSS-in-JS); no static stylesheet to import. */\n',
  );
  console.error('[CSS_RUNTIME] no static CSS found (tokens/component/fonts/remote all empty) — wrote a self-styling styles.css. Expected for CSS-in-JS DSes; if this DS does ship a stylesheet, set cfg.cssEntry to it. If cfg.cssEntry is ALREADY set and renders verify, this line refers only to the scrape — do not chase it.');
}
