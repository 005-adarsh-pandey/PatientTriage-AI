"""
check_raw_file.py - Inspect raw bytes of data.csv
"""

with open("data.csv", "rb") as f:
    raw_head = f.read(500)
    print("Raw bytes of data.csv (first 500 bytes):")
    print(raw_head)
    print("\nAttempting decode with errors='replace':")
    print(raw_head.decode('utf-8', errors='replace')[:400])
