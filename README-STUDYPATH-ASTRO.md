# StudyPath Astro rebuild

This branch introduces a maintainable Astro + TypeScript static-site foundation while retaining the original catalogue JSON files and legacy site files.

## Included
- Astro static output configured for GitHub Pages project path.
- Tailwind CSS and centralized global styles.
- Bachelor/Master selector and local client-side catalogue search.
- Local shortlist, document checklist, application planner and cost estimate.
- English/Bengali interface toggle for key homepage copy.
- Light/dark preference.
- Privacy, Terms, Disclaimer and Contact pages.
- GitHub Pages Actions workflow.
- Existing catalogue JSON copied into `public/data` before build.

## Run locally (Windows PowerShell)
```powershell
npm install
npm run dev
npm run build
npm run preview
```

The legacy root `index.html`, existing catalogue files, DAAD refresh script and backups have not been deleted or overwritten. See `CONTENT-MANAGEMENT-GUIDE.md` for data editing notes.
