#!/bin/bash
# Run both translation pipelines sequentially.
# Usage: bash datasets/hadith-data/sheikahmad/run_translations.sh
set -e
cd "$(dirname "$0")/../../.."

SCRIPT=datasets/translate_ollama_generic.py
PROMPT=datasets/hadith-data/sheikahmad/prompt_hadith_ar_to_en.txt
MODEL=llama3.1:8b

DEDUP=datasets/dedup_jsonl.py

echo "=== Starting Pure Canon translation (100,217 rows) ==="
python -u "$SCRIPT" \
  --input  datasets/hadith-data/sheikahmad/pure_canon.jsonl \
  --output datasets/hadith-data/sheikahmad/pure_canon_en.jsonl \
  --source-field text_ar --dest-field text_en --id-field id \
  --prompt-file "$PROMPT" --model "$MODEL" \
  --temperature 0.2 --num-predict 1024 --batch-save 50 --resume

echo "Deduplicating Pure Canon..."
python "$DEDUP" --input datasets/hadith-data/sheikahmad/pure_canon_en.jsonl --id-field id

echo ""
echo "=== Starting Green Book translation (35,453 rows) ==="
python -u "$SCRIPT" \
  --input  datasets/hadith-data/sheikahmad/green_book.jsonl \
  --output datasets/hadith-data/sheikahmad/green_book_en.jsonl \
  --source-field text_ar --dest-field text_en --id-field id \
  --prompt-file "$PROMPT" --model "$MODEL" \
  --temperature 0.2 --num-predict 1024 --batch-save 50 --resume

echo "Deduplicating Green Book..."
python "$DEDUP" --input datasets/hadith-data/sheikahmad/green_book_en.jsonl --id-field id

echo ""
echo "=== Both translations complete ==="
