# StudyPath Content Management Guide

## Data pipeline
Before development and production builds, `scripts/prepare-data.mjs` extracts the preserved legacy Master's CSV from root `index.html`, reads the curated Bachelor's JSON and DAAD JSON if available, normalises programme records, removes exact duplicates, and creates combined programme, country, university and funding-reference files in `public/data/`. The original website and source catalogues remain preserved.

## Add a programme
Edit `global-bachelor-programmes.json` for curated Bachelor records. Provide a unique ID, degree type, country, university, programme, subject, language, duration, tuition, deadline if known, official source URL and verification note. Use `Not confirmed` for unknown facts.

## DAAD catalogue
The existing `scripts/refresh_daad_catalogue.py` retrieves public DAAD International Programmes listings. It is run by the scheduled GitHub Actions workflow or locally with Python 3.12 and the script's dependencies. Do not replace its output with guessed data.

## Country and university directories
These are derived from programme data. Adding a properly sourced programme record updates its country and institution entries during the next build.

## Funding references
Funding entries are derived from programme funding text. Confirm current availability, eligibility, coverage and deadline at the scholarship provider before presenting an award as open.

## Add a guide
Edit `src/pages/resources/index.astro`. Keep general educational guidance separate from legal, visa and institution-specific rules. Cite official sources for factual rules.

## Change settings
Edit `src/config/site.ts` for brand, email and public URL. Edit `astro.config.mjs` for the GitHub Pages site and base path. Edit `src/styles/global.css` for colours. Edit `src/locales/en.json` and `src/locales/bn.json` for interface translations.

## Validate and publish
On Windows PowerShell:
```powershell
npm install
npm run build
```
The build runs data preparation and validation. Resolve reported missing fields, duplicate IDs or invalid source URLs before pushing. Review the GitHub Pull Request and deployment workflow before merging to `main`.

## Privacy
Never add passport numbers, personal documents, bank statements, passwords, medical details or private user records to public JSON. Do not create fake login, upload or admin features. Browser-local planning data is not a secure database.
