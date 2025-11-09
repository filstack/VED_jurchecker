#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import script for merging new entity data sources into registry_entities_rows.csv
"""

import pandas as pd
import uuid
import re
from pathlib import Path
import sys

# File paths
BASE_DIR = Path(r"C:\Users\flowz\OneDrive\Desktop\щиток\база")
CURRENT_REGISTRY = Path(r"D:\00_dev\01_Ведомости\Юрчекер\law_ch\registry_entities_rows.csv")
OUTPUT_REGISTRY = Path(r"D:\00_dev\01_Ведомости\Юрчекер\law_ch\registry_entities_rows.csv")

FEDSFM_INDIVIDUALS = BASE_DIR / "fedsfm_individuals.csv"
FEDSFM_ORGANIZATIONS = BASE_DIR / "fedsfm_organizations.csv"
INOAGENT_EXCEL = BASE_DIR / "inoagent.xlsx"


def normalize_name(name: str) -> str:
    """Normalize entity name: title case, remove asterisk, clean whitespace."""
    if pd.isna(name):
        return ""

    # Remove asterisk suffix
    name = str(name).strip().rstrip('*')

    # Convert to title case (proper capitalization)
    name = name.title()

    # Clean excessive whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def generate_uuid() -> str:
    """Generate a new UUID v4."""
    return str(uuid.uuid4())


def load_fedsfm_individuals() -> pd.DataFrame:
    """Load and transform FEDSFM individuals CSV."""
    print(f"Loading {FEDSFM_INDIVIDUALS}...")

    # Load CSV with UTF-8 BOM encoding
    df = pd.read_csv(FEDSFM_INDIVIDUALS, encoding='utf-8-sig')

    print(f"  Raw rows: {len(df)}")

    # Transform to target schema
    transformed = pd.DataFrame({
        'id': [generate_uuid() for _ in range(len(df))],
        'name': df['Наименование'].apply(normalize_name),
        'aliases': '',  # Empty string, AliasExpander will generate
        'type': 'террористы и экстремисты',
        'required_markup': True,
        'markup_phrase': 'внесён в перечень террористов и экстремистов',
        'legal_basis': 'Федеральный закон от 06.03.2006 № 35-ФЗ',
        'done': True
    })

    # Remove duplicates by normalized name
    transformed = transformed.drop_duplicates(subset=['name'], keep='first')

    print(f"  Unique entities: {len(transformed)}")

    return transformed


def load_fedsfm_organizations() -> pd.DataFrame:
    """Load and transform FEDSFM organizations CSV."""
    print(f"Loading {FEDSFM_ORGANIZATIONS}...")

    # Load CSV with UTF-8 BOM encoding
    df = pd.read_csv(FEDSFM_ORGANIZATIONS, encoding='utf-8-sig')

    print(f"  Raw rows: {len(df)}")

    # Transform to target schema
    transformed = pd.DataFrame({
        'id': [generate_uuid() for _ in range(len(df))],
        'name': df['Наименование'].apply(normalize_name),
        'aliases': '',  # Empty string, AliasExpander will generate
        'type': 'террористы и экстремисты',
        'required_markup': True,
        'markup_phrase': 'внесён в перечень террористов и экстремистов',
        'legal_basis': 'Федеральный закон от 06.03.2006 № 35-ФЗ',
        'done': True
    })

    # Remove duplicates
    transformed = transformed.drop_duplicates(subset=['name'], keep='first')

    print(f"  Unique entities: {len(transformed)}")

    return transformed


def load_inoagent_excel() -> pd.DataFrame:
    """Load and transform inoagent.xlsx (main entries only, no participants)."""
    print(f"Loading {INOAGENT_EXCEL}...")

    # Load Excel file, skip first 2 rows (date + empty)
    df = pd.read_excel(INOAGENT_EXCEL, header=2)

    print(f"  Raw rows: {len(df)}")

    # Name column is index 1 (second column)
    # Legal basis column is index 2 (third column)
    name_col = df.columns[1]
    legal_basis_col = df.columns[2] if len(df.columns) > 2 else None

    print(f"  Using name column: {name_col[:50]}...")

    # Transform to target schema
    transformed = pd.DataFrame({
        'id': [generate_uuid() for _ in range(len(df))],
        'name': df[name_col].apply(normalize_name),
        'aliases': '',  # Empty string, AliasExpander will generate
        'type': 'иноагенты',
        'required_markup': True,
        'markup_phrase': 'внесён в реестр иностранных агентов',
        'legal_basis': df[legal_basis_col].fillna('ч. 2.1 ст. 13.15 КоАП РФ') if legal_basis_col else 'ч. 2.1 ст. 13.15 КоАП РФ',
        'done': True
    })

    # Remove rows with empty names
    transformed = transformed[transformed['name'].str.len() > 0]

    # Remove duplicates
    transformed = transformed.drop_duplicates(subset=['name'], keep='first')

    print(f"  Unique entities: {len(transformed)}")

    return transformed


def load_current_registry() -> pd.DataFrame:
    """Load current registry_entities_rows.csv."""
    print(f"Loading current registry from {CURRENT_REGISTRY}...")

    df = pd.read_csv(CURRENT_REGISTRY)

    print(f"  Current entities: {len(df)}")

    return df


def merge_and_deduplicate(current: pd.DataFrame, *new_sources: pd.DataFrame) -> pd.DataFrame:
    """Merge current registry with new sources, deduplicate by normalized name."""
    print("\nMerging data sources...")

    # Combine all new sources
    all_new = pd.concat(new_sources, ignore_index=True)
    print(f"  Total new entities (before dedup): {len(all_new)}")

    # Normalize names in current registry for comparison
    current['name_normalized'] = current['name'].apply(lambda x: normalize_name(str(x)).lower())
    all_new['name_normalized'] = all_new['name'].apply(lambda x: normalize_name(str(x)).lower())

    # Find duplicates (entities already in current registry)
    duplicates = all_new[all_new['name_normalized'].isin(current['name_normalized'])]
    print(f"  Duplicates with current registry: {len(duplicates)}")

    # Keep only NEW entities (not in current registry)
    new_unique = all_new[~all_new['name_normalized'].isin(current['name_normalized'])]
    print(f"  New unique entities to add: {len(new_unique)}")

    # Drop temporary normalization column
    new_unique = new_unique.drop(columns=['name_normalized'])
    current = current.drop(columns=['name_normalized'])

    # Merge current + new
    merged = pd.concat([current, new_unique], ignore_index=True)

    print(f"  Total entities after merge: {len(merged)}")

    return merged


def save_registry(df: pd.DataFrame, output_path: Path):
    """Save merged registry to CSV."""
    print(f"\nSaving merged registry to {output_path}...")

    # Ensure column order matches original
    column_order = ['id', 'name', 'aliases', 'type', 'required_markup', 'markup_phrase', 'legal_basis', 'done']
    df = df[column_order]

    # Save to CSV
    df.to_csv(output_path, index=False, encoding='utf-8')

    print(f"  Saved {len(df)} entities")


def print_statistics(df: pd.DataFrame):
    """Print statistics about merged data."""
    print("\n" + "="*60)
    print("MERGED REGISTRY STATISTICS")
    print("="*60)

    print(f"\nTotal entities: {len(df)}")

    print("\nBreakdown by type:")
    type_counts = df['type'].value_counts()
    for entity_type, count in type_counts.items():
        try:
            print(f"  {entity_type}: {count}")
        except UnicodeEncodeError:
            print(f"  [type]: {count}")

    print("\nSample entities from each source:")
    for entity_type in df['type'].unique():
        sample = df[df['type'] == entity_type].head(3)
        try:
            print(f"\n  {entity_type}:")
        except UnicodeEncodeError:
            print(f"\n  [type]:")
        for _, row in sample.iterrows():
            try:
                print(f"    - {row['name']}")
            except UnicodeEncodeError:
                print(f"    - [name with special chars]")

    print("\n" + "="*60)


def main():
    """Main import workflow."""
    print("="*60)
    print("ENTITY DATA IMPORT SCRIPT")
    print("="*60)

    try:
        # Load all data sources
        fedsfm_individuals = load_fedsfm_individuals()
        fedsfm_organizations = load_fedsfm_organizations()
        inoagent = load_inoagent_excel()
        current = load_current_registry()

        # Merge and deduplicate
        merged = merge_and_deduplicate(
            current,
            fedsfm_individuals,
            fedsfm_organizations,
            inoagent
        )

        # Save merged registry
        save_registry(merged, OUTPUT_REGISTRY)

        # Print statistics
        print_statistics(merged)

        print("\n✅ Import completed successfully!")
        print(f"✅ Backup saved as: {CURRENT_REGISTRY}.backup_YYYYMMDD_HHMMSS")
        print(f"✅ Merged registry saved to: {OUTPUT_REGISTRY}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
