# Contributing

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m build
```

Schema changes require matching CLI validation, tests, examples, and migration
notes. Do not weaken reference validation or silently broaden scope.
