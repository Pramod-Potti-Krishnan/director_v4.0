# Railway CLI Reference Guide

A comprehensive reference for the Railway Command Line Interface (CLI).

**Official Documentation:** https://docs.railway.com/guides/cli
**CLI Reference:** https://docs.railway.com/reference/cli-api
**GitHub Repository:** https://github.com/railwayapp/cli

---

## Table of Contents

1. [Installation](#installation)
2. [Authentication](#authentication)
3. [Project Management](#project-management)
4. [Service Management](#service-management)
5. [Deployment Commands](#deployment-commands)
6. [Logs & Monitoring](#logs--monitoring)
7. [Environment Variables](#environment-variables)
8. [Database & Connections](#database--connections)
9. [SSH Access](#ssh-access)
10. [CI/CD Integration](#cicd-integration)
11. [Common Issues & Solutions](#common-issues--solutions)

---

## Installation

### Homebrew (macOS/Linux)
```bash
brew install railway
```

### NPM (macOS, Linux, Windows)
```bash
npm install -g @railway/cli
```
Requires Node.js version 16 or higher.

### Shell Script (macOS, Linux, Windows via WSL)
```bash
bash <(curl -fsSL cli.new)
```

### Scoop (Windows)
```powershell
scoop install railway
```

### Cargo (Rust)
```bash
cargo install railwayapp --locked
```

### Docker
```bash
docker pull ghcr.io/railwayapp/cli:latest
```

### AUR (Arch Linux)
```bash
paru -S railwayapp-cli
# or
yay -S railwayapp-cli
```

### Pre-built Binaries
Download from [GitHub Releases](https://github.com/railwayapp/cli/releases/latest)

---

## Authentication

### Interactive Login (Browser)
```bash
railway login
```
Opens browser for Railway authentication.

### Browserless Login
```bash
railway login --browserless
```
For environments without browser access (SSH sessions, remote servers).

### Token-Based Authentication

Railway supports two types of tokens:

#### Project Token (`RAILWAY_TOKEN`)
Used for deployment operations:
```bash
export RAILWAY_TOKEN=your-project-token
railway up
railway redeploy
railway logs
```

#### Account/Team Token (`RAILWAY_API_TOKEN`)
Used for account-level operations:
```bash
export RAILWAY_API_TOKEN=your-api-token
railway init
railway whoami
railway link
```

### Check Current User
```bash
railway whoami
```

### Logout
```bash
railway logout
```

---

## Project Management

### List All Projects
```bash
railway list
```

### Create New Project
```bash
railway init
railway init --name "my-project"
railway init --name "my-project" --workspace "my-workspace"
```

### Link to Existing Project
```bash
# Interactive mode
railway link

# With specific options
railway link --project "Project Name"
railway link --project "Project Name" --environment production
railway link --project "Project Name" --service "service-name"

# All options
railway link -p <PROJECT> -e <ENVIRONMENT> -s <SERVICE> -w <WORKSPACE>
```

### Check Project Status
```bash
railway status
railway status --json
```

### Unlink Project
```bash
railway unlink
```

### Open Project Dashboard
```bash
railway open
```

---

## Service Management

### Link to a Service
```bash
# Interactive mode (requires TTY)
railway service

# With service name or ID
railway service <service-name-or-id>
```

### Add New Service
```bash
# Add database
railway add --database postgres
railway add --database mysql
railway add --database redis
railway add --database mongo

# Add from Docker image
railway add --image nginx:latest

# Add from GitHub repo
railway add --repo https://github.com/user/repo
```

### Specify Service in Commands
Many commands accept `--service` flag:
```bash
railway logs --service <service-name-or-id>
railway up --service <service-name-or-id>
railway redeploy --service <service-name-or-id>
railway variables --service <service-name-or-id>
```

**Important:** The service ID from the UI (Ctrl+K copy) may differ from `RAILWAY_SERVICE_ID`. Get the correct ID from the service's Variables tab in the Railway dashboard.

---

## Deployment Commands

### Deploy Current Directory
```bash
railway up

# Deploy and detach (don't stream logs)
railway up --detach
railway up -d

# CI mode (only stream build logs, exit after build)
railway up --ci
railway up -c

# Deploy to specific service
railway up --service <service-name>

# Deploy to specific environment
railway up --environment production

# Deploy specific path
railway up ./path/to/project

# Include files ignored by .gitignore
railway up --no-gitignore

# Verbose output
railway up --verbose
```

### Redeploy Latest Deployment
```bash
railway redeploy

# Skip confirmation
railway redeploy --yes

# Redeploy specific service
railway redeploy --service <service-name>
```

### Remove Recent Deployment
```bash
railway down

# Skip confirmation
railway down --yes
```

### Deploy Template
```bash
railway deploy --template <template-name>
railway deploy --template <template-name> --variable "KEY=value"

# Service-specific variables
railway deploy --template <template> --variable "service.key=value"
```

---

## Logs & Monitoring

### View Logs
```bash
# Stream latest deployment logs
railway logs

# View logs for specific service
railway logs --service <service-name>

# View logs for specific environment
railway logs --environment production

# View only build logs
railway logs --build

# View only deployment logs (startup/runtime)
railway logs --deployment

# View logs for specific deployment ID
railway logs <deployment-id>

# Output as JSON
railway logs --json
```

### Log Filtering Syntax

Railway supports advanced filtering:

```bash
# Substring matching
railway logs  # then filter with: "error"

# Filter by log level
@level:error
@level:info
@level:warn

# Filter by service
@service:<service-id>

# Combine filters
@level:error AND "failed to send"

# Exclude services
-@service:<postgres-service-id>

# HTTP log filters
@path:/api/v1/users
@httpStatus:500
@srcIp:66.33.22.11
```

### Structured Logging
Emit single-line JSON for structured logs:
```json
{ "level": "info", "message": "A structured log message" }
```

---

## Environment Variables

### View Variables
```bash
railway variables
railway variables --service <service-name>
railway variables --environment production
railway variables --json
```

### Set Variables
```bash
railway variables --set KEY=value
railway variables --set KEY1=value1 --set KEY2=value2
```

### Run Command with Variables
```bash
# Execute command with Railway env vars injected
railway run <command>

# Examples
railway run npm start
railway run python main.py
railway run printenv
```

### Open Shell with Variables
```bash
railway shell
railway shell --service <service-name>
```

---

## Database & Connections

### Connect to Database Shell
```bash
railway connect
railway connect <service-name>
railway connect --environment production
```

Supported databases:
- PostgreSQL (requires `psql`)
- MySQL (requires `mysql`)
- MongoDB (requires `mongosh`)
- Redis (requires `redis-cli`)

### Provision Database
```bash
railway add --database postgres
railway add --database mysql
railway add --database redis
railway add --database mongo
```

---

## SSH Access

### Connect via SSH
```bash
# Interactive mode
railway ssh

# With specific options
railway ssh --project <project-id> --service <service-id> --environment <env-id>

# Execute single command
railway ssh -- ls -la
railway ssh -- cat /app/logs/error.log
```

### SSH Limitations
- No SCP/SFTP file transfer
- No SSH tunneling or port forwarding
- No VS Code Remote-SSH integration
- Requires running service (not sleeping instances)
- Uses WebSocket protocol (not standard SSH)

### File Transfer Workarounds
- Deploy file explorer service with shared volumes
- Use `curl` for uploads to external services
- Create temporary secured download endpoints

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service ${{ secrets.RAILWAY_SERVICE_ID }}
```

### Environment Variables for CI
```bash
# Required for deployment
RAILWAY_TOKEN=<project-token>

# Optional: specify service
RAILWAY_SERVICE_ID=<service-id>

# CI detection (auto-set in most CI environments)
CI=true
```

---

## Volume Management

### List Volumes
```bash
railway volume list
railway volume list --service <service-name>
```

### Add Volume
```bash
railway volume add
railway volume add --service <service-name>
```

### Attach/Detach Volume
```bash
railway volume attach
railway volume detach
```

### Delete Volume
```bash
railway volume delete
```

---

## Domain Management

### Add Domain
```bash
# Generate Railway domain
railway domain

# Add custom domain
railway domain my-custom-domain.com

# Specify port
railway domain --port 8080
railway domain my-domain.com --port 3000
```

---

## Environment Management

### Switch Environment
```bash
railway environment
railway environment production
railway environment staging
```

### Create New Environment
```bash
railway environment new <name>
```

### Delete Environment
```bash
railway environment delete <name>
```

---

## Shell Completions

Generate shell completions:
```bash
railway completion bash
railway completion zsh
railway completion fish
railway completion powershell
```

---

## Common Issues & Solutions

### "No service found" Error

**Problem:**
```
No service found. Please link one via `railway link` or specify one via the `--service` flag.
```

**Solutions:**
1. Link a service interactively:
   ```bash
   railway service  # Select from list
   ```

2. Specify service in command:
   ```bash
   railway logs --service <service-id>
   ```

3. Get correct service ID from Railway dashboard:
   - Go to your service in the dashboard
   - Click on "Variables" tab
   - Find `RAILWAY_SERVICE_ID` variable
   - **Note:** This may differ from the ID copied via Ctrl+K!

### Non-Interactive Environments (CI/CD)

For environments without TTY:
```bash
# Set token
export RAILWAY_TOKEN=your-project-token

# Use --service flag instead of interactive selection
railway logs --service <service-id>
railway up --service <service-id>
railway redeploy --service <service-id>
```

### Finding Service IDs

1. **From Dashboard:** Service > Variables > `RAILWAY_SERVICE_ID`
2. **From Status Command:**
   ```bash
   railway status --json
   ```
3. **From Link Command (when successful):**
   ```bash
   railway link --json
   ```

---

## Quick Reference Card

| Command | Purpose |
|---------|---------|
| `railway login` | Authenticate with Railway |
| `railway list` | List all projects |
| `railway link` | Link current directory to project |
| `railway service` | Link to specific service |
| `railway status` | Show project/service status |
| `railway up` | Deploy current directory |
| `railway up -d` | Deploy and detach |
| `railway logs` | Stream deployment logs |
| `railway logs --service X` | Logs for specific service |
| `railway run <cmd>` | Run command with env vars |
| `railway shell` | Open shell with env vars |
| `railway variables` | View environment variables |
| `railway connect` | Connect to database shell |
| `railway ssh` | SSH into running service |
| `railway redeploy` | Redeploy current service |
| `railway down` | Remove latest deployment |
| `railway open` | Open project in browser |
| `railway whoami` | Show current user |
| `railway logout` | Sign out |

---

## Useful Links

- **Documentation:** https://docs.railway.com/guides/cli
- **CLI Reference:** https://docs.railway.com/reference/cli-api
- **GitHub:** https://github.com/railwayapp/cli
- **Logs Guide:** https://docs.railway.com/guides/logs
- **Services Guide:** https://docs.railway.com/guides/services
- **Help Station:** https://station.railway.com

---

*Last updated: December 2024*
