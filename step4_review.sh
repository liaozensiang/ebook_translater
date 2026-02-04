#!/bin/bash

if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo ".env file not found."
  exit 1
fi

echo "Building Translator Image..."
docker build -t ebook-translator . > /dev/null

echo "Running Step 4: Web Review UI..."
echo "Access at http://localhost:$APP_PORT"

docker run --rm -it \
  -v $(pwd):/app \
  -p $APP_PORT:$APP_PORT \
  --env-file .env \
  ebook-translator \
  python3 src/main.py review --port $APP_PORT
