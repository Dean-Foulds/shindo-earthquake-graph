// IBM Plex Mono carries no CJK glyphs, so without an explicit Japanese face after
// it the browser picks an arbitrary per-glyph fallback and the JA locale renders
// in a mix of typefaces. Every inline fontFamily in the app uses this stack.
export const MONO =
  "'IBM Plex Mono','Hiragino Kaku Gothic ProN','Noto Sans JP','Yu Gothic',monospace"
