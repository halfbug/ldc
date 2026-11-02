#!/usr/bin/env bash
# Runs the suite in Playwright's own image (same version as swo-3.0/e2e), so nothing is installed on the host.
#   ./run.sh                                   every project
#   ./run.sh --project=api                     HTTP checks only, no browser, no credits
#   ./run.sh --project=ui --grep '#12'         one case
# Settings come from .env (see .env.example). Results: results/html/index.html, results/junit.xml.
#
# Local stack: the container shares Docker's host network, so the published swo ports (3001, 3002) answer on
# localhost, but rag started with `make run` listens on the WSL host, not in Docker. E2E_FORWARD_PORTS (e.g. 8002)
# forwards those ports inside the container to this machine, so the app's own http://localhost:8002 works.
# "8002:8003" forwards the container's 8002 to this machine's 8003 (a second rag, e.g. one with guardrails set).
set -euo pipefail
cd "$(dirname "$0")"
IMAGE=mcr.microsoft.com/playwright:v1.63.0-noble
ENV_FILE=()
[ -f .env ] && ENV_FILE=(--env-file .env)
FORWARD_PORTS="$(grep -E '^E2E_FORWARD_PORTS=' .env 2>/dev/null | cut -d= -f2- || true)"
HOST_IP="$(hostname -I | awk '{print $1}')"
docker run --rm --ipc=host --network host --user "$(id -u):$(id -g)" -e HOME=/tmp \
    -e FORWARD_PORTS="$FORWARD_PORTS" -e FORWARD_HOST="$HOST_IP" \
    "${ENV_FILE[@]}" -v "$PWD":/work -w /work "$IMAGE" \
    bash -c '
        [ -d node_modules/@playwright/test ] || npm install --no-audit --no-fund --loglevel=error
        for pair in $FORWARD_PORTS; do
            port=${pair%%:*}; target=${pair##*:}
            node -e "const n=require(\"net\");n.createServer(c=>{const u=n.connect($target,process.env.FORWARD_HOST);c.pipe(u).pipe(c);u.on(\"error\",()=>c.destroy());c.on(\"error\",()=>u.destroy())}).listen($port,\"127.0.0.1\")" &
        done
        sleep 1
        npx playwright test "$@"' _ "$@"
