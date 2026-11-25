# Agent Desk (paper trading, live Solana data)

Static dashboard in `public/` plus three small serverless functions in `api/` (Python, standard library only, no API keys).
Paper trading only: nothing here touches a wallet.

## Deploy
1. Push this folder to a GitHub repo.
2. On vercel.com choose **Add New, Project**, import the repo, set Framework Preset to **Other**, then Deploy.

If the `/api` functions are unreachable (for example when you open `public/index.html` directly) the page falls back to the simulation.

## Notes
- Never put a wallet private key in this repo, in the page, or in Vercel env vars for a public site.
- If you add an LLM key later (e.g. Groq), keep it in a Vercel environment variable and call it from a new function in `api/`.
