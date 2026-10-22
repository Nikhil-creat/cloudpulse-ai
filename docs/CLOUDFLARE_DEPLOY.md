# Deploy to Cloudflare Pages (free, no card)

Static site plus the secured AI proxy (`site/functions/api/llm.js`). Keys live in Cloudflare secrets.

1. dash.cloudflare.com → sign up (free) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git** → pick `cloudpulse-ai`.
2. Build settings:
   - Framework preset: **None**
   - Build command: leave empty
   - Build output directory: `/` (use `.` if it complains)
   - Root directory (advanced): `site`
3. Environment variables (advanced): add `GROQ_API_KEY` and `GEMINI_API_KEY`, choose **Encrypt** for both.
   Optional: `DAILY_CAP`, `RATE_PER_MIN`, `RATE_PER_DAY`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`.
4. **Save and Deploy**. Open `https://<project>.pages.dev/api/health` and look for `"llm": true`.
5. If you add the keys after the first deploy: Settings → Variables and Secrets, then redeploy.

Free limits: unlimited static bandwidth, 100,000 function requests per day. Security headers come from `site/_headers`.
