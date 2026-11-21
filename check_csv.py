import csv
import os

counts = {}
with open("test_cases.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        exists = os.path.isfile(row["file"])
        print("OK     " if exists else "MISSING", row["file"], "|", row["category"])
        counts[row["category"]] = counts.get(row["category"], 0) + 1

print(counts)
