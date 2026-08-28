"""
train_model.py - Standalone Model Training & Evaluation Pipeline
Trains on the real clinical dataset (data.csv - KTAS) with full evaluation metrics.
"""

from train_on_real_ktas import clean_and_train_ktas

if __name__ == "__main__":
    clean_and_train_ktas()
