import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://mdmominul-islam.github.io',
  base: '/scholarship-tracker',
  output: 'static',
  integrations: [tailwind()],
  build: { format: 'directory' }
});