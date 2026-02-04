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

echo "Running Step 2: Extract New Terms..."
echo "Input: $INPUT_EPUB"

docker run --rm \
  -v $(pwd):/app \
  --env-file .env \
  ebook-translator \
  python3 src/main.py extract-glossary \
    --input "$INPUT_EPUB" \
    --base_glossary "$ALIGN_OUTPUT_GLOSSARY" \
    --src-lang "$SRC_LANG" \
    --tgt-lang "$TGT_LANG"
