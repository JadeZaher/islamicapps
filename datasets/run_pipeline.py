#!/usr/bin/env python3
"""
run_pipeline.py
================
Master script to run the full Musnad extraction pipeline.

Steps:
  1. OCR extraction (pdf2image + easyocr)
  2. Parse hadiths from OCR text
  3. Translate via Ollama/Gemma (optional, requires Ollama running)
  4. Generate CSV datasets

Usage:
    # Full pipeline (without translation):
    python run_pipeline.py --pdf /path/to/ibadimusnad.pdf

    # Full pipeline with translation:
    python run_pipeline.py --pdf /path/to/ibadimusnad.pdf --translate --model gemma3:12b

    # Just regenerate CSVs from existing parsed data:
    python run_pipeline.py --csv-only

    # OCR specific page range:
    python run_pipeline.py --pdf /path/to/ibadimusnad.pdf --start 11 --end 50
"""

import argparse
import os
import sys
import subprocess


def run_step(script, args_list, description):
    """Run a pipeline step."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    cmd = [sys.executable, script] + args_list
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    if result.returncode != 0:
        print(f"\nERROR: {description} failed with exit code {result.returncode}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description='Run the full Musnad extraction pipeline')
    parser.add_argument('--pdf', help='Path to ibadimusnad.pdf')
    parser.add_argument('--output-dir', default='.', help='Output directory for intermediate files')
    parser.add_argument('--start', type=int, default=None, help='Start PDF page for OCR')
    parser.add_argument('--end', type=int, default=None, help='End PDF page for OCR')
    parser.add_argument('--dpi', type=int, default=300, help='DPI for image conversion')
    parser.add_argument('--translate', action='store_true', help='Run translation via Ollama')
    parser.add_argument('--model', default='gemma3:12b', help='Ollama model for translation')
    parser.add_argument('--csv-only', action='store_true', help='Only regenerate CSVs')
    parser.add_argument('--skip-ocr', action='store_true', help='Skip OCR step')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    ocr_output = os.path.join(args.output_dir, 'raw_ocr_pages.json')
    parsed_output = os.path.join(args.output_dir, 'parsed_hadiths.json')
    translated_output = os.path.join(args.output_dir, 'translated_hadiths.json')

    if args.csv_only:
        # Just regenerate CSVs
        input_file = translated_output if os.path.exists(translated_output) else parsed_output
        if not os.path.exists(input_file):
            print(f"ERROR: No parsed data found at {input_file}")
            sys.exit(1)
        run_step('04_generate_csvs.py',
                 ['--input', input_file, '--output-dir', args.output_dir],
                 'Step 4: Generate CSVs')
        return

    # Step 1: OCR
    if not args.skip_ocr:
        if not args.pdf:
            print("ERROR: --pdf is required for OCR step")
            sys.exit(1)
        ocr_args = ['--pdf', args.pdf, '--output', ocr_output, '--dpi', str(args.dpi)]
        if args.start:
            ocr_args += ['--start', str(args.start)]
        if args.end:
            ocr_args += ['--end', str(args.end)]
        if not run_step('01_ocr_extract.py', ocr_args, 'Step 1: OCR Extraction'):
            sys.exit(1)

    # Step 2: Parse
    if not run_step('02_parse_hadiths.py',
                    ['--input', ocr_output, '--output', parsed_output],
                    'Step 2: Parse Hadiths'):
        sys.exit(1)

    # Step 3: Translate (optional)
    if args.translate:
        if not run_step('03_translate_ollama.py',
                        ['--input', parsed_output, '--output', translated_output,
                         '--model', args.model],
                        'Step 3: Translate via Ollama/Gemma'):
            print("WARNING: Translation failed, continuing with Arabic-only data.")

    # Step 4: Generate CSVs
    csv_input = translated_output if os.path.exists(translated_output) else parsed_output
    if not run_step('04_generate_csvs.py',
                    ['--input', csv_input, '--output-dir', args.output_dir],
                    'Step 4: Generate CSVs'):
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Pipeline complete!")
    print(f"{'='*60}")
    print(f"\nOutputs:")
    print(f"  OCR data:    {ocr_output}")
    print(f"  Parsed:      {parsed_output}")
    if os.path.exists(translated_output):
        print(f"  Translated:  {translated_output}")
    print(f"  Hadith CSV:  {os.path.join(args.output_dir, 'musnad_hadiths.csv')}")
    print(f"  Narrator CSV:{os.path.join(args.output_dir, 'musnad_rawis.csv')}")


if __name__ == '__main__':
    main()
