format:
	black --quiet cdbbulkpv.py cdblib.py cdbpvpoll.py cdbwalk.py fens2cdb.py pgn2cdb.py addons/fens_filter_overlap.py addons/plot_fens_cdb_dist.py addons/score_fens_locally.py
	shfmt -w -i 4 addons/jumbo_fens2cdb.sh
	shfmt -w -i 4 addons/meta_jumbo.sh

all: format
