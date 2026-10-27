# Assignment 4 - Implementation plan and customer acceptance tests

Items: **#5711 progress bars** (feature) and **#7070 LRCLIB synced lyrics discarded** (bug).
Issues: <https://github.com/beetbox/beets/issues/5711>, <https://github.com/beetbox/beets/issues/7070>

## Implementation plan

| | #7070 lyrics bug | #5711 progress bars |
| --- | --- | --- |
| Root cause / need | `LRCLyrics.verify_synced_lyrics` checks only `splitlines()[-1]`; a trailing blank line makes it `""`, so the synced text is dropped. | Long commands print nothing while they run. |
| Change | `rstrip()` the LRC before taking its last line (`beetsplug/lyrics.py`); `_format_synced` also `rstrip()`s so stored text has no trailing newline. | New stdlib-only `beets.ui.progress(iterable, desc, unit, total)` in `beets/ui/__init__.py`, used by `update`, `write`, `move`, `lyrics`. |
| Effort / risk | ~1 h. Low: one expression. | ~3 h. Medium: bar must not corrupt log/print output. |
| Decisions | Skipped the "duration tolerance" side-point from the issue: it changes matching behaviour and is a maintainer call. | No `enlighten` dependency (the open upstream PR #5692 adds one plus a lockfile change). Bar goes to **stderr**, only on a TTY, never on Windows, erased while the loop body runs so logs/prints appear above it. Importer pipeline (threaded) left out. |
| Tests | `test/plugins/test_lyrics.py` (2 new cases) | `test/ui/test_ui_init.py::TestProgress` (6 tests) |

## Customer acceptance tests

Setup (once): `git clone <group repo> && cd <repo> && git checkout <branch> && uv sync --group test --extra lyrics`,
then `export BEETSDIR=$(mktemp -d)` and put `directory: $BEETSDIR/lib` / `library: $BEETSDIR/lib.db` in `$BEETSDIR/config.yaml`.
Import two files: `uv run beet import -A -C test/rsrc/full.mp3 test/rsrc/full.flac`.

### AT-1 Progress bar shows on a terminal (#5711)
1. In an interactive terminal run `uv run beet write -f`.
2. **Expected:** a line `Writing |####------| n/2 items` updates at the bottom; per-item output prints above it; the bar disappears when done.

### AT-2 Progress bar is absent when output is not a terminal (#5711)
1. Run `uv run beet write -f 2>err.txt | cat`.
2. **Expected:** `err.txt` contains no `Writing |` text and no escape codes.

### AT-3 Other commands (#5711)
1. Run `uv run beet update` (after `touch`-ing a file), `uv run beet move -p`, `uv run beet move` and `uv run beet lyrics` in a terminal.
2. **Expected:** `Updating`, `Moving`/`Copying`, `Fetching lyrics` bars appear and nothing else about command behaviour changes.

### AT-4 Automated check (#5711)
1. Run `uv run pytest test/ui/test_ui_init.py -k Progress`.
2. **Expected:** 6 passed.

### AT-5 Synced lyrics ending in a blank line are kept (#7070)
1. Run:
   ```
   uv run python -c "from beetsplug.lyrics import LRCLyrics as L; lrc='[00:17.23]I said hi\r\n[02:23.59]Feel it\r\n\r\n'; print(repr(L.verify_synced_lyrics(149.0, lrc)))"
   ```
2. **Expected:** the LRC string is printed (before the fix: `None`).

### AT-6 Whitespace-only and over-long lyrics are still rejected (#7070)
1. Run the same with `lrc='\r\n  \n'` and with `149.0` replaced by `100.0`.
2. **Expected:** `None` both times, no exception.

### AT-7 Automated check (#7070)
1. Run `uv run pytest test/plugins/test_lyrics.py -k TestLRCLib`.
2. **Expected:** all pass, including `synced with trailing blank lines`.
