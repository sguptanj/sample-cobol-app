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

Field Name,Position Range,Length,Raw Value,Parsed Value / Description
Account Number,1–10,10,1000000001,Account ID 1000000001
Transaction Type,11,1,C,Credit (C) transaction
Transaction Amount,12–20,9,000025000,"25,000.00 (implied 2 decimal places)"

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
