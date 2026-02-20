# AGENTS.md — PM Agent for FundFish

> **App:** https://fundfish.pro
> **Backend:** https://per-scholas-capstone.onrender.com
> **Repo:** ~/projects/perscholas-fundraising-demo

---

## 📋 Backend Logs (Render)

You have access to production logs via the Render CLI. **Use these proactively** to find issues, debug errors, and monitor health after deploys.

```bash
# Quick checks
bash ~/.claude/lib/render-logs.sh capstone --errors --last-hour    # Recent errors
bash ~/.claude/lib/render-logs.sh capstone --errors --last-day     # Errors in last 24h
bash ~/.claude/lib/render-logs.sh capstone --text "500" --limit 20 # 500 errors
bash ~/.claude/lib/render-logs.sh capstone --text "traceback"      # Python tracebacks
bash ~/.claude/lib/render-logs.sh capstone --limit 100             # General recent logs

# Direct Render CLI (more flexibility)
render logs -r srv-d5kejlvgi27c739pl6ag --limit 50 --output text
render logs -r srv-d5kejlvgi27c739pl6ag --level error --output text
```

**Service ID:** `srv-d5kejlvgi27c739pl6ag`

**When to check logs:**
- After any deploy (look for startup errors)
- When investigating bug reports
- During your daily run — check if your changes broke anything
- Proactively as part of health checks

**API key:** `RENDER_API_KEY` is in `~/.bashrc` — source it or export directly.

---

## Development

- **Stack:** Docker on Render
- **Deploy:** Push to main → auto-deploy
- **Decisions:** See `DECISIONS.md` for priorities

## WhatsApp
- **Always use E.164 format to message Ayaan:** `+12173777889`
- Do NOT use "Ayaan" as target — it will fail with "Unknown target"
- Example: `message(action="send", target="+12173777889", message="...")`

