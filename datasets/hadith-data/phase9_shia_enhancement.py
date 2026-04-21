#!/usr/bin/env python3
"""
Phase 9: Enhanced Shia Volumes Processing
Extract sanad data from remaining Shia sources (Al-Kāfi, Nahj al-Balāgha, etc.)
Goal: +2-3% improvement in overall data completeness
"""
import pandas as pd
import json
import os
import re
from pathlib import Path
from datetime import datetime

# Paths
CONSOLIDATED_CSV = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/unified_hadith_consolidated.csv'
SHIA_VOLUMES_DIR = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/shia-hadith/v2_books/'
BOOK_NAMES_FILE = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/shia-hadith/v2_books/BookNames.json'
OUTPUT_CSV = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/unified_hadith_consolidated_phase9.csv'

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ PHASE 9: Enhanced Shia Volumes Processing")
print("="*80)

try:
    # Load consolidated dataset
    print("\n[Loading consolidated dataset...]")
    df = pd.read_csv(CONSOLIDATED_CSV, low_memory=False)
    print(f"  Loaded {len(df)} records")
    
    # Load book names
    with open(BOOK_NAMES_FILE, 'r', encoding='utf-8') as f:
        book_names = json.load(f)
    
    # Track enhancement metrics
    enhancement_stats = {
        'sources_processed': [],
        'records_enhanced': 0,
        'sanads_extracted': 0,
        'sanad_fields_filled': 0
    }
    
    # Identify remaining Shia sources for processing (excluding volumes 34-38 already processed)
    volumes_to_process = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]
    
    for vol_num in volumes_to_process[:3]:  # Process first 3 remaining sources this hour
        vol_file = os.path.join(SHIA_VOLUMES_DIR, f'{vol_num}.json')
        
        if not os.path.exists(vol_file):
            continue
        
        print(f"\n[Processing Volume {vol_num}...]")
        
        with open(vol_file, 'r', encoding='utf-8') as f:
            vol_data = json.load(f)
        
        book_name = book_names.get(str(vol_num), f'Volume {vol_num}')
        enhancement_stats['sources_processed'].append(book_name)
        
        # Extract sanads from this volume
        for record in vol_data.get('hadiths', []):
            if 'sanad' in record and record['sanad']:
                enhancement_stats['sanads_extracted'] += 1
                
                # Try to match with consolidated dataset
                # Match based on volume + hadith_id if available
                if 'id' in record and 'volume' in record:
                    hadith_id = record['id']
                    volume = record.get('volume', vol_num)
                    
                    # Find matching records in consolidated dataset
                    matches = df[(df['volume'] == volume) & (df['hadith_number'] == hadith_id)]
                    
                    for idx, match_row in matches.iterrows():
                        # Only fill empty sanad fields
                        if pd.isna(match_row['sanad_arabic']) or match_row['sanad_arabic'] == '':
                            df.at[idx, 'sanad_arabic'] = record['sanad']
                            
                            # Try to get sanad_english if available
                            if 'sanad_en' in record:
                                df.at[idx, 'sanad_english'] = record['sanad_en']
                            
                            enhancement_stats['sanad_fields_filled'] += 1
        
        print(f"  ✓ Extracted {enhancement_stats['sanads_extracted']} sanads")
        print(f"  ✓ Filled {enhancement_stats['sanad_fields_filled']} sanad fields")
    
    # Calculate improvements
    original_sanad_count = 56445  # From Phase 8
    new_sanad_count = df[df['sanad_arabic'].notna() & (df['sanad_arabic'] != '')].shape[0]
    improvement = new_sanad_count - original_sanad_count
    
    print(f"\n[Sanad Enhancement Summary...]")
    print(f"  Original sanad count: {original_sanad_count}")
    print(f"  New sanad count: {new_sanad_count}")
    print(f"  Records enhanced: {improvement}")
    print(f"  Improvement percentage: +{(improvement/len(df))*100:.2f}%")
    
    # Save enhanced dataset
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"\n✓ Saved enhanced dataset to {OUTPUT_CSV}")
    
    # Report
    print("\n" + "="*80)
    print("[PHASE 9 COMPLETION REPORT]")
    print(f"Sources processed: {len(enhancement_stats['sources_processed'])}")
    for source in enhancement_stats['sources_processed']:
        print(f"  - {source}")
    print(f"Sanads extracted: {enhancement_stats['sanads_extracted']}")
    print(f"Sanad fields filled: {enhancement_stats['sanad_fields_filled']}")
    print(f"Dataset completeness: {new_sanad_count} records ({(new_sanad_count/len(df))*100:.1f}%)")
    print("="*80)

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

