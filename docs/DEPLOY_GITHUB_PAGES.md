# Deploy the site to GitHub Pages

GitHub Pages hosts only the static site in `site/`. The FastAPI backend, workers and databases need Docker (`docker compose up`) on a server or your own machine.

## From Termux on your phone
```bash
pkg update && pkg install git unzip -y
termux-setup-storage
cd ~ && unzip ~/storage/downloads/cloudpulse-ai-master.zip && cd cloudpulse-ai
git init -b main
git config user.name "Nikhil Chary Sriramoju"
git config user.email "sriramojunikhil66@gmail.com"
git add . && git commit -m "feat: CloudPulse AI master release"
git remote add origin https://github.com/Nikhil-creat/cloudpulse-ai.git
git push -u origin main
```
When Git asks for a password, paste a Personal Access Token (GitHub → Settings → Developer settings → Fine-grained tokens, `Contents: read/write`, `Workflows: read/write`, `Pages: read/write` on this repo).

## Turn on Pages
1. Create an empty repo named `cloudpulse-ai` on GitHub first (no README).
2. Repo → Settings → Pages → Build and deployment → Source: **GitHub Actions**.
3. Push to `main`. The workflow in `.github/workflows/pages.yml` publishes `site/`.
4. Your site: `https://nikhil-creat.github.io/cloudpulse-ai/`

## Quick alternative (no Actions)
Settings → Pages → Source: Deploy from a branch → `main` → folder `/ (root)`, then copy `site/index.html` to the repo root as `index.html`.

## About the assistant on the site
The Assistant panel calls Groq and Google directly from the visitor's browser with a key they paste in. The key is kept in `localStorage` on that device only. The page ships a Content-Security-Policy that allows connections only to `api.groq.com` and `generativelanguage.googleapis.com`. Do not hardcode a key in `index.html`: anything in a public repo is public.
