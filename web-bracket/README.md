# Web Bracket App (No Streamlit)

This is a zero-build bracket app using plain HTML/CSS/JS.

## Run

From repo root:

```bash
python -m http.server 8000
```

Then open:

`http://localhost:8000/web-bracket/`

## Share With Friends (GitHub Pages)

1. Push this repo to GitHub.
2. Make sure your default branch is `main` (or update the workflow branch).
3. In GitHub: `Settings -> Pages`, set `Source` to `GitHub Actions`.
4. Push changes under `web-bracket/` to `main`.
5. GitHub Actions will deploy automatically using:
   - `.github/workflows/deploy-web-bracket-pages.yml`
6. Share your Pages URL (shown in the Actions run / Pages settings).

## Rebuild Data

If `submission_2025.csv` or source CSVs change:

```bash
python web-bracket/build_bracket_data.py
```

This generates:

- `web-bracket/bracket_data_2025.json`

## Notes

- Men/Women tabs
- 64-team field (play-ins resolved from model probabilities)
- Picks through Championship (`R6CH`)
- Regions `X` and `Z` render right-to-left
- Hover team buttons for full text tooltip
