# Addons

Here is a collection of scripts that may be useful in connection with
`fens2cdb.py`, and in particular in uploading (large) collections of 
positions to cdb and to obtain their evaluations.

To avoid duplicate uploads, and to keep the individual uploads to a
reasonable size, the following workflow may be used to score all the 
positions in `popularpos.epd.gz` with the help of the already existing
`oracle1.epd.gz` and `oracle2.epd.gz` files that contain previously
uploaded positions with their cdb evaluations (as returned by
`fens2cdb.py`). After the three steps the file `popularpos_cdb.epd` will
contain all the EPDs with their cdb scores, as if `popularpos.epd.gz` was
directly fed through `fens2cdb.py` to cdb.

```
python fens_filter_overlap.py --noStats popularpos.epd.gz oracle1.epd.gz oracle2.epd.gz > new_popularpos.epd
jumbo_fens2cdb.sh -c 64 new_popularpos.epd >&log.txt &
score_fens_locally.py popularpos.epd.gz new_popularpos_cdb.epd oracle1.epd.gz oracle2.epd.gz > popularpos_cdb.epd
```

The three steps do the following:

1. `fens_filter_overlap.py` filters out of `popularpos.epd.gz` only those
   positions for which locally no cdb evaluation is available yet, and stores
   these positions in `new_popularpos.epd`.

2. `jumbo_fens2cdb.sh` splits the file `new_popularpos.epd` into chunks of
   100000 lines each and feeds those with concurrency 64 to cdb, via
   `fens2cdb.py`. Once all the chunks have been processed, their outputs 
   are merged into the file `new_popularpos_cdb.epd`.

3. `score_fens_locally.py` now obtains the cdb scores for _all_ the positions
   in `popularpos.epd.gz` from the locally available scores in
   `new_popularpos_cdb.epd`, `oracle1.epd.gz` and `oracle2.epd.gz` to produce
   the final `popularpos_cdb.epd`.

For very large `popularpos.epd.gz` the first step may require too much 
memory. Then a strategy is to first run 
`python fens_filter_overlap.py popularpos.epd.gz > popularpos_unique.epd` to
filter out any possible duplicates in `popularpos.epd.gz`, and then run in
place of the first step the command `python fens_filter_overlap.py --noStats --saveMemory popularpos_unique.epd oracle1.epd.gz oracle2.epd.gz > new_popularpos.epd`. If `popularpos.epd.gz` is known to only contain unique positions, then
just run the first command as stated, but with the additional switch `--saveMemory`.

## Visualization

In order to visualize the distribution of cdb evals and `min_ply` values in
a scored `foo_cdb.epd` file, the script `plot_fens_cdb_dist.py` may be used.
It will produce the two files `foo_cdb.png` and `foo_cdb_ply.png` with
bucket plots for the frequencies of the eval and ply values found in
`foo_cdb.epd`, where the latter means the distance of the positions to the
start position in plies.
