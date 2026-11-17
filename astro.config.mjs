import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://mdmominul-islam.github.io',
  base: '/scholarship-tracker',
  output: 'static',
  vite: {
    plugins: [tailwindcss()]
  },
  build: { format: 'directory' }
});