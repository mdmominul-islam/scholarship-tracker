import { mkdir, copyFile, readFile, writeFile, access } from 'node:fs/promises';
import { constants } from 'node:fs';

const sourceFiles = ['daad-programmes.json', 'global-bachelor-programmes.json'];
const root = process.cwd();
const out = new URL('../public/data/', import.meta.url);
await mkdir(out, { recursive: true });

function parseCsv(text) {
  const rows = []; let row = []; let field = ''; let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n') { row.push(field.replace(/\r$/, '')); if (row.some(v => v.trim())) rows.push(row); row = []; field = ''; }
    else field += ch;
  }
  row.push(field.replace(/\r$/, ''));
  if (row.some(v => v.trim())) rows.push(row);
  return rows;
}

function websiteUrl(value) {
  const v = String(value || '').trim();
  if (!v || /^(check|not available|n\/a|none)/i.test(v)) return '';
  if (/^https?:\/\//i.test(v)) return v;
  if (/^[a-z0-9.-]+\.[a-z]{2,}(\/.*)?$/i.test(v)) return 'https://' + v;
  return '';
}

const legacyHtml = await readFile('index.html', 'utf8');
const match = legacyHtml.match(/const CSV = \x60([\s\S]*?)\x60;/);
if (!match) throw new Error('Could not find the legacy programme CSV in index.html; refusing to build without the preserved Master catalogue.');
const parsed = parseCsv(match[1]);
const headers = (parsed.shift() || []).map(x => x.trim());
const legacy = parsed.map((values, index) => {
  const row = Object.fromEntries(headers.map((h, i) => [h, values[i] ?? '']));
  const website = websiteUrl(row.Website);
  return {
    id: 'legacy-master-' + String(row.No || index + 1),
    degreeType: 'Master',
    country: row.Country || 'Not confirmed',
    city: row.City || 'Not confirmed',
    university: row.University || 'Not confirmed',
    programme: row.Programme || 'Not confirmed',
    subject: row.Field || 'Not confirmed',
    language: row.Language || 'Not confirmed',
    duration: row.Duration || 'Not confirmed',
    tuition: row['Tuition (non-EU/yr)'] || 'Not confirmed',
    livingCostMonthlyEUR: row['Living cost (EUR/mo)'] || '',
    funding: row['Funding scheme(s)'] || 'Not confirmed',
    fundLevel: row['Funding level'] || 'Not confirmed',
    deadline: row['Intake and deadline'] || 'Not confirmed',
    sourceUrl: website,
    source: 'Preserved legacy StudyPath catalogue',
    publicationStatus: 'Needs verification',
    lastVerified: '',
    lastUpdated: '2026-11-18',
    note: row.Notes || 'Legacy catalogue record. Verify all admission, tuition, funding and deadline information with the official institution.',
    legacyStatus: row['My status'] || 'Not started',
    priority: row.Priority || 'Not confirmed',
    entryCycle: row['Entry cycle'] || 'Not confirmed'
  };
}).filter(r => r.university !== 'Not confirmed' && r.programme !== 'Not confirmed');

const payload = {
  generatedAt: new Date().toISOString(),
  source: 'Preserved from the existing StudyPath index.html CSV',
  count: legacy.length,
  publicationStatus: 'Needs verification; historical entries are not presented as confirmed current offers',
  programmes: legacy
};
await writeFile(new URL('legacy-masters.json', out), JSON.stringify(payload, null, 2) + '\n', 'utf8');
console.log(`Extracted ${legacy.length} preserved legacy Master's records.`);

for (const file of sourceFiles) {
  try {
    await access(file, constants.R_OK);
    await copyFile(file, new URL(file, out));
    console.log(`Prepared public/data/${file}`);
  } catch {
    if (file === 'global-bachelor-programmes.json') throw new Error(`Required catalogue missing: ${file}`);
    console.warn(`Optional catalogue not found: ${file}`);
  }
}
