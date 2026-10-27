# Assignment 4 - Implementation plan and tests

Items: **#5711 progress bars** (feature) and **#7070 LRCLIB synced lyrics discarded** (bug).
Issues: <https://github.com/beetbox/beets/issues/5711>, <https://github.com/beetbox/beets/issues/7070>

## Implementation plan

| | #7070 lyrics bug | #5711 progress bars |
| --- | --- | --- |
| Root cause / need | `LRCLyrics.verify_synced_lyrics` checks only `splitlines()[-1]`; a trailing blank line makes it `""`, so the synced text is dropped. | Long commands print nothing while they run. |
| Change | `rstrip()` the LRC before taking its last line (`beetsplug/lyrics.py`); `_format_synced` also `rstrip()`s so stored text has no trailing newline. | New stdlib-only `beets.ui.progress(iterable, desc, unit, total)` in `beets/ui/__init__.py`, used by `update`, `write`, `move`, `lyrics`. |
| Effort / risk | ~1 h. Low: one expression. | ~3 h. Medium: bar must not corrupt log/print output. |
| Decisions | Skipped the "duration tolerance" side-point from the issue: it changes matching behaviour and is a maintainer call. | No `enlighten` dependency (the open upstream PR #5692 adds one plus a lockfile change). Bar goes to **stderr**, only on a TTY, never on Windows, erased while the loop body runs so logs/prints appear above it. Importer pipeline (threaded) left out. |

---

## A. Customer acceptance tests (manual)

These can be run by anyone with the repository, Python and `uv`, on Linux or macOS.
No developer help is needed and no network is needed.

### Setup (once)

```bash
git clone https://github.com/uoguelph-engg4450/F26-Group13-beets.git
cd F26-Group13-beets
git checkout feature/progress-bars-and-lyrics-fix      # or main, once merged
uv sync --group test --extra lyrics

# Scratch library, kept outside the repo so no repo files are changed.
export WORK=$(mktemp -d)
export BEETSDIR=$WORK
mkdir -p $WORK/music $WORK/export
for i in $(seq 1 25); do cp test/rsrc/full.mp3 $WORK/music/t$i.mp3; done
cp test/rsrc/full.flac $WORK/music/f.flac
printf 'directory: %s/lib\nlibrary: %s/lib.db\nplugins: lyrics\n' $WORK $WORK > $WORK/config.yaml
uv run beet import -A -q $WORK/music        # -A: no network tagging
uv run beet ls | wc -l                       # must print 26
```

Tests AT-1 to AT-5 need an **interactive terminal** (a normal terminal window).
With only 26 items each command finishes quickly, so watch the last line as it runs.
For a longer run, use your own big library with `-p` (pretend, changes nothing).

### Test table

| ID | Covers | Preconditions | Steps | Expected result | Pass/Fail |
| --- | --- | --- | --- | --- | --- |
| AT-1 | #5711 `write` shows a bar | Setup done | 1. In a terminal run `uv run beet write -p` | A line such as `Writing \|#########-----------\| 12/26 items` updates at the bottom, counting up to `26/26`. Any per-item text prints above it. The bar line disappears at the end. | |
| AT-2 | #5711 no bar when output is not a terminal | Setup done | 1. Run `uv run beet write -p 2>$WORK/err.txt \| cat`<br>2. Run `grep -F "Writing |" $WORK/err.txt` | Step 2 prints nothing (exit code 1). `err.txt` holds no bar text and no `ESC[2K` control codes. | |
| AT-3 | #5711 `update` shows a bar and still applies changes | Setup done | 1. Change a tag on disk: `uv run python -c "import mediafile,glob; p=sorted(glob.glob('$WORK/lib/**/*.mp3',recursive=True))[0]; f=mediafile.MediaFile(p); f.title='Edited Title'; f.save()"`<br>2. Run `uv run beet update`<br>3. Run `uv run beet ls title:Edited` | Step 2 shows an `Updating \|...\| n/26 items` bar and prints the changed fields above it. Step 3 lists one item titled `Edited Title`. | |
| AT-4 | #5711 `move` shows a bar and still copies files | Setup done | 1. Run `uv run beet move -c -d $WORK/export`<br>2. Run `find $WORK/export -type f \| head` | Step 1 shows `Copying 26 items.` then a `Copying \|...\| n/26 items` bar reaching `26/26`. Step 2 lists copied audio files. | |
| AT-5 | #5711 `lyrics` shows a bar (offline) | Setup done | 1. Run `uv run beet lyrics -l` (`-l` = local only, no fetching) | A `Fetching lyrics \|...\| n/26 items` bar counts to `26/26` and no error is shown. | |
| AT-6 | #7070 synced lyrics ending in a blank line are kept | Setup done | 1. Run<br>`uv run python -c "from beetsplug.lyrics import LRCLyrics as L; print(repr(L.verify_synced_lyrics(149.0, '[00:17.23]I said hi\r\n[02:23.59]Feel it\r\n\r\n')))"` | Prints the LRC text `'[00:17.23]I said hi\r\n[02:23.59]Feel it'`. **Before the fix it printed `None`.** | |
| AT-7 | #7070 bad synced lyrics are still rejected | Setup done | 1. Run the AT-6 command with the lyrics `'\r\n  \n'`<br>2. Run it with the lyrics `'[02:23.59]x\r\n\r\n'` and duration `100.0` | Both print `None`. No exception or traceback. | |
| AT-8 | Regression: nothing else broke | Setup done | 1. Run `uv run pytest test -q` | Ends with `passed` and no failures (about 2700 tests, about 1 minute). | |

Clean-up: `rm -rf "$WORK"`; `unset BEETSDIR WORK`.

---

## B. Automated tests added (pytest)

Run all of them:
`uv run pytest test/ui/test_ui_init.py test/plugins/test_lyrics.py -k "Progress or TestLRCLib"`
(or simply `uv run pytest test`).

### #7070 - `test/plugins/test_lyrics.py`, `TestLRCLibLyrics.test_fetch_lyrics`

| Test case id | Proves |
| --- | --- |
| `synced with trailing blank lines` | An LRCLib record whose synced text ends in `\r\n\r\n` is returned as synced lyrics, with no trailing newline in the stored text. Fails without the fix. |
| `whitespace-only synced falls back to plain` | A synced field containing only blank lines does not crash (`IndexError` guard) and the plain lyrics are used instead. |

### #5711 - `test/ui/test_ui_init.py`, `TestProgress`

| Test | Proves |
| --- | --- |
| `test_yields_all_items_unchanged` | The helper returns exactly the items it was given, in order. |
| `test_draws_counts_and_erases_when_done` | The bar shows `0/2`, `1/2`, `2/2` with the right fill, and the last thing written erases the line. |
| `test_bar_is_erased_while_loop_body_runs` | While the caller's loop body runs (where it prints or logs) the bar is not on screen, so output is not garbled. |
| `test_unknown_total_shows_running_count` | For an iterator with no length the bar shows a running count (`2 items`) instead of a fraction. |
| `test_erased_when_loop_is_abandoned` | Breaking out of the loop early still erases the bar. |
| `test_silent_when_not_a_tty` | When stderr is not a terminal nothing is written, and items still pass through. |

### Known gaps

- No automated test that `update`, `write`, `move` and `lyrics` actually call the helper; AT-1, AT-3, AT-4 and AT-5 cover this by hand.
- The bar is disabled on Windows and has only been exercised on Linux.
