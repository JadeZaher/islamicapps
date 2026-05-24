# Text Cleanup & Embedding Preparation

## Problem

The data readiness audit identified text quality issues that will degrade embedding quality:

| Issue | Count | Impact |
|---|---|---|
| Arabic texts with OCR numeric sequences | 7,302 | Noise in embeddings, wrong similarity matches |
| English texts with AI refusal artifacts | 484 | "I cannot translate..." embeds as refusal, not hadith content |
| Very short Arabic texts (<20 chars) | 922 | Fragments produce low-quality embeddings |

Total affected: ~8,700 texts out of 99,029 (~8.8%).

## Goal

Clean all text data to produce high-quality embeddings:
1. Strip or flag OCR artifacts in Arabic text (numeric sequences, non-Arabic characters)
2. Re-translate or remove AI refusal artifacts from English text
3. Flag or exclude very short texts from embedding pipeline
4. Normalize Arabic text (diacritics, alif variants, ta marbuta) for consistent embeddings

## Constraints

- Preserve original text in a backup property (text_arabic_raw, text_english_raw) before any modification
- Never delete hadith nodes — only clean their text properties
- Refusal re-translations require Ollama or API access
- All scripts idempotent

## Success Criteria

- OCR artifact count drops below 500
- AI refusal count drops to 0 (re-translated or flagged)
- All texts >10 chars ready for embedding
- Re-run audit shows all text checks PASS
