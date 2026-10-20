#!/usr/bin/with-contenv bashio
bashio::log.info "Starting Fit Plan on :8098 …"
cd /app
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 8098 --no-access-log
