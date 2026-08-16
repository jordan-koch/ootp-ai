"""Marks `tests/fixtures` as a package.

Without this, mypy sees `synthetic.py` under two module names — bare `synthetic`
(because pytest's `prepend` import mode puts `tests/` on `sys.path`) and
`fixtures.synthetic` (how the test modules import it) — and fails the whole-tree run
with "Source file found twice under different module names".

`--explicit-package-bases` is not the alternative fix: it makes `src` resolve as the
installed package and produces a fresh crop of errors.
"""
