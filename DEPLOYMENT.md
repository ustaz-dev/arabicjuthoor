# Deployment guide

## Going live on `arabicjuthoor.com`

Three steps. About 15 minutes total once the domain is in your Cloudflare account.

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/<your-username>/arabicjuthoor.git
git push -u origin main
```

The `.github/workflows/deploy.yml` workflow will fire automatically and deploy the site to GitHub Pages.

### 2. Enable GitHub Pages

In the repo on GitHub:

1. **Settings → Pages**
2. **Source:** *GitHub Actions* (not "Deploy from a branch")
3. The deployment runs and produces a URL like `https://<username>.github.io/arabicjuthoor/`. Confirm it loads correctly.

### 3. Point `arabicjuthoor.com` at GitHub Pages

The `CNAME` file in this repo already contains `arabicjuthoor.com`, so GitHub will accept the custom domain. You just need DNS records:

In **Cloudflare → arabicjuthoor.com → DNS** add four `A` records and one `CNAME`:

| Type | Name | Content | Proxy status |
|---|---|---|---|
| A | @ | 185.199.108.153 | DNS only (grey cloud) |
| A | @ | 185.199.109.153 | DNS only |
| A | @ | 185.199.110.153 | DNS only |
| A | @ | 185.199.111.153 | DNS only |
| CNAME | www | `<username>.github.io` | DNS only |

Then in **GitHub → Settings → Pages**:
- Custom domain: `arabicjuthoor.com`
- Wait 5–10 minutes for DNS to propagate, then tick **Enforce HTTPS**.

Cloudflare will handle the SSL automatically.

---

## What's in the deployment package

| File | Purpose |
|---|---|
| `index.html` | The dashboard — entry point at `arabicjuthoor.com/` |
| `CNAME` | Tells GitHub Pages the custom domain |
| `robots.txt` | Allows crawlers, points at sitemap, excludes `Data raw/` |
| `sitemap.xml` | Lists all indexable URLs for Google / Bing |
| `favicon.svg` | Browser-tab icon (the letter ج on the brand gradient) |
| `og-image.svg` | Social-sharing card (1200×630, used by Facebook, LinkedIn, Twitter, WhatsApp, Slack previews) |
| `.nojekyll` | Tells GitHub Pages to serve files as-is, no Jekyll processing |
| `.github/workflows/deploy.yml` | Auto-deploys on every push to `main` |

---

## Recommended next moves after going live

### Submit to Google + Bing

1. **Google Search Console** — <https://search.google.com/search-console>
   - Add `https://arabicjuthoor.com/` as a property
   - Verify via DNS TXT record (Cloudflare makes this trivial)
   - **Sitemaps → Add a new sitemap → `sitemap.xml`** → Submit

2. **Bing Webmaster Tools** — <https://www.bing.com/webmasters>
   - Same process; Bing also feeds DuckDuckGo and Yahoo
   - Submit `sitemap.xml`

3. **Google Scholar** — if you want academic indexing:
   - Add a `<meta name="citation_*" >` tag set to scholarly pages
   - This dashboard isn't formatted as a paper, but the position paper (`02-architecture/our-contributions-and-roadmap.md`) could be reformatted as one for Scholar indexing later

### Convert the OG image to PNG (optional but recommended)

Most social scrapers handle SVG fine in 2026, but a few older ones (especially older WhatsApp clients) still prefer PNG. Easiest paths:

- **Online:** drop `og-image.svg` into <https://svgtopng.com/> or <https://cloudconvert.com/svg-to-png>. Set output to 1200×630. Save as `og-image.png` in the repo root. Then change the meta tags in `index.html` from `og-image.svg` to `og-image.png`.
- **Local:** `pip install cairosvg` then `cairosvg og-image.svg -o og-image.png -W 1200 -H 630`

### Optional: convert key .md files to .html

GitHub Pages with `.nojekyll` serves Markdown files as plain text. Researchers can read them (browsers display them, GitHub renders them) but they don't look polished. Two options:

1. **Leave as-is.** Researchers want the raw markdown; this is fine.
2. **Add a markdown renderer.** Inject a small client-side script (e.g. <https://marked.js.org/>) on a wrapper page that fetches and renders any `.md`. Roughly 30 lines of JS. Ask for this if you want it.

---

## Verifying everything is wired correctly

Once the domain is live, test these in order:

1. <https://arabicjuthoor.com/> loads the dashboard ✓
2. <https://arabicjuthoor.com/robots.txt> shows the robots file ✓
3. <https://arabicjuthoor.com/sitemap.xml> shows the sitemap XML ✓
4. <https://arabicjuthoor.com/favicon.svg> shows the ج icon ✓
5. Paste your URL into <https://www.opengraph.xyz/> — the social card preview should show the OG image and proper title
6. <https://search.google.com/test/rich-results?url=https%3A%2F%2Farabicjuthoor.com%2F> validates the structured data
7. <https://pagespeed.web.dev/?url=https%3A%2F%2Farabicjuthoor.com%2F> reports performance

A clean PageSpeed score of 95+ is the target. Current setup should easily hit that.
