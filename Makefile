format:
	black --quiet cdbbulkpv.py cdblib.py cdbpvpoll.py cdbwalk.py fens2cdb.py pgn2cdb.py
	shfmt -w -i 4 addons/jumbo_fens2cdb.sh

all: format
