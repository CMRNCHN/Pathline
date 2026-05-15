# Performance Baseline

Baseline measurements captured by `benchmarks/baseline_report.py`. These numbers describe **current** behaviour; they are *not* performance constraints. Use them as the reference point when evaluating future optimisation work.

## Run Metadata

- Captured at: `2026-05-15T15:30:09.842038+00:00`
- Python: `3.11.15`
- Platform: `Linux-6.18.5-x86_64-with-glibc2.39`

## Target Thresholds

| Operation | Threshold |
| --- | --- |
| replay_seek | < 200 ms (P95) |
| event_stream_load | < 200 ms (P95) |
| snapshot_load | < 100 ms (P95) |
| export_* | < 500 ms (P95) |

## Measurements

| Operation | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Samples | Threshold (ms) | Status | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | --- |
| replay_seek (100-event session) | 0.47 | 0.70 | 0.73 | 0.49 | 10 | 200 | OK | 100 events, 10 seeks |
| event_stream_load (raw JSONL) | 0.31 | 0.33 | 0.33 | 0.30 | 5 | 200 | OK | 100 events, 5 iterations |
| snapshot_load (5 sessions) | 0.61 | 0.75 | 0.77 | 0.61 | 5 | 100 | OK | 5 sessions reconstructed |
| snapshot_create | 0.03 | 0.04 | 0.05 | 0.03 | 5 | 100 | OK | in-memory copy of ReplayState |
| snapshot_persist (json dump) | 1.34 | 1.66 | 1.67 | 1.44 | 5 | 100 | OK | indented JSON to tmp disk |
| export_json | 0.34 | 0.37 | 0.40 | 0.34 | 25 | 500 | OK | graph_nodes=14, iters=25 |
| export_mermaid | 0.01 | 0.02 | 0.03 | 0.02 | 25 | 500 | OK | graph_nodes=14, iters=25 |
| export_markdown | 0.03 | 0.04 | 0.05 | 0.03 | 25 | 500 | OK | graph_nodes=14, iters=25 |

## Threshold Violations

None — every measured P95 is within target.

## Hot Functions (cProfile, cumulative time)

Snapshots of the heaviest call sites from one representative run of each profiled operation. Cumulative time is wall-clock time spent in the function *including* callees.

### replay_seek

- duration: 1.71 ms, calls: 3183

| Function | Cumulative (ms) | Total (ms) | Calls |
| --- | ---: | ---: | ---: |
| `benchmarks/profile_replay.py:71:<lambda>` | 1.68 | 0.01 | 1 |
| `ivr_assessor/events/replay_service.py:50:load_replay` | 1.67 | 0.06 | 1 |
| `ivr_assessor/events/replay_reducer.py:27:apply_event` | 0.77 | 0.39 | 99 |
| `ivr_assessor/events/replay_loader.py:43:get_timeline` | 0.72 | 0.01 | 1 |
| `ivr_assessor/events/replay_loader.py:15:load_events` | 0.63 | 0.10 | 1 |
| `json/__init__.py:299:loads` | 0.49 | 0.07 | 100 |
| `json/decoder.py:332:decode` | 0.39 | 0.13 | 100 |
| `ivr_assessor/events/replay_reducer.py:9:parse_timestamp` | 0.31 | 0.23 | 198 |

### snapshot_load

- duration: 1.02 ms, calls: 1408

| Function | Cumulative (ms) | Total (ms) | Calls |
| --- | ---: | ---: | ---: |
| `benchmarks/profile_snapshots.py:110:<lambda>` | 1.01 | 0.01 | 1 |
| `ivr_assessor/events/replay_service.py:50:load_replay` | 0.99 | 0.01 | 1 |
| `json/__init__.py:299:loads` | 0.56 | 0.06 | 81 |
| `ivr_assessor/events/replay_loader.py:43:get_timeline` | 0.54 | 0.00 | 1 |
| `ivr_assessor/events/replay_loader.py:15:load_events` | 0.49 | 0.08 | 1 |
| `json/decoder.py:332:decode` | 0.48 | 0.10 | 81 |
| `ivr_assessor/events/replay_service.py:117:_get_best_snapshot` | 0.35 | 0.02 | 1 |
| `json/decoder.py:343:raw_decode` | 0.32 | 0.32 | 81 |

### export_json

- duration: 0.36 ms, calls: 9

| Function | Cumulative (ms) | Total (ms) | Calls |
| --- | ---: | ---: | ---: |
| `benchmarks/profile_exports.py:125:<lambda>` | 0.35 | 0.01 | 1 |
| `json/__init__.py:183:dumps` | 0.35 | 0.00 | 1 |
| `json/encoder.py:183:encode` | 0.34 | 0.01 | 1 |
| `json/encoder.py:205:iterencode` | 0.34 | 0.34 | 1 |
| `ivr_assessor/events/replay_state.py:27:as_dict` | 0.00 | 0.00 | 1 |
| `~:0:<built-in method builtins.isinstance>` | 0.00 | 0.00 | 2 |
| `~:0:<method 'disable' of '_lsprof.Profiler' objects>` | 0.00 | 0.00 | 1 |
| `~:0:<method 'join' of 'str' objects>` | 0.00 | 0.00 | 1 |

### export_mermaid

- duration: 0.06 ms, calls: 120

| Function | Cumulative (ms) | Total (ms) | Calls |
| --- | ---: | ---: | ---: |
| `benchmarks/profile_exports.py:129:<lambda>` | 0.06 | 0.01 | 1 |
| `ivr_assessor/map_store.py:134:export_mermaid` | 0.05 | 0.04 | 1 |
| `~:0:<method 'get' of 'dict' objects>` | 0.00 | 0.00 | 27 |
| `~:0:<method 'append' of 'list' objects>` | 0.00 | 0.00 | 27 |
| `~:0:<built-in method builtins.sorted>` | 0.00 | 0.00 | 3 |
| `~:0:<method 'replace' of 'str' objects>` | 0.00 | 0.00 | 28 |
| `~:0:<method 'items' of 'dict' objects>` | 0.00 | 0.00 | 16 |
| `~:0:<built-in method builtins.len>` | 0.00 | 0.00 | 14 |

### export_markdown

- duration: 0.16 ms, calls: 438

| Function | Cumulative (ms) | Total (ms) | Calls |
| --- | ---: | ---: | ---: |
| `benchmarks/profile_exports.py:133:<lambda>` | 0.16 | 0.01 | 1 |
| `ivr_assessor/map_store.py:157:export_markdown` | 0.15 | 0.06 | 1 |
| `ivr_assessor/map_store.py:134:export_mermaid` | 0.05 | 0.04 | 1 |
| `~:0:<built-in method builtins.sum>` | 0.01 | 0.00 | 1 |
| `~:0:<method 'append' of 'list' objects>` | 0.01 | 0.01 | 160 |
| `~:0:<method 'get' of 'dict' objects>` | 0.01 | 0.01 | 123 |
| `ivr_assessor/map_store.py:161:<genexpr>` | 0.01 | 0.01 | 15 |
| `~:0:<built-in method builtins.sorted>` | 0.01 | 0.01 | 17 |

## Reproducing

```sh
cd backend/python
python -m benchmarks.baseline_report
```

Individual modules — `benchmarks.profile_replay`, `benchmarks.profile_snapshots`, `benchmarks.profile_exports` — can be run directly for ad-hoc investigation.
