import { defineConfig } from 'astro/config';

// When deploying to GitHub Pages at /txt2vst/, set base.
// When using custom domain (txt2vst.com), remove base or set to '/'.
const isGHPages = process.env.GITHUB_ACTIONS === 'true';

export default defineConfig({
  site: isGHPages ? 'https://fabriziosalmi.github.io' : 'https://txt2vst.com',
  base: isGHPages ? '/txt2vst/' : '/',
  output: 'static',
});
