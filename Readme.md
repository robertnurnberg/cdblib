# Library with wrapper functions for the chessdb.cn API

The library `cdblib.py` allows to conveniently use the API of the Chess Cloud Database [chessdb.cn](https://chessdb.cn/queryc_en/) (cdb), the largest online database of chess positions and openings, from within Python.

The library is heavily inspired by, and originally based on, Joost VandeVondele's 
[cdbexplore](https://github.com/vondele/cdbexplore). See also [below](#other) for other repositories relevant for the interaction with cdb.

## Purpose

Provide a simple library with wrapper functions for the API of cdb. All the wrapper functions will continuously query cdb until a satisfactory response has been received. The latest version of the library allows for concurrency. For the original, purely sequential library, see the [classical](https://github.com/robertnurnberg/cdblib/tree/classical) branch.

## Usage

By way of example, nine small application scripts are provided.

* [`cdbwalk`](#cdbwalk) - walk through cdb towards the leafs, extending existing lines
* [`pgn2cdb`](#pgn2cdb) - populate cdb with moves from games in a PGN, and monitoring their coverage on cdb
* [`bulkqueue2cdb`](#bulkqueue2cdb) - bulk queue positions from files to cdb
* [`fens2cdb`](#fens2cdb) - request evaluations from cdb for FENs stored in a file
* [`cdb2bmepd`](#cdb2bmepd) - request (clear) best moves from cdb for FENs stored in a file
* [`cdb2json`](#cdb2json) - request json data from cdb for FENs stored in a file
* [`cdbpvpoll`](#cdbpvpoll) - monitor a position's PV on cdb over time
* [`cdbbulkpv`](#cdbbulkpv) - bulk-request PVs from cdb for positions stored in a file
* [`cdb2uci`](#cdb2uci) - a simple UCI engine wrapper to interact with cdb

## Installation

```shell
git clone https://github.com/robertnurnberg/cdblib && pip install -r cdblib/requirements.txt
```

---

### `cdbwalk`

A command line program to walk within the tree of cdb, starting either from a list of FENs or from the (opening) lines given in a PGN file, possibly extending each explored line within cdb by one ply.

```
usage: cdbwalk.py [-h] [-v] [--moveTemp MOVETEMP] [--backtrack BACKTRACK] [--depthLimit DEPTHLIMIT] [--TBwalk] [-c CONCURRENCY] [-b BATCHSIZE] [-u USER] [-s] [-l LOOPS | --forever] filename

A script that walks within the chessdb.cn tree, starting from FENs or lines in a PGN file. Based on the given parameters, the script selects a move in each node, walking towards the leafs. Once an unknown position is reached, it is queued for analysis and the walk terminates.

positional arguments:
  filename              PGN file if suffix is .pgn(.gz), o/w a file with FENs.

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase output with -v, -vv, -vvv etc. (default: 0)
  --moveTemp MOVETEMP   Temperature T for move selection: in each node of the tree the probability to pick a move m will be proportional to exp((score(m)-score(bestMove))/T). Here unscored moves get assigned the score of the currently worst move. If T is zero, then always select the best move. (default: 10)
  --backtrack BACKTRACK
                        The number of plies to walk back from the newly created leaf towards the root, queuing each position on the way for analysis. (default: 0)
  --depthLimit DEPTHLIMIT
                        The upper limit of plies the walk is allowed to last. (default: 200)
  --TBwalk              Continue the walk in 7men EGTB land. (default: False)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -b BATCHSIZE, --batchSize BATCHSIZE
                        Number of positions processed in parallel. Small values guarantee more responsive output, large values give faster turnaround. (default: None)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
  -l LOOPS, --loops LOOPS
                        Run the script for N passes. (default: 1)
  --forever             Run the script in an infinite loop. (default: False)
```

Sample usage and output:
```
> python cdbwalk.py TCEC_S24_sufi_book.pgn -v
Read 50 (opening) lines from file TCEC_S24_sufi_book.pgn.
Started parsing the positions with concurrency 16 ...
Line 1/50: 1. e4 e5 2. d4 exd4 3. Qxd4 Nc6 4. Qe3 g6 5. Bd2 Bg7 6. Nc3 Nge7 (63cp) 7. Nf3 O-O 8. O-O-O d5 9. Qc5 b6 10. Qa3 d4 11. Bg5 Qd7 12. Bb5 a6 13. Bxe7 axb5 14. Qxa8 Nxe7 15. Nxd4 Bxd4 16. Nd5 Bg7 17. Nf6+ Bxf6 18. Rxd7 Bxd7 19. Qa3 Nc6 20. Rd1 Bg4 21. f3 Be6 22. f4 h5 23. h3 Bg7 24. Qf3 b4 25. e5 Ne7 26. g4 Bh6 27. Kb1 c6
Line 2/50: 1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. f3 e6 7. Be3 b5 8. Qd2 Bb7 9. g4 h6 10. O-O-O Nbd7 (109cp) 11. h4 Qa5 12. a3 b4 13. axb4 Qxb4 14. Qg2 Nc5 15. g5 Nfd7 16. Na2 Qa5 17. Kb1 hxg5
.
.
.
Line 50/50: 1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+ 4. Bd2 a5 5. Qc2 d5 6. e3 O-O 7. Bd3 Nc6 8. a3 Bxd2+ 9. Nbxd2 Ne7 (111cp) 10. g4 Kh8 11. g5 Nd7 12. h4 c5 13. Bxh7 cxd4 14. exd4 b5 15. cxb5 e5 16. dxe5 Bb7 17. h5 Rc8 18. Qb1 Qb6 19. Bf5 Qxb5
Done processing TCEC_S24_sufi_book.pgn in 34.8s.

> date
Sun 23 Jul 14:13:42 CEST 2023
```

### `pgn2cdb`

A command line program to populate cdb with moves from games stored in a PGN file, up to a desired depth. The script also provides information about the existing coverage of the lines on cdb.

```
usage: pgn2cdb.py [-h] [-v] [-d DEPTH] [-p PAINT] [-c CONCURRENCY] [-b BATCHSIZE] [-u USER] [-s] filename

A simple script to pass pgns to chessdb.cn.

positional arguments:
  filename              .pgn(.gz) file

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase output with -v, -vv, -vvv etc. (default: 0)
  -d DEPTH, --depth DEPTH
                        Number of plies to be added to chessdb.cn. (default: 30)
  -p PAINT, --paint PAINT
                        Depth in plies to try to extend the root's connected component to in each line. (default: 0)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -b BATCHSIZE, --batchSize BATCHSIZE
                        Number of FENs processed in parallel. Small values guarantee more responsive output, large values give faster turnaround. (default: None)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
``` 

Sample usage and output:
```
> python pgn2cdb.py -d 1000 -vv TCEC_Season_25_-_Entrance_League.pgn
Read 93 pgns from file TCEC_Season_25_-_Entrance_League.pgn.
Started to parse these to chessdb.cn to depth 1000 with concurrency 16 ...
  For pgn 93/93 read 143/1000 plies. Final position has 7 pieces.
    Position at depth 143 is already in chessdb.cn, not yet connected to root.
    Queueing new positions from ply 142 ... 
    Queued new positions until ply 24.
    Queueing new positions from ply 21 ... 
    Queued new positions until ply 21.
    Position at depth 16 is connected to the root.
  For pgn 92/93 read 184/1000 plies. Final position has 7 pieces.
    Position at depth 184 is already in chessdb.cn, not yet connected to root.
    Queueing new positions from ply 183 ... 
    Queued new positions until ply 29.
    Position at depth 28 is connected to the root.
  .
  .
  .
  For pgn 1/93 read 143/1000 plies. Final position has 15 pieces.
    Position at depth 143 is checkmate or stalemate.
    Position at depth 142 is new to chessdb.cn.
    Queueing new positions from ply 142 ... 
    Queued new positions until ply 96.
    Queueing new positions from ply 94 ... 
    Queued new positions until ply 36.
    Queueing new positions from ply 33 ... 
    Queued new positions until ply 33.
    Position at depth 28 is connected to the root.
Done processing TCEC_Season_25_-_Entrance_League.pgn to depth 1000 in 701.7s.
45/93 final positions already in chessdb.cn. (48.39%)
Queued 10056 new positions to chessdb.cn. Local cache hit rate: 188/10782 = 1.74%.

> date
Sat  5 Aug 19:32:36 CEST 2023
```

```
> python pgn2cdb.py -d 50 -vv Trompowsky2e6.pgn
Read 9436 pgns from file Trompowsky2e6.pgn.
Started to parse these to chessdb.cn to depth 50 with concurrency 16 ...
  For pgn 9436/9436 read 50/50 plies. Final position has 21 pieces.
    Position at depth 50 is new to chessdb.cn.
    Queueing new positions from ply 50 ... 
    Queued new positions until ply 42.
    Position at depth 33 is connected to the root.
  For pgn 9435/9436 read 50/50 plies. Final position has 20 pieces.
    Position at depth 50 is new to chessdb.cn.
    Queueing new positions from ply 50 ... 
    Queued new positions until ply 41.
    Position at depth 30 is connected to the root.
  .
  .
  .
  For pgn 1/9436 read 50/50 plies. Final position has 20 pieces.
    Position at depth 50 is new to chessdb.cn.
    Queueing new positions from ply 50 ... 
    Queued new positions until ply 42.
    Queueing new positions from ply 39 ... 
    Queued new positions until ply 39.
    Position at depth 38 is connected to the root.
Done processing Trompowsky2e6.pgn to depth 50 in 9234.5s.
763/9436 final positions already in chessdb.cn. (8.09%)
Queued 76852 new positions to chessdb.cn. Local cache hit rate: 449/221243 = 0.20%.

> date
Sat  5 Aug 23:11:51 CEST 2023
```

### `bulkqueue2cdb`

A command line program to queue positions from games in PGN files, or from extended EPDs, to cdb. In contrast to `pgn2cdb`, this script provides no information about existing coverage on cdb, and simply queues _all_ positions of interest for analysis on cdb.

```
usage: bulkqueue2cdb.py [-h] [-o OUTFILE] [-v] [--plyBegin PLYBEGIN] [--plyEnd PLYEND] [--pieceMin PIECEMIN] [--pieceMax PIECEMAX] [-c CONCURRENCY] [-u USER] [-s] filenames [filenames ...]

A script to queue positions from files to chessdb.cn.

positional arguments:
  filenames             Files that contain games/lines to be uploaded. Suffix .pgn(.gz) indicates PGN format, o/w a (.gz) text file with FENs/EPDs. The latter may use the extended "moves m1 m2 m3" syntax from cdb's API.

options:
  -h, --help            show this help message and exit
  -o OUTFILE, --outFile OUTFILE
                        Filename to write unique FENs to. (default: None)
  -v, --verbose         Increase output with -v, -vv, -vvv etc. (default: 0)
  --plyBegin PLYBEGIN   Ply in each line from which positions will be queued to cdb. A value of 0 corresponds to the starting FEN without any moves played. Negative values count from the back, as per the Python standard. (default: 0)
  --plyEnd PLYEND       Ply in each line until which positions will be queued to cdb. A value of None means including the final move of the line. (default: None)
  --pieceMin PIECEMIN   Only queue positions with at least this many pieces (cdb only stores positions with 8 pieces or more). (default: 8)
  --pieceMax PIECEMAX   Only queue positions with at most this many pieces. (default: 32)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
```

Sample usage and output:
```
> python bulkqueue2cdb.py Trompowsky2e6.pgn --plyBegin 51 --plyEnd 60 -c 32
Loading games from 1 file(s) ...
Loaded 9436 games from file Trompowsky2e6.pgn.
Loaded 66984 unique EPDs from file Trompowsky2e6.pgn.
Done. Parsed 9436 games/lines in 57.0s.
Found 66984 unique positions from 9436 games/lines in 1 file(s) to send to cdb.
Started parsing the FENs with concurrency 32 ...
Done. Queued 66984 FENs from 9436 games in 791.6s.
```

### `fens2cdb`

A command line program to bulk-request evaluations from cdb for all the FENs/EPDs stored within a file. 

```
usage: fens2cdb.py [-h] [--shortFormat] [--quiet] [-e] [-c CONCURRENCY] [-b BATCHSIZE] [-u USER] [-s] [--suppressLearning] input [output]

A simple script to request evals from chessdb.cn for a list of FENs stored in a file. The script will add "; EVALSTRING;" to every line containing a FEN. Lines beginning with "#" are ignored, as well as any text after the first four fields of each FEN.

positional arguments:
  input                 source filename with FENs (w/ or w/o move counters)
  output                optional destination filename (default: None)

options:
  -h, --help            show this help message and exit
  --shortFormat         EVALSTRING will be just a number, or an "M"-ply mate score, or "#" for checkmate, or "". (default: False)
  --quiet               Suppress all unnecessary output to the screen. (default: False)
  -e, --enqueue         -e queues unknown positions once, -ee until an eval comes back. (default: 0)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -b BATCHSIZE, --batchSize BATCHSIZE
                        Number of FENs processed in parallel. Small values guarantee more responsive output, large values give faster turnaround. (default: None)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
  --suppressLearning    Suppress cdb's automatic learning. (default: False)
``` 

Sample usage and output:
```
> python fens2cdb.py matetrack.epd > matetrack_cdbeval.epd
Read 6561 FENs from file matetrack.epd.
Started parsing the FENs with concurrency 16 ...
Done. Scored 6561 FENs in 142.6s.
```

For help with very large source files, see also [Addons](addons/Readme.md).

### `cdb2bmepd`

A command line program to bulk-request (clear) best moves from cdb for all the FENs/EPDs stored within a file. 

```
usage: cdb2bmepd.py [-h] [--gap GAP] [--drawGap DRAWGAP] [--quiet] [-c CONCURRENCY] [-b BATCHSIZE] [-u USER] [-s] input [output]

A simple script to request (clear) best moves from chessdb.cn for a list of FENs stored in a file. The script will output "{fen} bm {bm}; c0 {comment};" for every line containing a FEN with a clear best move on cdb. Lines beginning with "#" are ignored.

positional arguments:
  input                 source filename with FENs (w/ or w/o move counters)
  output                optional destination filename (default: None)

options:
  -h, --help            show this help message and exit
  --gap GAP             Necessary gap between best move and second best move. (default: 20)
  --drawGap DRAWGAP     Necessary gap between 0cp best move and second best move. (Default: max(GAP // 2, 1)) (default: None)
  --quiet               Suppress all unnecessary output to the screen. (default: False)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -b BATCHSIZE, --batchSize BATCHSIZE
                        Number of FENs processed in parallel. Small values guarantee more responsive output, large values give faster turnaround. (default: None)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
``` 

Sample usage and output:
```
> python cdb2bmepd.py -c 32 Grob_Test_Suite_2024-04-29.epd > Grob_Test_Suite_2024-04-29_bm.epd
Read 47300 FENs from file Grob_Test_Suite_2024-04-29.epd.
Started parsing the FENs with concurrency 32 ...
Done. Processed 47300 FENs in 718.2s.
Filtered 3627 positions with bm output.
```

### `cdb2json`

A command line program to bulk-request json data from cdb for all the FENs/EPDs stored within a file. 

```
usage: cdb2json.py [-h] [--retainAll] [--quiet] [-c CONCURRENCY] [-b BATCHSIZE] [-u USER] [-s] input [output]

A simple script to request json data from chessdb.cn for a list of FENs stored in a file.

positional arguments:
  input                 source filename with FENs (w/ or w/o move counters)
  output                optional destination filename (default: None)

options:
  -h, --help            show this help message and exit
  --retainAll           Store the full json data from cdb (by default only uci moves and their scores). (default: False)
  --quiet               Suppress all unnecessary output to the screen. (default: False)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -b BATCHSIZE, --batchSize BATCHSIZE
                        Number of FENs processed in parallel. Small values guarantee more responsive output, large values give faster turnaround. (default: None)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
``` 

Sample usage and output:
```
> python cdb2json.py -c 32 Grob_Test_Suite_2024-04-29_bm.epd > Grob_Test_Suite_2024-04-29_bm.json
Read 3627 FENs from file Grob_Test_Suite_2024-04-29_bm.epd.
Started parsing the FENs with concurrency 32 ...
Done. Processed 3627 FENs in 64.9s.
```

### `cdbpvpoll`

A command line program to monitor dynamic changes in a position's PV on cdb.

```
usage: cdbpvpoll.py [-h] [--epd EPD] [--stable] [-sleep SLEEP] [--san] [-u USER]
 [-s] 
Monitor dynamic changes in a position's PV on chessdb.cn by polling it at regular intervals.

options:
  -h, --help            show this help message and exit
  --epd EPD             FEN/EPD of the position to monitor. (default: rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq g3)
  --stable              Pass "&stable=1" option to the API. (default: False)
  --sleep SLEEP         Time interval between polling requests in seconds. (default: 3600)
  --san                 Give PV in short algebraic notation (SAN). (default: False)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
``` 

Sample usage and output:
```
> python cdbpvpoll.py
  2023-04-28T18:04:23.380757:  123cp -- d7d5 e2e3 e7e5 d2d4 b8c6 b1c3 c8e6 d4e5 c6e5 h2h3 h7h5 g1f3 e5f3 d1f3 h5g4 h3g4 e6g4 f3g2 h8h1 g2h1 g8f6 c1d2 d8d6 c3b5 d6b6 f2f3 a7a6 b5c3 g4f5 e1c1 e8c8 c1b1 c8b8 d2c1 f8b4 c3e2 d8e8 h1h4 b4e7 h4g3 g7g6 f1h3 f5h3 g3h3 e7c5 e2d4 b6d6 a2a4 d6e5 d1d3 e5h5 h3g2 h5h4 a4a5 c5b4 d3d1 h4h5 d4b3 e8h8 g2f1 h5h3 f1e2 b4d6 c1d2

  2023-04-28T19:04:23.983954:  126cp -- d7d5 e2e3 e7e5 d2d4 b8c6 b1c3 c8e6 d4e5 c6e5 h2h3 h7h5 g1f3 e5f3 d1f3 h5g4 h3g4 e6g4 f3g2 h8h1 g2h1 g8f6 c1d2 d8d6 c3b5 d6b6 f2f3 a7a6 b5c3 g4f5 e1c1 e8c8 c1b1 c8b8 d2c1 f8b4 c3e2 d8e8 h1h4 b4e7 h4g3 g7g6 f1h3 f5h3 g3h3 e7c5 e2d4 b6d6 a2a4 d6e5 d1d3 e5h5 h3g2 c5b6 d3d1 b8c8 d1h1 h5e5 h1h4 e5d6 c1d2 c8b8 g2h3 c7c5 d4b3 f6h5 h3g4 d6c6
```

### `cdbbulkpv`

A command line program to bulk-request from cdb the PVs of all the positions stored in a file.

```
usage: cdbbulkpv.py [-h] [--stable] [--san] [-c CONCURRENCY] [-b BATCHSIZE] [-u USER] [-s] [--forever] filename

A script that queries chessdb.cn for the PV of all positions in a file.

positional arguments:
  filename              PGN file if suffix is .pgn(.gz), o/w a file with FENs.

options:
  -h, --help            show this help message and exit
  --stable              Pass "&stable=1" option to the API. (default: False)
  --san                 For PGN files, give PVs in short algebraic notation (SAN). (default: False)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -b BATCHSIZE, --batchSize BATCHSIZE
                        Number of positions processed in parallel. Small values guarantee more responsive output, large values give faster turnaround. (default: None)
  -u USER, --user USER  Add this username to the http user-agent header. (default: None)
  -s, --suppressErrors  Suppress error messages from cdblib. (default: False)
  --forever             Run the script in an infinite loop. (default: False)
```

Sample usage and output:
```
> python cdbbulkpv.py TCEC_S24_sufi_book.pgn --san
Read 50 (opening) lines from file TCEC_S24_sufi_book.pgn.
Started parsing the positions with concurrency 16 ...
1. e4 e5 2. d4 exd4 3. Qxd4 Nc6 4. Qe3 g6 5. Bd2 Bg7 6. Nc3 Nge7 ; cdb eval: 65; PV: 7. O-O-O d6 8. Nce2 Ng8 9. h4 h5 10. Nf4 Nf6 11. f3 Rb8 12. Bb5 a6 13. Bxc6+ bxc6 14. Bc3 Qe7 15. Nge2 Bb7 16. Rde1 c5 17. Qd2 Kf8 18. Kb1 Bc6 19. b3 Nd7 20. Nd5 Bxd5 21. exd5 Qd8 22. Qd3 Bxc3 23. Nxc3 Rb4 24. Re4 Nf6 25. Rxb4 cxb4 26. Ne4 Nxe4 27. Qxe4 a5 28. Qd4 Kg8 29. Qa7 Kg7 30. Qxa5 c5 31. Qxd8 Rxd8 ;
1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. f3 e6 7. Be3 b5 8. Qd2 Bb7 9. g4 h6 10. O-O-O Nbd7 ; cdb eval: 106; PV: 11. h4 Nb6 12. a3 Rc8 13. Be2 Nfd7 14. Kb1 Qc7 15. g5 hxg5 16. hxg5 Nc4 17. Bxc4 Rxh1 18. Rxh1 Qxc4 19. Bf2 Be7 20. Nb3 b4 21. axb4 Qxb4 22. Bd4 e5 23. Be3 Nf8 24. Rh8 a5 25. Rg8 a4 26. Nd5 Qxd2 27. Nxd2 Bd8 28. f4 g6 29. fxe5 dxe5 30. c3 Ba6 31. Kc2 Be2 ;
.
.
.
1. Nf3 d5 2. c4 e6 3. d4 Nf6 4. Nc3 c6 5. Bg5 dxc4 6. e4 b5 7. a4 Bb4 ; cdb eval: 43; PV: 8. e5 h6 9. exf6 hxg5 10. fxg7 Rg8 11. g3 g4 12. Ne5 Qd5 13. Rg1 Qe4+ 14. Be2 Nd7 15. Nxg4 Bb7 16. Kf1 Bxc3 17. bxc3 O-O-O 18. Bf3 Qd3+ 19. Qxd3 cxd3 20. Ne3 Rxg7 21. Be4 d2 22. axb5 cxb5 23. Bxb7+ Kxb7 24. Ke2 f5 25. Rgd1 f4 26. gxf4 Rf7 27. Kf3 Nb6 28. Rxd2 Rdf8 29. f5 exf5 30. Rda2 Ra8 31. h4 a6 32. h5 Rh7 33. Rh1 Rah8 34. Rg1 Na4 35. Ra3 Rxh5 36. Rg7+ Kb8 37. Rf7 R8h7 38. Rf6 Kb7 39. Ke2 Rh3 40. Rxf5 Nb6 41. Rf6 R3h6 42. Rf5 Rh5 43. Rf4 Rh4 44. Rf5 R4h5 ;
1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+ 4. Bd2 a5 5. Qc2 d5 6. e3 O-O 7. Bd3 Nc6 8. a3 Bxd2+ 9. Nbxd2 Ne7 ; cdb eval: 94; PV: 10. g4 g6 11. g5 Nd7 12. h4 c5 13. h5 cxd4 14. exd4 b6 15. O-O-O Ba6 16. Rh3 Kg7 17. Rdh1 Rg8 18. Nh2 Rc8 19. Kb1 Kf8 ;
Done. Polled 50 positions in 9.3s.

> date
Fri  7 Jul 22:00:03 CEST 2023
```

### `cdb2uci`

A simple UCI engine wrapper to interact with cdb.
```
usage: cdb2uci.py [-h] [-e] [-c CONCURRENCY] [--epd EPD] [--MultiPV MULTIPV] [--QueryPV]

A simple UCI engine that only queries chessdb.cn. On successful probing of a position it will report depth 1, otherwise depth 0 and score cp 0. For go commands any limits (including time) will be ignored. The https://backscattering.de/chess/uci for details on the UCI protocol.

options:
  -h, --help            show this help message and exit
  -e, --enqueue         -e queues unknown positions once, -ee until an eval comes back. The latter may be desirable in engine vs engine matches. (default: 0)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. Values > 1 are meaningful only if QueryPV is True and MultiPV > 1. (default: 8)
  --epd EPD             Extended EPD of board on engine start-up. (default: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1)
  --MultiPV MULTIPV     Value of UCI option MultiPV on engine start-up. (default: 1)
  --QueryPV             Value of UCI option QueryPV on engine start-up. (default: False)
  --debug               Run in debug mode (with additional output). (default: False)
```

In Linux the actual executable for the engine can be created with e.g. `echo "#! /bin/bash\n\npython /path_to_cdblib/cdb2uci.py -c 1 -ee" > cdb2uci.sh && chmod +x cdb2uci.sh`. Such an executable can then be used within chess GUIs or in chess engine tournaments.


---
&nbsp;
# <a id="other"></a>Other repositories related to cdb

* [noobpwnftw/chessdb](https://github.com/noobpwnftw/chessdb) - the backend of [chessdb.cn](https://chessdb.cn/queryc_en/)
* [dav1312/ChessDB-Online-Book](https://github.com/dav1312/ChessDB-Online-Book) - backend for [ChessDB-Online-Book](https://dav1312.github.io/ChessDB-Online-Book/), a very nice GUI to interact with cdb
* [dubslow/NoobChessDBPy](https://github.com/dubslow/NoobChessDBPy) - extremely fast bulk-queries to cdb, including breadth-first traversal of the tree with filtering options
* [vondele/cdbexplore](https://github.com/vondele/cdbexplore) - search and explore cdb from a given position, building a local search tree using a mini-max like algorithm
* [vondele/chessgraph](https://github.com/vondele/chessgraph) - a utility to create a graph of moves from a specified position, using e.g. cdb
* [robertnurnberg/grobtrack](https://github.com/robertnurnberg/grobtrack) - monitor cdb's eval and PV for 1. g4 over time
* [robertnurnberg/cdbmatetrack](https://github.com/robertnurnberg/cdbmatetrack) - track cdb's progress on the problem suite from [matetrack](https://github.com/vondele/matetrack)
* [robertnurnberg/caissatrack](https://github.com/robertnurnberg/caissatrack) - track cdb's evaluations of the 100k most popular positions in
[Caissabase](http://www.caissabase.co.uk)
* [robertnurnberg/ecotrack](https://github.com/robertnurnberg/ecotrack) - track cdb's evaluations of the most common ECO openings
* [robertnurnberg/uhotrack](https://github.com/robertnurnberg/uhotrack) - track cdb's evaluations of the positions in the UHO Lichess book from
[official-stockfish/books](https://github.com/official-stockfish/books)
* [robertnurnberg/chopstrack](https://github.com/robertnurnberg/chopstrack) - track cdb's evaluations of the positions in the CHOPS (Complex Human OPeningS) book

### Repositories for offline access to cdb

* [vondele/cdbdirect](https://github.com/vondele/cdbdirect) - directly probe a local copy of a snapshot of cdb
* [vondele/cdbsubtree](https://github.com/vondele/cdbsubtree) - count the number of positions in a subtree of (a snapshot of) cdb
* [vondele/cdbtreesearch](https://github.com/vondele/cdbtreesearch) - softmax and mini-max searches in (a snapshot of) cdb
---
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
