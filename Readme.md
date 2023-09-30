# Library with wrapper functions for the chessdb.cn API

The library `cdblib.py` allows to conveniently use the API of the Chess Cloud Database [chessdb.cn](https://chessdb.cn/queryc_en/) (cdb), the largest online database of chess positions and openings, from within Python.

The library is heavily inspired by, and originally based on, Joost VandeVondele's script
[cdbexplore](https://github.com/vondele/cdbexplore). See also [below](#other) for other repositories relevant for the interaction with cdb.

## Purpose

Provide a simple library with wrapper functions for the API of cdb. All the wrapper functions will continuously query cdb until a satisfactory response has been received.

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
usage: pgn2cdb.py [-h] [-v] [-d DEPTH] [-p PAINT] [-u USER] filename

A simple script to pass pgns to chessdb.cn.

positional arguments:
  filename              pgn file

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase output with -v, -vv, -vvv etc. (default: 0)
  -d DEPTH, --depth DEPTH
                        number of plies to be added to chessdb.cn (default: 30)
  -p PAINT, --paint PAINT
                        depth in plies to try to extend the root's connected component to in each line (default: 0)
  -u USER, --user USER  username for the http user-agent header (default: None)
``` 

Sample usage and output:
```
> python pgn2cdb.py -d 1000 TCEC_Season_24_-_Superfinal.pgn -vv
Read 100 pgns from file TCEC_Season_24_-_Superfinal.pgn.
Starting to pass these to chessdb.cn to depth 1000 ...
  For pgn 100/100 read 111/1000 plies. Final position has 7 pieces.
    Position at depth 111 is already in chessdb.cn, not yet connected to root.
    Queueing new positions from ply 110 ... 
    Queued new positions until ply 91.
    Queueing new positions from ply 87 ... 
    Queued new positions until ply 40.
    Position at depth 27 is connected to the root.
  For pgn 99/100 read 149/1000 plies. Final position has 9 pieces.
    Position at depth 149 is checkmate or stalemate.
    Position at depth 148 is new to chessdb.cn.
    Queueing new positions from ply 148 ... 
    Queued new positions until ply 39.
    Position at depth 37 is connected to the root.
  .
  .
  .
  For pgn 1/100 read 179/1000 plies. Final position has 7 pieces.
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
  For pgn 9436/9436 read 40/40 plies. Final position has 26 pieces.
    Position at depth 40 is new to chessdb.cn.
    Queueing new positions from ply 40 ...
    Queued new positions until ply 32.
    Position at depth 18 is connected to the root.
  For pgn 9435/9436 read 40/40 plies. Final position has 22 pieces.
    Position at depth 40 is new to chessdb.cn.
    Queueing new positions from ply 40 ...
    Queued new positions until ply 31.
    Position at depth 23 is connected to the root.
  .
  .
  .
  For pgn 1/9436 read 40/40 plies. Final position has 22 pieces.
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

A command line program to bulk-request evaluations from cdb for all the FENs/EPDs stored within a file. Note that this script is extremely slow for now, and much faster alternatives are available at [dubslow/NoobChessDBPy](https://github.com/dubslow/NoobChessDBPy).

```
usage: fens2cdb.py [-h] [--shortFormat] [--quiet] [-u USER] input [output]

A simple script to request evals from chessdb.cn for a list of FENs stored in a file. The script will add "; EVALSTRING;" to every line containing a FEN. Lines beginning with "#" are ignored, as well as any text after the first four fields of each FEN.

positional arguments:
  input          source filename with FENs (w/ or w/o move counters)
  output         optional destination filename (default: None)

options:
  -h, --help            show this help message and exit
  --shortFormat         EVALSTRING will be just a number, or an "M"-ply mate score, or "#" for checkmate, or "". (default: False)
  --quiet               Suppress all unnecessary output to the screen. (default: False)
  -u USER, --user USER  Add this username to the http user-agent header (default: None)
``` 

Sample usage and output:
```
> sed -i 's/ bm/; bm/' ChestUCI_23102018.epd
> python fens2cdb.py ChestUCI_23102018.epd > ChestUCI_23102018_cdbeval.epd
FENs loaded...
Done. Scored 6566 FENs in 2816.6s.
```

### `cdbpvpoll`

A command line program to monitor dynamic changes in a position's PV on cdb.

```
usage: cdbpvpoll.py [-h] [--epd EPD] [--stable] [-sleep SLEEP] [--san] [-u USER]

Monitor dynamic changes in a position's PV on chessdb.cn by polling it at regular intervals.

options:
  -h, --help            show this help message and exit
  --epd EPD             FEN/EPD of the position to monitor (default: rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq g3)
  --stable              pass "&stable=1" option to API (default: False)
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
usage: cdbbulkpv.py [-h] [--stable] [--san] [-u USER] [--forever] filename

A script that queries chessdb.cn for the PV of all positions in a file.

positional arguments:
  filename       PGN file if suffix is .pgn, o/w a text file with FENs

options:
  -h, --help            show this help message and exit
  --stable              pass "&stable=1" option to API (default: False)
  --san                 For PGN files, give PVs in short algebraic notation (SAN). (default: False)
  -u USER, --user USER  Add this username to the http user-agent header (default: None)
  --forever             Run the script in an infinite loop. (default: False)
```

Sample usage and output:
```
> python cdbbulkpv.py TCEC_S24_sufi_book.pgn --san
Read 50 (opening) lines from file TCEC_S24_sufi_book.pgn.
1. e4 e5 2. d4 exd4 3. Qxd4 Nc6 4. Qe3 g6 5. Bd2 Bg7 6. Nc3 Nge7; cdb eval: 69; PV: 7. O-O-O d6 8. Nce2 Ng8 9. h4 Nf6 10. f3 h5 11. Nf4 Ne5 12. Be2 Qe7 13. Ngh3 Bxh3 14. Rxh3 a5 15. Kb1 c6 16. Bc1 Rd8 17. Rhh1 Nfd7 18. Bd2 Nc5 19. Bxa5 Rd7 20. Bb6 Qf6 
1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. f3 e6 7. Be3 b5 8. Qd2 Bb7 9. g4 h6 10. O-O-O Nbd7; cdb eval: 109; PV: 11. h4 b4 12. Na4 Qa5 13. b3 Nc5 14. a3 Qc7 15. axb4 Nxa4 16. bxa4 d5 17. e5 Nd7 18. f4 Nb6 19. Rh3 Bc8 20. Bf2 Bd7 21. f5 Nc4 22. Qc3 Be7 23. Bxc4 Qxc4 24. Qxc4 dxc4 25. Rc3 Bxa4 26. fxe6 O-O 27. Ra3 Be8 28. exf7+ Rxf7 29. Be1 Rf4 30. Nf5 Bf8 31. Re3 a5 32. e6 axb4 33. e7 Bxe7 34. Nxe7+ Kh7 35. Kb1 Rxg4 36. Bxb4 Rb8 37. c3 Rxh4 38. Re5 Rh2 39. Kc1 Rb6 40. Rd6 Rb7 41. Rd2 Rh1+ 42. Rd1 Rh2 43. Rde1 Bh5 44. Nf5 Bg6 45. Nd4 Ra7 46. R5e2 Rh4 47. Kb2 Bd3 48. Rf2 g5 49. Bc5 Rb7+ 50. Ka3 Re4 51. Rxe4 Bxe4 52. Rf6 Bd3 53. Ka4 
.
.
.
1. d4 Nf6 2. c4 e6 3. Nf3 Bb4+ 4. Bd2 a5 5. Qc2 d5 6. e3 O-O 7. Bd3 Nc6 8. a3 Bxd2+ 9. Nbxd2 Ne7; cdb eval: 99; PV: 10. g4 g6 11. g5 Nd7 12. h4 c5 13. h5 cxd4 14. exd4 dxc4 15. Be4 Ra7 16. O-O-O b5 17. Rh3 f5 18. gxf6 Nxf6 19. hxg6 h5 20. Ng5 Ned5 21. Kb1 b4 22. Nxc4 bxa3 23. Nf7 Qc7 24. Rxa3 Bb7 25. f3 Rb8 26. Rc1 Ba6 27. Bxd5 Nxd5 28. Nce5 Qxc2+ 
Done processing TCEC_S24_sufi_book.pgn.

> date
Wed 23 Aug 11:18:55 CEST 2023
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
* [robertnurnberg/caissatrack](https://github.com/robertnurnberg/caissatrack) - track cdb's evaluations of the 100k most popular positions in
[Caissabase](http://www.caissabase.co.uk)
* [robertnurnberg/uhotrack](https://github.com/robertnurnberg/uhotrack) - track cdb's evaluations of the positions in the UHO books from
[sp-cc.de](https://www.sp-cc.de/uho_xxl_project.htm)
---
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
