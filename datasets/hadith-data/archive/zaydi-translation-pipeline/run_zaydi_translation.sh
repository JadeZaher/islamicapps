#!/usr/bin/env bash
# Translate Zaydi hadiths from Arabic to English using Ollama
# Prerequisites: ollama pull llama3.1:8b && ollama serve

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

python "$ROOT_DIR/datasets/translate_ollama_generic.py" \
  --input "$SCRIPT_DIR/zaydi_for_translation.jsonl" \
  --output "$SCRIPT_DIR/zaydi_translated.jsonl" \
  --source-field text_ar \
  --dest-field text_en \
  --prompt-file "$SCRIPT_DIR/zaydi_translation_prompt.txt" \
  --model llama3.1:8b \
  --temperature 0.2 \
  --num-predict 1024 \
  --resume

echo ""
echo "Translation complete. Run merge script next:"
echo "  python merge_zaydi_translations.py"
