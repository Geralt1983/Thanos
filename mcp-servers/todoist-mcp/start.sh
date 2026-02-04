#!/bin/bash
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env.local ]; then
  export $(cat .env.local | grep -v '^#' | xargs)
fi

if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Also check parent Thanos .env
if [ -f ../../.env ]; then
  export $(cat ../../.env | grep -v '^#' | xargs)
fi

exec node dist/index.js
