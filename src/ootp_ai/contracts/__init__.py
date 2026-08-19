"""The tracked declarations, and the two pure functions that read them.

`tables.toml` and `field_map.toml` are the single source for every table's grain, key
and coverage, and for what we believe about every landed field. `loader.py` parses and
*validates* them; `policy.py` decides what may reach a page.

Nothing here opens a game file or a database. Both modules are pure functions over a
declaration, which is what lets the guards that matter run in CI with no MySQL and no
save on disk.
"""
