#!/usr/bin/env python3
"""
Phase 9: Enhanced Shia Sanad Extraction
Extract sanad data from Shia JSON volumes to fill missing sanad fields
Focus: Al-Kāfi, Al-Amālī, Al-Khiṣāl, Nahj al-Balāgha
"""
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

# Paths
CONSOLIDATED_CSV = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/unified_hadith_consolidated.csv'
SHIA_VOLUMES_DIR = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/shia-hadith/v2_books/'
OUTPUT_CSV = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/unified_hadith_consolidated.csv'

print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ PHASE 9: Enhanced Shia Sanad Extraction")
print("="*80)

try:
    # Load consolidated dataset
    print("\n[Loading consolidated dataset...]")
    df = pd.read_csv(CONSOLIDATED_CSV, low_memory=False)
    print(f"  Loaded {len(df)} records")
    
    # Count initial sanads
    initial_sanad_count = df[(df['sanad_arabic'].notna()) & (df['sanad_arabic'] != '')].shape[0]
    print(f"  Initial sanad_arabic count: {initial_sanad_count}")
    
    # Mapping of volume numbers to expected source names
    # Based on BookNames.json structure
    source_mapping = {
        1: ['Al-Kāfi', 'Al-Khiṣāl', "ʿUyūn akhbār al-Riḍā", 'Al-Amālī'],  # Vol 1 has multiple books
        2: ['Al-Kāfi', 'Man Lā Yaḥḍuruh al-Faqīh'],
        3: ['Al-Kāfi', 'Man Lā Yaḥḍuruh al-Faqīh'],
        4: ['Al-Kāfi', 'Man Lā Yaḥḍuruh al-Faqīh'],
        5: ['Al-Kāfi', 'Man Lā Yaḥḍuruh al-Faqīh'],
        6: ['Al-Kāfi'],
        7: ['Al-Kāfi'],
        8: ['Al-Kāfi'],
        10: ['Nahj al-Balāgha'],
        11: ['Al-Amālī'],
    }
    
    # Volumes to process (excluding 34-38 from Phase 8)
    volumes_to_process = [1, 2, 3, 4, 5]  # Process first 5 volumes this hour
    
    enhancement_stats = {
        'volumes_processed': 0,
        'hadiths_found': 0,
        'sanads_matched': 0,
        'sanads_filled': 0,
        'english_sanads_filled': 0,
        'sources_processed': set()
    }
    
    for vol_num in volumes_to_process:
        vol_file = os.path.join(SHIA_VOLUMES_DIR, f'{vol_num}.json')
        
        if not os.path.exists(vol_file):
            print(f"  [Skip] Volume {vol_num} file not found")
            continue
        
        print(f"\n[Processing Volume {vol_num}...]")
        
        # Load volume data
        with open(vol_file, 'r', encoding='utf-8') as f:
            vol_data = json.load(f)
        
        print(f"  Loaded {len(vol_data)} hadith records")
        enhancement_stats['volumes_processed'] += 1
        
        # Extract sanads from this volume
        matched_count = 0
        for hadith in vol_data:
            enhancement_stats['hadiths_found'] += 1
            
            # Get sanad data from thaqalayn
            sanad_ar = hadith.get('thaqalaynSanad', '').strip()
            
            if not sanad_ar:
                continue
            
            # Extract identifying information
            book_name = hadith.get('book', '')
            hadith_id = hadith.get('id')
            
            if book_name:
                enhancement_stats['sources_processed'].add(book_name)
            
            # Find matching records in consolidated dataset
            matches = df[(df['source_canonical'] == book_name) & (df['hadith_number'] == hadith_id)]
            
            for idx, match_row in matches.iterrows():
                # Only fill empty sanad fields (preserve existing data)
                has_sanad = pd.notna(match_row['sanad_arabic']) and match_row['sanad_arabic'] != ''
                
                if not has_sanad:
                    df.at[idx, 'sanad_arabic'] = sanad_ar
                    enhancement_stats['sanads_filled'] += 1
                    matched_count += 1
        
        print(f"  ✓ Matched and filled: {matched_count} records")
        enhancement_stats['sanads_matched'] += matched_count
    
    # Calculate final metrics
    final_sanad_count = df[(df['sanad_arabic'].notna()) & (df['sanad_arabic'] != '')].shape[0]
    improvement = final_sanad_count - initial_sanad_count
    
    print(f"\n[Sanad Enhancement Summary]")
    print(f"  Initial sanad count: {initial_sanad_count}")
    print(f"  Final sanad count: {final_sanad_count}")
    print(f"  Records enhanced: {improvement}")
    print(f"  Improvement: +{(improvement/len(df))*100:.2f}%")
    print(f"  Sources processed: {len(enhancement_stats['sources_processed'])}")
    
    # Save enhanced dataset
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"\n✓ Saved enhanced dataset back to {OUTPUT_CSV}")
    
    # Append to consolidation log
    log_file = '/sessions/nice-admiring-davinci/mnt/islamicapps/datasets/hadith-data/CONSOLIDATION_LOG.txt'
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ PHASE 9 COMPLETE: Enhanced Shia Sanad Extraction\n")
        log.write(f"  Volumes processed: {enhancement_stats['volumes_processed']}\n")
        log.write(f"  Sanads extracted: {enhancement_stats['hadiths_found']}\n")
        log.write(f"  Sanads matched and filled: {improvement}\n")
        log.write(f"  Final sanad count: {final_sanad_count} ({(final_sanad_count/len(df))*100:.1f}%)\n")
        log.write(f"  Status: Ready for Excel regeneration\n")
    
    print("\n" + "="*80)
    print("[PHASE 9 COMPLETION REPORT]")
    print(f"Volumes processed: {enhancement_stats['volumes_processed']}")
    print(f"Hadiths analyzed: {enhancement_stats['hadiths_found']}")
    print(f"Sanads filled: {improvement}")
    print(f"New sanad coverage: {final_sanad_count}/{len(df)} ({(final_sanad_count/len(df))*100:.1f}%)")
    print(f"Sources enhanced: {', '.join(sorted(enhancement_stats['sources_processed']))}")
    print("="*80)

except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

