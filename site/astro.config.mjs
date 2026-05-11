import { defineConfig } from 'astro/config';

// Custom domain txt2vst.com is active (see public/CNAME),
// so base is always '/' — no subpath needed.
export default defineConfig({
  site: 'https://txt2vst.com',
  output: 'static',
});
