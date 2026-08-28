"""
inspect_and_compare.py - Compares raw_patient_visits.csv and data.csv with encoding auto-detection
"""
import pandas as pd
import numpy as np

def load_with_encoding(filepath):
    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-8-sig']
    for enc in encodings:
        try:
            df = pd.read_csv(filepath, encoding=enc)
            print(f"Successfully loaded {filepath} using '{enc}' encoding.")
            return df, enc
        except Exception as e:
            continue
    raise ValueError(f"Could not load {filepath} with tested encodings.")

def analyze():
    print("=" * 60)
    print("  DETAILED DATASET COMPARISON: data.csv vs raw_patient_visits.csv")
    print("=" * 60)

    # 1. Load data.csv
    df_new, enc_new = load_with_encoding("data.csv")
    print(f"\n[1] data.csv (New Dataset):")
    print(f"  • Shape: {df_new.shape[0]} rows, {df_new.shape[1]} columns")
    print(f"  • Columns: {list(df_new.columns)}")
    print(f"  • Non-null counts per column:\n{df_new.notnull().sum()}")
    print(f"\n  • Sample Head (3 rows):\n{df_new.head(3)}")
    print(f"\n  • Summary Description:\n{df_new.describe(include='all')}")

    print("\n" + "-" * 60 + "\n")

    # 2. Load raw_patient_visits.csv
    df_old, enc_old = load_with_encoding("raw_patient_visits.csv")
    print(f"\n[2] raw_patient_visits.csv (Previous Dataset):")
    print(f"  • Shape: {df_old.shape[0]} rows, {df_old.shape[1]} columns")
    print(f"  • Columns: {list(df_old.columns)}")
    print(f"  • Non-null counts per column:\n{df_old.notnull().sum()}")
    print(f"\n  • Sample Head (3 rows):\n{df_old.head(3)}")
    print(f"\n  • Summary Description:\n{df_old.describe(include='all')}")

if __name__ == "__main__":
    analyze()
