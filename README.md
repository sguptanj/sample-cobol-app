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

Position	Length	Field
1–10	10	Account number
11	1	Transaction type
12–20	9	Transaction amount

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
