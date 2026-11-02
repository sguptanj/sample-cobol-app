COBC = cobc
PYTHON = python3

SOURCES = \
	src/main.cob \
	src/validate-transaction.cob \
	src/validate-account.cob \
	src/check-transaction-limit.cob \
	src/calculate-service-fee.cob \
	src/update-account.cob

BINARY = build/banking-app

all: build

build:
	mkdir -p build logs
	touch logs/audit.log
	$(COBC) -x -I copybooks -o $(BINARY) $(SOURCES) -Q "-Wno-cpp"

data:
	$(PYTHON) scripts/create-sample-data.py

run: build data
	./$(BINARY)

test: build data
	./$(BINARY)
	bash tests/test.sh

clean:
	rm -f build/banking-app
	rm -f build/accounts-updated.dat
	rm -f build/transaction-report.txt
	rm -f logs/audit.log

.PHONY: all build data run test clean
