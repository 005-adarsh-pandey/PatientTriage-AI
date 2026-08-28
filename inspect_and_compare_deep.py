"""
inspect_and_compare_deep.py - Deep comparative analysis between data.csv (KTAS real clinical dataset) and raw_patient_visits.csv
"""
import pandas as pd
import numpy as np

def run_deep_comparison():
    print("=" * 70)
    print("  DEEP DATASET COMPARISON & STATISTICAL AUDIT")
    print("=" * 70)

    # 1. Load data.csv (KTAS Real Emergency Department Dataset)
    # Uses sep=';' and encoding='latin1' or 'cp1252'
    df_ktas = pd.read_csv("data.csv", sep=";", encoding="latin1")
    print(f"\n[1] NEW DATASET: data.csv (Real KTAS Emergency Department Dataset)")
    print(f"  • Total Patient Encounters (Rows): {len(df_ktas):,}")
    print(f"  • Total Attributes (Columns): {len(df_ktas.columns)}")
    print(f"  • Column Names: {list(df_ktas.columns)}")
    print(f"\n  • Sample 3 Rows:")
    print(df_ktas[['Age', 'Sex', 'Arrival mode', 'Injury', 'Chief_complain', 'Mental', 'NRS_pain', 'SBP', 'DBP', 'HR', 'RR', 'BT', 'Saturation', 'KTAS_expert', 'Disposition', 'Diagnosis in ED']].head(3))
    print(f"\n  • Triage Target (KTAS_expert) Distribution:")
    print(df_ktas['KTAS_expert'].value_counts().sort_index())
    print(f"\n  • Disposition (Outcome) Distribution:")
    print(df_ktas['Disposition'].value_counts().sort_index())
    print(f"\n  • Mental Status Distribution:")
    print(df_ktas['Mental'].value_counts().sort_index())
    print(f"\n  • Mistriage Rate in Human RNs (mistriage column):")
    print(df_ktas['mistriage'].value_counts(normalize=True))

    print("\n" + "=" * 70 + "\n")

    # 2. Load raw_patient_visits.csv (Previous Synthetic Dataset)
    df_prev = pd.read_csv("raw_patient_visits.csv")
    print(f"[2] PREVIOUS DATASET: raw_patient_visits.csv (Synthetic Kaggle Dataset)")
    print(f"  • Total Patient Encounters (Rows): {len(df_prev):,}")
    print(f"  • Total Attributes (Columns): {len(df_prev.columns)}")
    print(f"  • Column Names: {list(df_prev.columns)}")
    print(f"\n  • Sample 3 Rows:")
    print(df_prev.head(3))
    print(f"\n  • Urgency Level Distribution:")
    print(df_prev['urgency_level'].value_counts())

if __name__ == "__main__":
    run_deep_comparison()
