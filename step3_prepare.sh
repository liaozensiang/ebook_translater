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

echo "Running Step 3: Prepare Review Session..."
echo "Input: $INPUT_EPUB"
echo "Work Dir: $WORK_DIR"

# Optional: Add --auto-translate if you want to pre-translate everything
# ARGS: --auto-translate

docker run --rm \
  -v $(pwd):/app \
  --env-file .env \
  ebook-translator \
  python3 src/main.py prepare \
    --input "$INPUT_EPUB" \
    --glossary "$ALIGN_OUTPUT_GLOSSARY" \
    --work-dir "$WORK_DIR" \
    --src-lang "$SRC_LANG" \
    --tgt-lang "$TGT_LANG" \
    --auto-translate 
