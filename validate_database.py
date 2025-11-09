#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database validation script - checks for errors, bugs, and data quality issues
"""

import pandas as pd
import json
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

REGISTRY_PATH = r'D:\00_dev\01_Ведомости\Юрчекер\law_ch\registry_entities_rows.csv'

def load_registry():
    """Load registry CSV."""
    print("Loading registry...")
    df = pd.read_csv(REGISTRY_PATH, encoding='utf-8')
    print(f"✅ Loaded {len(df)} entities\n")
    return df


def check_duplicates(df):
    """Check for duplicate entities."""
    print("="*60)
    print("CHECK 1: DUPLICATE DETECTION")
    print("="*60)

    # Check exact name duplicates
    name_counts = df['name'].value_counts()
    duplicates = name_counts[name_counts > 1]

    if len(duplicates) > 0:
        print(f"❌ FOUND {len(duplicates)} duplicate names:")
        for name, count in duplicates.head(10).items():
            print(f"   - '{name}' appears {count} times")
            dupes = df[df['name'] == name]
            for idx, row in dupes.iterrows():
                print(f"      ID: {row['id']}, Type: {row['type']}")
        if len(duplicates) > 10:
            print(f"   ... and {len(duplicates) - 10} more duplicates")
    else:
        print("✅ No exact duplicate names found")

    # Check normalized name duplicates (case-insensitive, whitespace normalized)
    df['name_normalized'] = df['name'].str.lower().str.strip().str.replace(r'\s+', ' ', regex=True)
    normalized_counts = df['name_normalized'].value_counts()
    normalized_duplicates = normalized_counts[normalized_counts > 1]

    if len(normalized_duplicates) > 0:
        print(f"\n⚠️  FOUND {len(normalized_duplicates)} case-insensitive duplicates:")
        for norm_name, count in normalized_duplicates.head(10).items():
            print(f"   - '{norm_name}' ({count} times)")
            matches = df[df['name_normalized'] == norm_name]['name'].unique()
            print(f"      Variants: {list(matches)}")
        if len(normalized_duplicates) > 10:
            print(f"   ... and {len(normalized_duplicates) - 10} more")
    else:
        print("✅ No case-insensitive duplicates found")

    # Check duplicate IDs
    id_counts = df['id'].value_counts()
    id_duplicates = id_counts[id_counts > 1]

    if len(id_duplicates) > 0:
        print(f"\n❌ CRITICAL: {len(id_duplicates)} duplicate IDs found!")
        for entity_id, count in id_duplicates.head(5).items():
            print(f"   - ID '{entity_id}' used {count} times")
    else:
        print("\n✅ All IDs are unique")

    return len(duplicates), len(normalized_duplicates), len(id_duplicates)


def check_data_integrity(df):
    """Check for data integrity issues."""
    print("\n" + "="*60)
    print("CHECK 2: DATA INTEGRITY")
    print("="*60)

    issues = []

    # Check for empty names
    empty_names = df[df['name'].isna() | (df['name'].str.strip() == '')]
    if len(empty_names) > 0:
        print(f"❌ FOUND {len(empty_names)} entities with empty names:")
        for idx, row in empty_names.head(5).iterrows():
            print(f"   - Row {idx}: ID={row['id']}, Type={row['type']}")
        issues.append(f"{len(empty_names)} empty names")
    else:
        print("✅ No empty names")

    # Check for missing IDs
    missing_ids = df[df['id'].isna()]
    if len(missing_ids) > 0:
        print(f"\n❌ FOUND {len(missing_ids)} entities with missing IDs")
        issues.append(f"{len(missing_ids)} missing IDs")
    else:
        print("✅ All entities have IDs")

    # Check for invalid types
    valid_types = ['иноагенты', 'экстремисты', 'террористы', 'нежелательные', 'террористы и экстремисты']
    invalid_types = df[~df['type'].isin(valid_types)]
    if len(invalid_types) > 0:
        print(f"\n❌ FOUND {len(invalid_types)} entities with invalid types:")
        invalid_type_counts = invalid_types['type'].value_counts()
        for type_val, count in invalid_type_counts.items():
            print(f"   - '{type_val}': {count} entities")
        issues.append(f"{len(invalid_types)} invalid types")
    else:
        print("✅ All types are valid")

    # Check for names that are too short (likely errors)
    short_names = df[df['name'].str.len() < 3]
    if len(short_names) > 0:
        print(f"\n⚠️  FOUND {len(short_names)} entities with very short names (<3 chars):")
        for idx, row in short_names.head(10).iterrows():
            print(f"   - '{row['name']}' (Type: {row['type']})")
        issues.append(f"{len(short_names)} very short names")
    else:
        print("✅ No suspiciously short names")

    # Check for names that are too long (potential data corruption)
    long_names = df[df['name'].str.len() > 200]
    if len(long_names) > 0:
        print(f"\n⚠️  FOUND {len(long_names)} entities with very long names (>200 chars):")
        for idx, row in long_names.head(5).iterrows():
            print(f"   - {row['name'][:80]}... (Type: {row['type']}, Length: {len(row['name'])})")
        issues.append(f"{len(long_names)} very long names")
    else:
        print("✅ No suspiciously long names")

    # Check aliases format
    print("\n✅ Checking aliases field...")
    malformed_aliases = 0
    for idx, row in df.iterrows():
        if pd.notna(row['aliases']) and row['aliases'] != '':
            try:
                # Try to parse as JSON
                if isinstance(row['aliases'], str):
                    json.loads(row['aliases'])
            except (json.JSONDecodeError, TypeError):
                malformed_aliases += 1
                if malformed_aliases <= 5:
                    print(f"   ⚠️  Row {idx}: Malformed aliases for {row['name']}")

    if malformed_aliases > 0:
        print(f"⚠️  FOUND {malformed_aliases} entities with malformed aliases")
        issues.append(f"{malformed_aliases} malformed aliases")
    else:
        print("✅ All aliases are properly formatted")

    return issues


def check_alias_quality(df):
    """Check alias generation quality using JurChecker."""
    print("\n" + "="*60)
    print("CHECK 3: ALIAS GENERATION QUALITY")
    print("="*60)

    try:
        from jur_checker import JurChecker

        print("Loading JurChecker to analyze alias generation...")
        checker = JurChecker('registry_entities_rows.csv')

        print("✅ JurChecker loaded successfully")
        print("   Automaton built - alias generation working")

        # Sample test searches
        print("\n📝 Testing sample searches:")
        test_cases = [
            "Навальный",
            "Алексей Навальный",
            "Навального",
            "Navalny",
        ]

        for test in test_cases:
            results = checker.find_raw_candidates(test)
            print(f"   '{test}': {len(results)} matches")

        return True

    except Exception as e:
        print(f"❌ ERROR loading JurChecker: {e}")
        return False


def check_type_distribution(df):
    """Check entity type distribution for anomalies."""
    print("\n" + "="*60)
    print("CHECK 4: TYPE DISTRIBUTION")
    print("="*60)

    type_counts = df['type'].value_counts()
    total = len(df)

    print(f"Total entities: {total:,}\n")
    for entity_type, count in type_counts.items():
        percentage = (count / total) * 100
        print(f"   {entity_type}: {count:,} ({percentage:.1f}%)")

    # Check for suspicious distributions
    if type_counts.max() / total > 0.95:
        print("\n⚠️  WARNING: One type dominates >95% of database")

    return type_counts


def check_name_patterns(df):
    """Check for suspicious name patterns."""
    print("\n" + "="*60)
    print("CHECK 5: NAME PATTERN ANALYSIS")
    print("="*60)

    # Check for non-Cyrillic characters in person names (should be rare)
    fedsfm_entities = df[df['type'] == 'террористы и экстремисты']

    if len(fedsfm_entities) > 0:
        print(f"Analyzing {len(fedsfm_entities)} FEDSFM entities...")

        # Check for Latin characters (might indicate data issues)
        has_latin = fedsfm_entities[fedsfm_entities['name'].str.contains('[A-Za-z]', regex=True)]
        if len(has_latin) > 0:
            print(f"   ℹ️  {len(has_latin)} entities contain Latin characters:")
            for idx, row in has_latin.head(5).iterrows():
                print(f"      - {row['name']}")
            if len(has_latin) > 5:
                print(f"      ... and {len(has_latin) - 5} more")
        else:
            print("   ✅ All FEDSFM entities use Cyrillic")

        # Check for numbers in names (might indicate data corruption)
        has_numbers = fedsfm_entities[fedsfm_entities['name'].str.contains('[0-9]', regex=True)]
        if len(has_numbers) > 0:
            print(f"\n   ⚠️  {len(has_numbers)} entities contain numbers:")
            for idx, row in has_numbers.head(5).iterrows():
                print(f"      - {row['name']}")
        else:
            print("   ✅ No numbers in FEDSFM entity names")

        # Check for proper name format (should have 2-3 words for persons)
        word_counts = fedsfm_entities['name'].str.split().str.len()
        single_word = word_counts[word_counts == 1]
        if len(single_word) > 0:
            print(f"\n   ℹ️  {len(single_word)} single-word entries (might be organizations):")
            sample = fedsfm_entities[fedsfm_entities['name'].str.split().str.len() == 1].head(5)
            for idx, row in sample.iterrows():
                print(f"      - {row['name']}")

        many_words = word_counts[word_counts > 4]
        if len(many_words) > 0:
            print(f"\n   ℹ️  {len(many_words)} entries with >4 words:")
            sample = fedsfm_entities[fedsfm_entities['name'].str.split().str.len() > 4].head(3)
            for idx, row in sample.iterrows():
                print(f"      - {row['name'][:80]}...")


def generate_report(df, duplicate_stats, integrity_issues):
    """Generate final validation report."""
    print("\n" + "="*60)
    print("VALIDATION REPORT SUMMARY")
    print("="*60)

    exact_dupes, normalized_dupes, id_dupes = duplicate_stats

    total_issues = exact_dupes + id_dupes + len(integrity_issues)

    print(f"\n📊 Database size: {len(df):,} entities")
    print(f"\n🔍 Issues found: {total_issues}")

    if exact_dupes > 0:
        print(f"   ❌ {exact_dupes} exact duplicate names")
    if normalized_dupes > 0:
        print(f"   ⚠️  {normalized_dupes} case-insensitive duplicates")
    if id_dupes > 0:
        print(f"   ❌ {id_dupes} duplicate IDs (CRITICAL)")

    for issue in integrity_issues:
        print(f"   ⚠️  {issue}")

    if total_issues == 0:
        print("\n✅ ✅ ✅ DATABASE VALIDATION PASSED! ✅ ✅ ✅")
        print("No critical errors found. Database is ready for production use.")
    elif id_dupes > 0 or exact_dupes > 0:
        print("\n❌ CRITICAL ERRORS FOUND - Database needs cleanup!")
    else:
        print("\n⚠️  Minor issues found - Review recommended but database is usable")

    print("\n" + "="*60)


def main():
    """Main validation workflow."""
    print("="*60)
    print("DATABASE VALIDATION SCRIPT")
    print("="*60)
    print()

    # Load data
    df = load_registry()

    # Run checks
    duplicate_stats = check_duplicates(df)
    integrity_issues = check_data_integrity(df)
    check_alias_quality(df)
    check_type_distribution(df)
    check_name_patterns(df)

    # Generate report
    generate_report(df, duplicate_stats, integrity_issues)


if __name__ == '__main__':
    main()
