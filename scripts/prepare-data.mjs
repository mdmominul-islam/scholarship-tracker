import { mkdir, copyFile, readFile, writeFile, access } from 'node:fs/promises';
import { constants } from 'node:fs';

const outputDir = new URL('../public/data/', import.meta.url);
await mkdir(outputDir, { recursive: true });

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
function rowsOf(payload) {
  return Array.isArray(payload) ? payload : payload?.programmes || payload?.items || payload?.results || [];
}
async function readJson(path) {
  try { return JSON.parse(await readFile(path, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}
async function writeJson(name, payload) {
  await writeFile(new URL(name, outputDir), JSON.stringify(payload, null, 2) + '\n', 'utf8');
}

const legacyHtml = await readFile('index.html', 'utf8');
const match = legacyHtml.match(/const CSV = \x60([\s\S]*?)\x60;/);
if (!match) throw new Error('Could not find the legacy programme CSV in index.html; refusing to build without the preserved Master catalogue.');
const parsed = parseCsv(match[1]);
const headers = (parsed.shift() || []).map(x => x.trim());
const legacy = parsed.map((values, index) => {
  const row = Object.fromEntries(headers.map((h, i) => [h, values[i] ?? '']));
  return {
    id: 'legacy-master-' + String(row.No || index + 1), degreeType: 'Master',
    country: row.Country || 'Not confirmed', city: row.City || 'Not confirmed',
    university: row.University || 'Not confirmed', programme: row.Programme || 'Not confirmed',
    subject: row.Field || 'Not confirmed', language: row.Language || 'Not confirmed',
    duration: row.Duration || 'Not confirmed', tuition: row['Tuition (non-EU/yr)'] || 'Not confirmed',
    livingCostMonthlyEUR: row['Living cost (EUR/mo)'] || '',
    funding: row['Funding scheme(s)'] || 'Not confirmed', fundLevel: row['Funding level'] || 'Not confirmed',
    deadline: row['Intake and deadline'] || 'Not confirmed', sourceUrl: websiteUrl(row.Website),
    source: 'Preserved legacy StudyPath catalogue', publicationStatus: 'Needs verification',
    lastVerified: '', lastUpdated: '2026-11-18',
    note: row.Notes || 'Legacy catalogue record. Verify all admission, tuition, funding and deadline information with the official institution.',
    legacyStatus: row['My status'] || 'Not started', priority: row.Priority || 'Not confirmed',
    entryCycle: row['Entry cycle'] || 'Not confirmed'
  };
}).filter(r => r.university !== 'Not confirmed' && r.programme !== 'Not confirmed');
await writeJson('legacy-masters.json', { generatedAt: new Date().toISOString(), source: 'Preserved from the existing StudyPath index.html CSV', count: legacy.length, publicationStatus: 'Needs verification; historical entries are not presented as confirmed current offers', programmes: legacy });
console.log('Preserved legacy Masters records:', legacy.length);

const bachelor = await readJson('global-bachelor-programmes.json');
const daad = await readJson('daad-programmes.json');
if (!bachelor) throw new Error('global-bachelor-programmes.json is missing.');
await copyFile('global-bachelor-programmes.json', new URL('global-bachelor-programmes.json', outputDir));
try { await access('daad-programmes.json', constants.R_OK); await copyFile('daad-programmes.json', new URL('daad-programmes.json', outputDir)); }
catch { console.warn('DAAD catalogue not found; the rest of the catalogue will still build.'); }

const raw = [...rowsOf(bachelor), ...legacy, ...rowsOf(daad)];
const normalized = raw.map((r, i) => {
  const degree = String(r.degreeType || r.degree || '').toLowerCase();
  return {
    ...r,
    id: String(r.id || 'catalogue-' + (i + 1)),
    degreeType: degree.includes('bachelor') ? 'Bachelor' : degree.includes('master') ? 'Master' : degree.includes('phd') || degree.includes('doctor') ? 'PhD' : (r.degreeType || 'Other'),
    country: r.country || 'Not confirmed', city: r.city || 'Not confirmed',
    university: r.university || r.institution || 'Not confirmed',
    programme: r.programme || r.courseName || r.name || 'Not confirmed',
    subject: r.subject || r.field || 'Not confirmed',
    language: r.language || r.teachingLanguage || 'Not confirmed',
    duration: r.duration || 'Not confirmed', tuition: r.tuition || 'Not confirmed',
    funding: r.funding || r.fundText || 'Not confirmed',
    deadline: r.deadline || 'Not confirmed',
    sourceUrl: websiteUrl(r.sourceUrl || r.officialUniversityUrl || r.detailUrl || r.daadUrl),
    source: r.source || (r.detailUrl || r.daadUrl ? 'DAAD International Programmes catalogue' : 'Catalogue record'),
    publicationStatus: r.publicationStatus || (r.detailStatus === 'Fetched' ? 'Source detail fetched; verify at institution' : 'Needs verification'),
    lastVerified: r.lastVerified || '', lastUpdated: r.lastUpdated || r.generatedAt || ''
  };
}).filter(r => r.university !== 'Not confirmed' && r.programme !== 'Not confirmed');
const unique = new Map();
for (const row of normalized) {
  const key = [row.degreeType,row.country,row.university,row.programme].join('|').toLowerCase();
  if (!unique.has(key)) unique.set(key, row);
}
const programmes = [...unique.values()];
await writeJson('programme-catalogue.json', { generatedAt: new Date().toISOString(), count: programmes.length, sources: ['DAAD International Programmes public catalogue', 'Existing StudyPath Master catalogue', 'Curated international Bachelor catalogue'], note: 'Record-level source and verification notes must be checked before application.', programmes });
await writeJson('courses.json', { generatedAt: new Date().toISOString(), count: programmes.length, courses: programmes });

const countryMap = new Map();
const universityMap = new Map();
const scholarshipMap = new Map();
for (const p of programmes) {
  if (!countryMap.has(p.country)) countryMap.set(p.country, { name:p.country, programmeCount:0, degrees:new Set(), sourceUrls:new Set() });
  const c = countryMap.get(p.country); c.programmeCount++; c.degrees.add(p.degreeType); if(p.sourceUrl)c.sourceUrls.add(p.sourceUrl);
  const ukey = [p.country,p.university].join('|');
  if (!universityMap.has(ukey)) universityMap.set(ukey,{ id:'uni-'+universityMap.size+1, name:p.university, country:p.country, city:p.city, programmeCount:0, degrees:new Set(), subjects:new Set(), officialLinks:new Set(), verification:'Derived from programme listings; verify on institution website.' });
  const u=universityMap.get(ukey); u.programmeCount++; u.degrees.add(p.degreeType); u.subjects.add(p.subject); if(p.sourceUrl)u.officialLinks.add(p.sourceUrl);
  const fund=String(p.funding||'').trim();
  if(fund && !/^(not confirmed|none|no programme-specific award)/i.test(fund)) {
    const skey=[p.country,p.university,p.programme,fund].join('|');
    if(!scholarshipMap.has(skey)) scholarshipMap.set(skey,{id:'sch-'+(scholarshipMap.size+1),name:fund.length>110?fund.slice(0,107)+'…':fund,provider:p.university,country:p.country,university:p.university,degreeType:p.degreeType,programme:p.programme,coverage:p.fundLevel||'Not confirmed',deadline:p.deadline||'Not confirmed',officialUrl:p.sourceUrl||'',source:p.source,publicationStatus:'Needs verification',note:'Funding text is associated with this programme record; confirm award availability, eligibility, coverage and deadline from the official provider.'});
  }
}
const toArray = m => [...m.values()].map(x=>Object.fromEntries(Object.entries(x).map(([k,v])=>[k,v instanceof Set?[...v]:v])));
await writeJson('countries.json',{generatedAt:new Date().toISOString(),count:countryMap.size,countries:toArray(countryMap).sort((a,b)=>a.name.localeCompare(b.name))});
await writeJson('universities.json',{generatedAt:new Date().toISOString(),count:universityMap.size,universities:toArray(universityMap).sort((a,b)=>a.name.localeCompare(b.name))});
await writeJson('scholarships.json',{generatedAt:new Date().toISOString(),count:scholarshipMap.size,scholarships:[...scholarshipMap.values()]});
console.log('Combined programmes:',programmes.length,'Countries:',countryMap.size,'Universities:',universityMap.size,'Funding references:',scholarshipMap.size);
