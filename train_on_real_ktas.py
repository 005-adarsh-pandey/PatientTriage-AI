"""
train_on_real_ktas.py - Training pipeline adapted for real KTAS data.csv dataset
"""
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

def clean_and_train_ktas():
    print("=" * 65)
    print("  TRAINING ML MODEL ON REAL CLINICAL DATASET (data.csv - KTAS)")
    print("=" * 65)

    # 1. Read data.csv
    df = pd.read_csv("data.csv", sep=";", encoding="latin1")
    print(f"[*] Loaded data.csv: {df.shape[0]} patient encounters, {df.shape[1]} columns.")

    # 2. Data Cleaning & Feature Extraction
    # Clean numerical columns that might contain comma decimals or strings
    def clean_num(val, default=0.0):
        if pd.isna(val):
            return default
        try:
            return float(str(val).replace(',', '.').strip())
        except Exception:
            return default

    df['Age'] = df['Age'].apply(lambda x: clean_num(x, 40.0))
    df['Sex_code'] = df['Sex'].apply(lambda x: 1 if str(x) == '1' else 0) # 1=Male, 0=Female
    df['Arrival_mode_code'] = df['Arrival mode'].apply(lambda x: int(clean_num(x, 1)))
    df['Injury_code'] = df['Injury'].apply(lambda x: 1 if str(x) == '1' else 0) # 1=Injury, 0=Non-injury
    df['Mental_code'] = df['Mental'].apply(lambda x: int(clean_num(x, 1))) # 1=Alert, 2=Verbal, 3=Pain, 4=Unresponsive
    df['NRS_pain_clean'] = df['NRS_pain'].apply(lambda x: clean_num(x, 0.0))
    df['SBP_clean'] = df['SBP'].apply(lambda x: clean_num(x, 120.0))
    df['DBP_clean'] = df['DBP'].apply(lambda x: clean_num(x, 80.0))
    df['HR_clean'] = df['HR'].apply(lambda x: clean_num(x, 75.0))
    df['RR_clean'] = df['RR'].apply(lambda x: clean_num(x, 18.0))
    df['BT_clean'] = df['BT'].apply(lambda x: clean_num(x, 36.8))
    df['Saturation_clean'] = df['Saturation'].apply(lambda x: clean_num(x, 98.0))
    
    # Derived clinical features
    df['is_pediatric'] = (df['Age'] < 18).astype(int)
    df['is_geriatric'] = (df['Age'] >= 65).astype(int)
    df['is_hypoxic'] = (df['Saturation_clean'] < 92).astype(int)
    df['is_hypotensive'] = (df['SBP_clean'] < 90).astype(int)
    df['qsofa_score'] = ((df['RR_clean'] >= 22).astype(int) + (df['SBP_clean'] <= 100).astype(int) + (df['Mental_code'] > 1).astype(int)) * (df['Age'] >= 18).astype(int)
    df['pews_score'] = ((df['RR_clean'] > 30).astype(int) + (df['HR_clean'] > 130).astype(int) + (df['Saturation_clean'] < 95).astype(int)) * (df['Age'] < 18).astype(int)

    # Clean target
    df['KTAS_expert'] = df['KTAS_expert'].apply(lambda x: int(clean_num(x, 3)))
    df['is_admission'] = df['Disposition'].isin([2, 3, 4]).astype(int) # 2=Ward, 3=ICU, 4=Death

    feature_cols = [
        'Age', 'is_pediatric', 'is_geriatric', 'Sex_code', 'Arrival_mode_code',
        'Injury_code', 'Mental_code', 'NRS_pain_clean', 'SBP_clean', 'DBP_clean',
        'HR_clean', 'RR_clean', 'BT_clean', 'Saturation_clean', 'is_hypoxic',
        'is_hypotensive', 'qsofa_score', 'pews_score'
    ]

    X = df[feature_cols].values
    y = df['KTAS_expert'].values
    y_admit = df['is_admission'].values

    print(f"\n[*] Extracted Feature Matrix: {X.shape}")
    print(f"[*] Target Acuity Distribution (KTAS_expert 1 to 5):\n{pd.Series(y).value_counts().sort_index()}")

    # 3. Train Cost-Sensitive Random Forest
    class_weights = {1: 10.0, 2: 4.0, 3: 1.5, 4: 1.0, 5: 1.0}
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_split=4,
        class_weight=class_weights,
        random_state=42,
        n_jobs=-1
    )
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(rf, X, y, cv=cv, scoring='accuracy')
    print(f"\n[*] 5-Fold Cross Validation Accuracy: {cv_scores.mean()*100:.2f}% (±{cv_scores.std()*100:.2f}%)")

    rf.fit(X, y)
    y_pred = rf.predict(X)
    print("\n[*] Full Classification Report (Model Trained on Real KTAS Data):")
    print(classification_report(y, y_pred, digits=3, zero_division=0))

    # 4. Train Admission Gradient Boosting Classifier
    gb_admit = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.06,
        max_depth=4,
        random_state=42
    )
    gb_admit.fit(X, y_admit)
    admit_acc = accuracy_score(y_admit, gb_admit.predict(X))
    print(f"[*] Admission Prediction Model Accuracy: {admit_acc * 100:.2f}%")

    # 5. Feature Importances
    importances = pd.Series(rf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\n[*] Top Clinical Feature Importances:")
    for feat, imp in importances.items():
        print(f"  • {feat:<20}: {imp*100:.2f}%")

    # 6. Save Bundle
    bundle = {
        'triage_model': rf,
        'admission_model': gb_admit,
        'feature_cols': feature_cols,
        'dataset_name': 'data.csv (KTAS Real Clinical Dataset)'
    }
    joblib.dump(bundle, "trained_triage_models.joblib")
    print("\n[*] Successfully serialized trained models to 'trained_triage_models.joblib'!")
    print("=" * 65)

if __name__ == "__main__":
    clean_and_train_ktas()
