import { mkdir, copyFile, access } from 'node:fs/promises';
import { constants } from 'node:fs';

const sourceFiles = ['daad-programmes.json', 'global-bachelor-programmes.json'];
await mkdir('public/data', { recursive: true });
for (const file of sourceFiles) {
  try {
    await access(file, constants.R_OK);
    await copyFile(file, `public/data/${file}`);
    console.log(`Prepared public/data/${file}`);
  } catch {
    console.warn(`Optional catalogue not found: ${file}`);
  }
}