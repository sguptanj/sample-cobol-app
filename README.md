# COBOL Banking Transaction Processing System

A sample legacy banking application developed using GnuCOBOL.

## Features

- Customer account management
- Credit and debit transaction processing
- Transaction validation
- Account balance verification
- Sequential file processing
- Batch transaction execution
- Transaction report generation
- Automated test cases

## Requirements

- Ubuntu Linux
- GnuCOBOL
- Python 3
- GNU Make

## Build

make build

## Generate sample data

make data

Sample data/transcation.dat
1000000001C000025000

## 💳 Transaction Record Layout (`data/transactions.dat`)

| Position Range | Length | Field Name | Raw Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| **1–10** | 10 | Account Number | `1000000001` | Unique customer account identifier |
| **11** | 1 | Transaction Type | `C` | Type of transaction (`C` for Credit, `D` for Debit) |
| **12–20** | 9 | Transaction Amount | `000025000` | Transaction value (with implied decimal places) |

### Example Record Breakdown
* **Raw Line:** `1000000001C000025000`
* **Parsed:** Account `1000000001` | Credit (`C`) | Amount: `25,000.00`
## Execute application

make run

## Run tests

make test

## Clean build

make clean

## Project Structure

- src: COBOL programs
- copybooks: Shared COBOL structures
- data: Banking input records
- scripts: Data generation utilities
- tests: Automated test cases
- build: Compiled binaries and generated reports
