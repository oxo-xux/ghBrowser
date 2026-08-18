# ghBrowser

Password-protected private cloud browser running in GitHub Actions with Cloudflare free tunnel.

## How It Works

- GitHub Actions spins up a Firefox browser (linuxserver/firefox)
- Python auth proxy shows a sign-in dashboard, validates password, sets session cookie
- Cloudflare free quick tunnel gives you a public `*.trycloudflare.com` URL
- Runs for **5 hours 50 minutes** per workflow dispatch
- **No server, no Cloudflare account needed** — everything runs in GitHub Actions

## Setup

### 1. Add GitHub Secret

Go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|---|---|
| `BASIC_AUTH_PASSWORD` | Your login password |

### 2. Run

Go to **Actions > Run Browser > Run workflow**.

The URL appears in the job log and summary.

### 3. Access

Open the URL → sign in with your password → full Firefox browser.

## Architecture

```
Cloudflare Free Tunnel (*.trycloudflare.com)
    → Python Auth Proxy (sign-in dashboard, port 8080)
        → LinuxServer Firefox (port 3000)
```
