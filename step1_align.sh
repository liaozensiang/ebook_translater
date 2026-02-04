#!/bin/bash

if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo ".env file not found."
  exit 1
fi

# Ensure Image is Built
echo "Building Translator Image..."
docker build -t ebook-translator . > /dev/null

echo "Running Step 1: Align & Create Base Glossary..."
echo "Source: $ALIGN_SOURCE_EPUB"
echo "Reference: $ALIGN_REF_EPUB"

docker run --rm \
  -v $(pwd):/app \
  --env-file .env \
  ebook-translator \
  python3 src/main.py align \
    --source "$ALIGN_SOURCE_EPUB" \
    --reference "$ALIGN_REF_EPUB" \
    --out "$ALIGN_OUTPUT_GLOSSARY" \
    --src-lang "$SRC_LANG" \
    --tgt-lang "$TGT_LANG"
