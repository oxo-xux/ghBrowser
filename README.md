# ghBrowser

Password-protected cloud browser running in GitHub Actions with Cloudflare free tunnel.

## How It Works

- GitHub Actions spins up a full XFCE desktop + Firefox browser
- Webtop's built-in password protects access
- Cloudflare free quick tunnel gives you a public `*.trycloudflare.com` URL
- Runs for **5 hours 50 minutes** per workflow dispatch
- **No server, no Cloudflare account needed** — everything runs in GitHub Actions

## Setup

### 1. Add GitHub Secret

Go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|---|---|
| `BASIC_AUTH_PASSWORD` | Your login password (any string, e.g. `mypassword123`) |

### 2. Run

Go to **Actions > Run Browser > Run workflow** and click "Run workflow".

The browser URL will appear in:
- The job log output
- The job summary page

### 3. Access

Open the URL → enter your `BASIC_AUTH_PASSWORD` secret value as the password.

## Architecture

```
Cloudflare Free Tunnel (*.trycloudflare.com)
    → LinuxServer Webtop (XFCE + Firefox, port 3000)
```

All running inside a GitHub Actions runner for 5h 50min.
