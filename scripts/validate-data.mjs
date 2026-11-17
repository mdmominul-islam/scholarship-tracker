import { readFile } from 'node:fs/promises';
const files=['programme-catalogue.json','countries.json','universities.json','scholarships.json','legacy-masters.json','global-bachelor-programmes.json'];
let errors=0;
for(const file of files){
 try{
  const data=JSON.parse(await readFile(new URL('../public/data/'+file,import.meta.url),'utf8'));
  const rows=Array.isArray(data)?data:data.programmes||data.countries||data.universities||data.scholarships||[];
  if(!Array.isArray(rows))throw new Error('Expected a data array');
  const ids=new Set();
  for(const [i,row] of rows.entries()){
   if(file==='countries.json'){if(!row.name)throw new Error('Country '+(i+1)+' missing name');continue;}
   if(file==='universities.json'){if(!row.name||!row.country)throw new Error('University '+(i+1)+' missing name or country');continue;}
   if(file==='scholarships.json'){if(!row.name||!row.provider)throw new Error('Funding record '+(i+1)+' missing name or provider');continue;}
   for(const key of ['degreeType','country','university','programme'])if(!String(row[key]??'').trim())throw new Error('Row '+(i+1)+' missing '+key);
   if(row.id&&ids.has(row.id))throw new Error('Duplicate ID '+row.id);if(row.id)ids.add(row.id);
   for(const key of ['sourceUrl','detailUrl','daadUrl','officialUniversityUrl'])if(row[key]&&!/^https?:\/\//i.test(row[key]))throw new Error('Invalid '+key+' in row '+(i+1));
  }
  console.log('✓ '+file+': '+rows.length+' records');
 }catch(e){errors++;console.error('✗ '+file+': '+e.message)}
}
if(errors)process.exitCode=1;
