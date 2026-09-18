#!/usr/bin/with-contenv bashio
bashio::log.info "Starting Evo Scheduler on :8099 …"
cd /app
exec python3 -m uvicorn server:app --host 0.0.0.0 --port 8099 --no-access-log
