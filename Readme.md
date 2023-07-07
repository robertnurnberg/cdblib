# Library with wrapper functions for the chessdb.cn API

The library `cdblib.py` allows to conveniently use the API of the Chess Cloud Database [chessdb.cn](https://chessdb.cn/queryc_en/) (cdb), the largest online database of chess positions and openings, from within Python.

The library is heavily inspired by, and originally based on, Joost VandeVondele's 
[cdbexplore](https://github.com/vondele/cdbexplore). See also [below](#other) for other repositories relevant for the interaction with cdb.

## Purpose

Provide a simple library with wrapper functions for the API of cdb. All the wrapper functions will continuously query cdb until a satisfactory response has been received. The latest version of the library allows for concurrency.

## Usage

By way of example, five small application scripts are provided.

* [`cdbwalk`](#cdbwalk) - walk through cdb towards the leafs, extending existing lines
* [`pgn2cdb`](#pgn2cdb) - populate cdb with moves from games in a PGN
* [`fens2cdb`](#fens2cdb) - request evaluations from cdb for FENs stored in a file
* [`cdbpvpoll`](#cdbpvpoll) - monitor a position's PV on cdb over time
* [`cdbbulkpv`](#cdbbulkpv) - bulk-request PVs from cdb for positions stored in a file

## Installation

```shell
git clone https://github.com/robertnurnberg/cdblib && pip install -r cdblib/requirements.txt
```

---

### `cdbwalk`

A command line program to walk within the tree of cdb, starting either from a list of FENs or from the (opening) lines given in a PGN file, possibly extending each explored line within cdb by one ply.

```
usage: cdbwalk.py [-h] [-v] [--moveTemp MOVETEMP] [--backtrack BACKTRACK] [--depthLimit DEPTHLIMIT] [--TBwalk] [-u USER] [--forever] filename

A script that walks within the chessdb.cn tree, starting from FENs or lines in a PGN file. Based on the given parameters, the script selects a move in each node, walking towards the leafs. Once an unknown position is reached, it is queued for analysis and the walk terminates.

positional arguments:
  filename              PGN file if suffix is .pgn, o/w a text file with FENs

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase output with -v, -vv, -vvv etc. (default: 0)
  --moveTemp MOVETEMP   Temperature T for move selection: in each node of the tree the probability to pick a move m will be proportional to exp((score(m)-score(bestMove))/T). Here unscored moves get assigned the score of the currently worst move. If T is zero, then always select the best move. (default: 10)
  --backtrack BACKTRACK
                        The number of plies to walk back from the newly created leaf towards the root, queuing each position on the way for analysis. (default: 0)
  --depthLimit DEPTHLIMIT
                        The upper limit of plies the walk is allowed to last. (default: 200)
  --TBwalk              Continue the walk in 7men EGTB land. (default: False)
  -u USER, --user USER  Add this username to the http user-agent header (default: None)
  --forever             Run the script in an infinite loop. (default: False)
```

Sample usage and output:
```
> python cdbwalk.py TCEC_S24_sufi_book.pgn -v
Read 50 (opening) lines from file TCEC_S24_sufi_book.pgn.
Line 1/50: 1. e4 e5 2. d4 exd4 3. Qxd4 Nc6 4. Qe3 g6 5. Bd2 Bg7 6. Nc3 Nge7 (50cp) 7. O-O-O d6 8. Qe1 O-O 9. h4 h5 10. f3 b5 11. Bxb5 Nd4 12. g4 Nxb5 13. Nxb5 Rb8 14. Nc3 c5 15. Bg5 hxg4
Line 2/50: 1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. f3 e6 7. Be3 b5 8. Qd2 Bb7 9. g4 h6 10. O-O-O Nbd7 (104cp) 11. h4 b4 12. Na4 Qa5 13. b3 Nc5 14. a3 Qc7 15. axb4 Nxa4 16. bxa4 d5 17. e5 Nd7 18. f4 Nb6 19. Rh3 Nc4 20. Qc3 Qd7 21. Bxc4 Rc8 22. Ne2 Rxc4 23. Qxc4 dxc4 24. Rxd7 Kxd7 25. c3 f6 26. Bd4 Rg8 27. Kd2 Ba8 28. Ke3
.
.
.
Line 50/50: 1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+ 4. Bd2 a5 5. Qc2 d5 6. e3 O-O 7. Bd3 Nc6 8. a3 Bxd2+ 9. Nbxd2 Ne7 (106cp) 10. g4 c5 11. dxc5 Kh8 12. g5 Nd7 13. cxd5 exd5 14. h4 b6 15. c6 Nc5 16. Nd4 f6 17. h5 a4 18. O-O-O fxg5 19. h6 g6 20. Kb1 
Done processing TCEC_S24_sufi_book.pgn.

> date
Tue  2 May 10:22:59 CEST 2023
```

### `pgn2cdb`

A command line program to populate cdb with moves from games stored in a PGN
file, up to a desired depth. Note that this script is very slow, and much faster alternatives are available at [dubslow/NoobChessDBPy](https://github.com/dubslow/NoobChessDBPy).

```
usage: pgn2cdb.py [-h] [-v] [-d DEPTH] [-u USER] filename

A simple script to pass pgns to chessdb.cn.

positional arguments:
  filename              pgn file

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase output with -v, -vv, -vvv etc. (default: 0)
  -d DEPTH, --depth DEPTH
                        number of plies to be added to chessdb.cn (default: 30)
  -u USER, --user USER  username for the http user-agent header (default: None)
``` 

Sample usage and output:
```
> python pgn2cdb.py -d 1000 TCEC_Season_24_-_Superfinal.pgn -vv
Read 100 pgns from file TCEC_Season_24_-_Superfinal.pgn.
Starting to pass these to chessdb.cn to depth 1000 ...
  For pgn 100/100 read 111/1000 plies. Final pos has 7 pieces.
    Position at depth 111 is already in chessdb.cn, not yet connected to root.
    Queueing new positions from ply 110 ... 
    Queued new positions until ply 91.
    Queueing new positions from ply 87 ... 
    Queued new positions until ply 40.
    Position at depth 27 is connected to the root.
  For pgn 99/100 read 149/1000 plies. Final pos has 9 pieces.
    Position at depth 149 is checkmate or stalemate.
    Position at depth 148 is new to chessdb.cn.
    Queueing new positions from ply 148 ... 
    Queued new positions until ply 39.
    Position at depth 37 is connected to the root.
  .
  .
  .
  For pgn 1/100 read 179/1000 plies. Final pos has 7 pieces.
    Position at depth 179 is already in chessdb.cn, not yet connected to root.
    Position at depth 57 is connected to the root.
Done processing TCEC_Season_24_-_Superfinal.pgn to depth 1000.
87/100 final positions already in chessdb.cn. (87.00%)
Queued 1412 new positions to chessdb.cn. Local cache hit rate: 14/9190 = 0.15%.

> date
Fri 27 Apr 09:15:48 CEST 2023
```

```
> python pgn2cdb.py -d 40 Trompowsky2e6.pgn -vv 
Read 9436 pgns from file Trompowsky2e6.pgn.
Starting to pass these to chessdb.cn to depth 40 ...
  For pgn 9436/9436 read 40/40 plies. Final pos has 26 pieces.
    Position at depth 40 is new to chessdb.cn.
    Queueing new positions from ply 40 ...
    Queued new positions until ply 32.
    Position at depth 18 is connected to the root.
  For pgn 9435/9436 read 40/40 plies. Final pos has 22 pieces.
    Position at depth 40 is new to chessdb.cn.
    Queueing new positions from ply 40 ...
    Queued new positions until ply 31.
    Position at depth 23 is connected to the root.
  .
  .
  .
  For pgn 1/9436 read 40/40 plies. Final pos has 22 pieces.
    Position at depth 40 is new to chessdb.cn.
    Queueing new positions from ply 40 ...
    Queued new positions until ply 18.
    Position at depth 17 is connected to the root.
Done processing Trompowsky2e6.pgn to depth 40.
248/9436 final positions already in chessdb.cn. (2.63%)
Queued 172787 new positions to chessdb.cn. Local cache hit rate: 1168/190413 = 0.61%.

> date
Thu 27 Apr 15:53:13 CEST 2023
```

### `fens2cdb`

A command line program to bulk-request evaluations from cdb for all the FENs/EPDs stored within a file. 

```
usage: fens2cdb.py [-h] [--shortFormat] [--quiet] [-c CONCURRENCY] [-u USER] input [output]

A simple script to request evals from chessdb.cn for a list of FENs stored in a file. The script will add "; EVALSTRING;" to every line containing a FEN. Lines beginning with "#" are ignored, as well as any text after the first four fields of each FEN.

positional arguments:
  input          source filename with FENs (w/ or w/o move counters)
  output         optional destination filename (default: None)

options:
  -h, --help            show this help message and exit
  --shortFormat         EVALSTRING will be just a number, or an "M"-ply mate score, or "#" for checkmate, or "". (default: False)
  --quiet               Suppress all unnecessary output to the screen. (default: False)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -u USER, --user USER  Add this username to the http user-agent header (default: None)
``` 

Sample usage and output:
```
> python fens2cdb.py matetrack.epd > matetrack_cdbeval.epd
Loaded 6561 FENs ...
Started parsing the FENs with concurrency 16 ...
Done. Scored 6561 FENs in 142.6s.
```

### `cdbpvpoll`

A command line program to monitor dynamic changes in a position's PV on cdb.

```
usage: cdbpvpoll.py [-h] [--epd EPD] [-sleep SLEEP] [--san] [-u USER]

Monitor dynamic changes in a position's PV on chessdb.cn by polling it at regular intervals.

options:
  -h, --help            show this help message and exit
  --epd EPD             FEN/EPD of the position to monitor (default: rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq g3)
  --sleep SLEEP         time interval between polling requests in seconds (default: 3600)
  --san                 give PV in short algebraic notation (SAN) (default: False)
  -u USER, --user USER  username for the http user-agent header (default: None)
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
usage: cdbbulkpv.py [-h] [--san] [-c CONCURRENCY] [-u USER] [--forever] filename

A script that queries chessdb.cn for the PV of all positions in a file.

positional arguments:
  filename       PGN file if suffix is .pgn, o/w a text file with FENs

options:
  -h, --help            show this help message and exit
  --san                 For PGN files, give PVs in short algebraic notation (SAN). (default: False)
  -c CONCURRENCY, --concurrency CONCURRENCY
                        Maximum concurrency of requests to cdb. (default: 16)
  -u USER, --user USER  Add this username to the http user-agent header (default: None)
  --forever             Run the script in an infinite loop. (default: False)
```

Sample usage and output:
```
> python cdbbulkpv.py TCEC_S24_sufi_book.pgn --san
Read 50 (opening) lines from file /home/rn/python/cdb/TCEC_S24_sufi_book.pgn.
Started parsing the positions with concurrency 16 ...
1. e4 e5 2. d4 exd4 3. Qxd4 Nc6 4. Qe3 g6 5. Bd2 Bg7 6. Nc3 Nge7; cdb eval: 65; PV: 7. O-O-O d6 8. Nce2 Ng8 9. h4 h5 10. Nf4 Nf6 11. f3 Rb8 12. Bb5 a6 13. Bxc6+ bxc6 14. Bc3 Qe7 15. Nge2 Bb7 16. Rde1 c5 17. Qd2 Kf8 18. Kb1 Bc6 19. b3 Nd7 20. Nd5 Bxd5 21. exd5 Qd8 22. Qd3 Bxc3 23. Nxc3 Rb4 24. Re4 Nf6 25. Rxb4 cxb4 26. Ne4 Nxe4 27. Qxe4 a5 28. Qd4 Kg8 29. Qa7 Kg7 30. Qxa5 c5 31. Qxd8 Rxd8 
1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. f3 e6 7. Be3 b5 8. Qd2 Bb7 9. g4 h6 10. O-O-O Nbd7; cdb eval: 106; PV: 11. h4 Nb6 12. a3 Rc8 13. Be2 Nfd7 14. Kb1 Qc7 15. g5 hxg5 16. hxg5 Nc4 17. Bxc4 Rxh1 18. Rxh1 Qxc4 19. Bf2 Be7 20. Nb3 b4 21. axb4 Qxb4 22. Bd4 e5 23. Be3 Nf8 24. Rh8 a5 25. Rg8 a4 26. Nd5 Qxd2 27. Nxd2 Bd8 28. f4 g6 29. fxe5 dxe5 30. c3 Ba6 31. Kc2 Be2
.
.
.
1. Nf3 d5 2. c4 e6 3. d4 Nf6 4. Nc3 c6 5. Bg5 dxc4 6. e4 b5 7. a4 Bb4; cdb eval: 43; PV: 8. e5 h6 9. exf6 hxg5 10. fxg7 Rg8 11. g3 g4 12. Ne5 Qd5 13. Rg1 Qe4+ 14. Be2 Nd7 15. Nxg4 Bb7 16. Kf1 Bxc3 17. bxc3 O-O-O 18. Bf3 Qd3+ 19. Qxd3 cxd3 20. Ne3 Rxg7 21. Be4 d2 22. axb5 cxb5 23. Bxb7+ Kxb7 24. Ke2 f5 25. Rgd1 f4 26. gxf4 Rf7 27. Kf3 Nb6 28. Rxd2 Rdf8 29. f5 exf5 30. Rda2 Ra8 31. h4 a6 32. h5 Rh7 33. Rh1 Rah8 34. Rg1 Na4 35. Ra3 Rxh5 36. Rg7+ Kb8 37. Rf7 R8h7 38. Rf6 Kb7 39. Ke2 Rh3 40. Rxf5 Nb6 41. Rf6 R3h6 42. Rf5 Rh5 43. Rf4 Rh4 44. Rf5 R4h5 
1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+ 4. Bd2 a5 5. Qc2 d5 6. e3 O-O 7. Bd3 Nc6 8. a3 Bxd2+ 9. Nbxd2 Ne7; cdb eval: 94; PV: 10. g4 g6 11. g5 Nd7 12. h4 c5 13. h5 cxd4 14. exd4 b6 15. O-O-O Ba6 16. Rh3 Kg7 17. Rdh1 Rg8 18. Nh2 Rc8 19. Kb1 Kf8 
Done. Polled 50 positions in 9.3s.

> date
Fri  7 Jul 22:00:03 CEST 2023
```

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
---
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
