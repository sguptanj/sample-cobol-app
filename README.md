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

## Transaction Types

The banking application supports the following transaction types:

| Transaction Type | Code | Description |
|---|---|---|
| Credit | `C` | Adds the specified amount to the customer's account balance. |
| Debit | `D` | Deducts the specified amount from the customer's account balance, subject to validation rules. |
| Invalid | `X` | Represents an unsupported transaction type and is rejected during validation. |

### Transaction Record Format

The application uses fixed-width transaction records with the following structure:

| Field | Position | Length |
|---|---:|---:|
| Account Number | 1–10 | 10 characters |
| Transaction Code | 11 | 1 character |
| Transaction Amount | 12–20 | 9 characters |

**Example transaction records:**

```text
1000000001C000025000
1000000001D000010000
1000000002D009999999
1000000002X000001000
```

### Transaction Validation

Each transaction is validated before processing:

- **Credit:** Validates the account and transaction details before adding the amount.
- **Debit:** Validates account balance, minimum balance requirements and transaction limits before deduction.
- **Invalid transaction:** Rejects unsupported transaction codes.
- **Account validation:** Rejects transactions for accounts that do not exist.

Rejected transactions are recorded with corresponding error codes in the transaction processing output.


## Transaction Error Codes

The banking application uses error codes to identify rejected transactions.

| Error Code | Description | Reason |
|---|---|---|
| `ERR-001` | Invalid Transaction Type | Unsupported transaction code provided |
| `ERR-003` | Invalid Account | Customer account does not exist |
| `ERR-004` | Insufficient Balance | Account does not have sufficient funds |
| `ERR-005` | Business Validation Failure | Transaction rejected by an additional business validation rule |

Rejected transactions are logged with their corresponding error codes for troubleshooting and audit purposes.



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
