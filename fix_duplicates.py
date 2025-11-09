#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix duplicate entities in the database
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

REGISTRY_PATH = r'D:\00_dev\01_Ведомости\Юрчекер\law_ch\registry_entities_rows.csv'

def fix_duplicates():
    """Remove duplicate entities, keeping the first occurrence."""
    print("Loading registry...")
    df = pd.read_csv(REGISTRY_PATH, encoding='utf-8')
    original_count = len(df)
    print(f"Original count: {original_count:,} entities")

    # Find duplicates
    duplicates = df[df.duplicated(subset=['name'], keep=False)]
    duplicate_names = duplicates['name'].unique()

    print(f"\nFound {len(duplicate_names)} duplicate names affecting {len(duplicates)} rows")

    # Show which ones will be kept
    print("\nDuplicate resolution strategy:")
    for name in duplicate_names[:5]:
        dupes = df[df['name'] == name]
        print(f"\n'{name}':")
        for idx, row in dupes.iterrows():
            keep = "KEEP" if idx == dupes.index[0] else "REMOVE"
            print(f"  [{keep}] ID: {row['id'][:8]}... Type: {row['type']}")

    if len(duplicate_names) > 5:
        print(f"\n... and {len(duplicate_names) - 5} more duplicate groups")

    # Remove duplicates (keep first occurrence)
    df_clean = df.drop_duplicates(subset=['name'], keep='first')

    removed_count = original_count - len(df_clean)
    print(f"\n✂️  Removing {removed_count} duplicate entries...")

    # Save cleaned registry
    df_clean.to_csv(REGISTRY_PATH, index=False, encoding='utf-8')

    print(f"\n✅ Cleaned database saved!")
    print(f"   Before: {original_count:,} entities")
    print(f"   After:  {len(df_clean):,} entities")
    print(f"   Removed: {removed_count} duplicates")

    return removed_count


if __name__ == '__main__':
    fix_duplicates()
