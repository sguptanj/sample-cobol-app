#!/usr/bin/env python3

from pathlib import Path

Path("data").mkdir(exist_ok=True)

accounts = [
    ("1000000001", "Siddharth Gupta", 100000),
    ("1000000002", "Rahul Sharma", 150000),
    ("1000000003", "Amit Verma", 250000),
]

transactions = [
    ("1000000001", "C", 25000),
    ("1000000001", "D", 10000),
    ("1000000002", "D", 9999999),
    ("1000000002", "X", 1000),
    ("9999999999", "C", 5000),
    ("1000000002", "D", 60000),
]

with open("data/accounts.dat", "w") as f:
    for account, name, balance in accounts:
        f.write(f"{account:<10}{name:<20}{balance:09d}\n")

with open("data/transactions.dat", "w") as f:
    for account, transaction_type, amount in transactions:
        f.write(
            f"{account:<10}{transaction_type}{amount:09d}\n"
        )

print("Banking test data generated successfully.")
