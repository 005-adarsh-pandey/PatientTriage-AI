"""
debug_benchmarks.py - Inspect each benchmark case prediction
"""
from test_cases import CLINICAL_BENCHMARK_CASES
from triage_engine import triage_engine

for c in CLINICAL_BENCHMARK_CASES:
    res = triage_engine.evaluate_triage(c)
    print(f"Case: {c['id']} | Title: {c['title']}")
    print(f"  Expected: Level {c['expected_level']} | Predicted: Level {res['final_level']} (Rule: {res['rule_level']}, ML: {res['ml_level']})")
    print(f"  Drivers: {res['clinical_drivers'][:2]}")
    print()
