"""Root pytest configuration.

`studio/tests.py` is an empty Django stub ("# Create your tests here.").
It shares the `studio.tests` name with our real `studio/tests/` package, which
makes pytest raise an import-file-mismatch during collection. Ignore the stub so
the full suite collects cleanly. We do not modify application code.
"""

collect_ignore = ["studio/tests.py"]
