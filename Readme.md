# Library with wrapper functions for the chessdb.cn API

Allows to conveniently use the API of the Chess Cloud Database (cdb), the largest online database of chess positions and openings, from within Python:

[chessdb](https://chessdb.cn/queryc_en/)

Heavily inspired by, and based on, Joost VandeVondele's script
[cdbexplore](https://github.com/vondele/cdbexplore).

## Purpose

Provide a simple library with wrapper functions for the API of cdb. All the wrapper functions will continuously query cdb until a satisfactory response has been received.

## Usage

By way of example, three small application scripts are provided.

* `pgn2cdb`

A command line program to populate cdb with moves from games stored in a PGN
file, up to a desired depth.

```
usage: pgn2cdb.py [-h] [-v] [-d DEPTH] filename

A simple script to pass pgns to chessdb.cn.

positional arguments:
  filename              pgn file

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase output with -v, -vv, -vvv etc. (default: 0)
  -d DEPTH, --depth DEPTH
                        number of plies to be added to chessdb.cn (default: 30)
``` 

* `fens2cdb`

A command line program to bulk-request evaluations from cdb for all the FENs/EPDs stored within a file.

```
usage: fens2cdb.py [-h] [--shortFormat] [--quiet] input [output]

A simple script to request evals from chessdb.cn for a list of FENs/EPDs stored in a file. The script will add "; EVALSTRING;" to every line containing a FEN. Lines beginning with "#" are ignored, as well as text after the first ";" on each line.

positional arguments:
  input          source filename with FENs/EPDs
  output         optional destination filename (default: None)

options:
  -h, --help     show this help message and exit
  --shortFormat  EVALSTRING is either just a number, or "#" for checkmate, or "". (default: False)
  --quiet        Suppress all unnecessary output to the screen. (default: False)
``` 

* `cdbpvpoll`

A command line program to monitor dynamic changes in a position's PV on cdb.

```
usage: cdbpvpoll.py [-h] [--epd EPD] [-sleep SLEEP] [--san]

Monitor dynamic changes in a position's PV on chessdb.cn by polling it at regular intervals.

options:
  -h, --help            show this help message and exit
  --epd EPD             FEN/EPD of the position to monitor (default: rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq g3)
  --sleep SLEEP         time interval between polling requests in seconds (default: 3600)
  --san                 give PV in short algebraic notation (SAN) (default: False)
``` 

