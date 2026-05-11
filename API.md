# API Deployment Notes

The app now has the same public read/calculation API shape in two runtimes:

- Netlify: `/api/*` is routed to `netlify/functions/api.js`.
- Local server: `python web_app.py` serves the same `/api/*` paths from SQLite.

Netlify is read-only. Admin writes still require the local Python server because
they update `nhi_drug_coverage.db`.

## Public Endpoints

```http
GET  /api/health
GET  /api/config
GET  /api/stats
GET  /api/drugs?category=oncology_breast
GET  /api/drug/:id
GET  /api/formulations?drug=trastuzumab
POST /api/calculate/risk-scores
POST /api/calculate/staging-score
```

Example calculation request:

```bash
curl -X POST https://your-site.netlify.app/api/calculate/staging-score \
  -H "content-type: application/json" \
  -d "{\"age\":55,\"size_mm\":20,\"grade\":2,\"nodes_pos\":0,\"cT\":\"T2\",\"cN\":\"N0\",\"cM\":\"M0\",\"er_hscore\":270,\"pr_hscore\":200,\"her2\":\"-\",\"ki67\":15}"
```

## Refreshing Netlify API Data

After changing the SQLite database locally, refresh the static Netlify payloads:

```bash
python api_export.py
git add data/api
git commit -m "Update API data export"
git push origin master
```

## PWA

The deployed frontend includes:

- `manifest.webmanifest`
- `sw.js`
- `offline.html`
- PNG icons under `icons/`

The service worker uses network-first for `/api/*` and cached shell fallback for
the app UI.
