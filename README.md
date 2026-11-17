# StudyPath — Global Study Abroad Information Platform

**Live:** https://mdmominul-islam.github.io/scholarship-tracker/  
**Repository:** https://github.com/mdmominul-islam/scholarship-tracker

StudyPath is a free English/Bengali static information and planning platform for students in Bangladesh and international applicants.

## Features
- Combined Bachelor, Master and other programme search.
- Country, university, course and scholarship/funding-reference directories.
- Degree, country and subject filters; sorting and CSV export.
- Local shortlist and up-to-four programme comparison.
- Preliminary programme matching (not an admissions decision).
- Local document checklist, application tracker, deadline planner and study cost calculator.
- JSON backup/restore for local non-sensitive planning data.
- Light/dark theme, key bilingual interface labels, responsive mobile navigation.
- Study-abroad guides, FAQ, email-draft feedback, Privacy, Terms, Disclaimer and Copyright pages.

## Free technology
Astro, TypeScript, Tailwind CSS, static JSON catalogues, browser localStorage, GitHub Pages and GitHub Actions. No paid APIs, backend, paid hosting, authentication service, database subscription or secret API keys.

## Data provenance and accuracy
The catalogue combines the preserved Master's records embedded in the original root `index.html`, curated `global-bachelor-programmes.json`, and the DAAD International Programmes catalogue in `daad-programmes.json` when available. Build scripts normalise these sources and derive country, university, course and funding-reference directories. Some records need verification. Funding references do not mean an award is currently open. Always check official provider sources for fees, deadlines, eligibility, current availability and award coverage. The DAAD catalogue is not a complete inventory of every German degree programme.

## Main folders
- `src/pages/`: homepage, directory, resources and legal pages.
- `src/layouts/`: shared layout.
- `src/styles/global.css`: theme and responsive design.
- `src/config/site.ts`: brand, URL and contact configuration.
- `src/locales/`: English and Bengali UI dictionaries.
- `public/data/`: generated data files.
- `scripts/prepare-data.mjs`: preserved catalogue extraction and normalisation.
- `scripts/validate-data.mjs`: data validation.
- `.github/workflows/deploy.yml`: GitHub Pages deployment.
- `index.html`: preserved original website and legacy Master's CSV source.

## Requirements
Node.js 22+ and npm.

## Run locally (Windows PowerShell)
```powershell
npm install
npm run dev
```
Open the local URL printed by Astro (normally `http://localhost:4321`).

## Build and preview
```powershell
npm run build
npm run preview
```
The build prepares and validates the JSON catalogues before generating static files in `dist/`.

## GitHub Pages deployment
1. Push the code to this public repository.
2. In GitHub → Settings → Pages, choose **GitHub Actions** as the source.
3. Review and merge the StudyPath Astro Pull Request into `main`.
4. Check the Actions tab for a successful Pages deployment.
5. Visit the Live URL above.

Astro is configured with the project base path `/scholarship-tracker/`. Keep this base path unless the hosting URL changes.

## Change brand, contact, URL or colours
- Brand/email/public URL: `src/config/site.ts`.
- GitHub Pages site/base: `astro.config.mjs`.
- Main and dark colour variables: `src/styles/global.css`.

## Add or update programmes
- Curated Bachelor records: `global-bachelor-programmes.json`.
- DAAD records: existing `scripts/refresh_daad_catalogue.py` and scheduled workflow.
- Legacy Master's CSV remains in root `index.html` and is extracted during build.
Use stable unique IDs, official source URLs and clear verification notes. Never guess fees, deadlines, eligibility or scholarships. Run `npm run build` before publishing.

## Privacy and limitations
There are no user accounts, secure backend, cloud sync, document uploads or background notifications. Shortlists, notes, checklists, application plans and events are saved only in the current browser. Do not enter passport numbers, bank information, passwords, private documents or sensitive personal data. Feedback opens a `mailto:` draft; the site does not send it itself. Eligibility matching is informational only and cost calculations are estimates based on user-entered values.

See `CONTENT-MANAGEMENT-GUIDE.md` and `PRIVACY-AND-DISCLAIMER-NOTES.md` for detailed guidance.
