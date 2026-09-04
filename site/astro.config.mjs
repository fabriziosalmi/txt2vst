import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Custom domain txt2vst.com is active (see public/CNAME),
// so base is always '/' — no subpath needed.
export default defineConfig({
  site: 'https://www.txt2vst.com',
  output: 'static',
  integrations: [sitemap()],
});
