# Deploy to Vercel (live in about 5 minutes)

Vercel hosts everything in `site/`: the static page plus two serverless functions in `site/api/` (`/api/llm`, `/api/health`). Set **Root Directory to `site`** so Vercel ignores the Docker backend and frontend folders. Your Groq and Gemini keys live in Vercel environment variables and never reach the browser. The Python backend (FastAPI, Celery, databases) is not deployed here; run it with Docker.

## Steps
1. vercel.com → Sign up → **Continue with GitHub**.
2. **Add New → Project** → import `Nikhil-creat/cloudpulse-ai`.
3. Configure:
   - Root Directory: tap **Edit**, choose **`site`**, Continue
   - Framework Preset: **Other**
   - Leave Build and Output settings alone (`site/vercel.json` sets them).
4. Environment Variables (add before deploying):
   - `GROQ_API_KEY` = your key from console.groq.com/keys
   - `GEMINI_API_KEY` = your key from aistudio.google.com/apikey
   - Optional: `DAILY_CAP` (default 800 requests per day), `RATE_PER_MIN` (10), `RATE_PER_DAY` (100)
   - Optional but recommended: `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` (free Upstash database) so rate limits are shared across instances
5. **Deploy**. Open `https://<project>.vercel.app/api/health`. You should see `"llm": true`.
6. Open the site, scroll to Assistant. It now works without pasting a key.

## After deploying
- Project → Settings → Domains to add a custom domain.
- Project → Analytics → Enable (privacy-friendly page views; the site already loads the script).
- Update `canonical`, `og:url`, `og:image` in `site/index.html` and `sitemap.xml`/`robots.txt` to your Vercel URL, then push.
- Every `git push` to `main` redeploys automatically. Pull requests get preview URLs.

## Security notes
- Strict CSP (`script-src 'self'`), HSTS, COOP/CORP and frame blocking are set in `vercel.json`.
- `/api/llm` rejects cross-site requests, enforces the system prompt on the server, screens prompt injection, redacts secrets in and out, and caps usage per IP and per day.
- Set a spending limit in the Groq and Google dashboards as a second safety net.
- Hobby plan is for personal, non-commercial use.
