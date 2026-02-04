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

echo "Running Step 5: Export Final EPUB..."
echo "Input: $INPUT_EPUB"
echo "Output: $OUTPUT_EPUB"

docker run --rm \
  -v $(pwd):/app \
  --env-file .env \
  ebook-translator \
  python3 src/main.py export \
    --input "$INPUT_EPUB" \
    --output "$OUTPUT_EPUB" \
    --work-dir "$WORK_DIR"
