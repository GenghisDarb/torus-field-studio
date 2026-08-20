# v0.3.0 verification package

This package verifies the published geometry evidence and its custody boundary. It does not
authorize another scored held-out execution.

After installing the v0.3.0 wheel, extract this package and run:

```text
python verify.py
```

The verifier audits every included geometry TBX, checks the single-execution and independent-raw-
verification receipts, and enforces the nonbinary claim boundary. To independently recompute from
the deposited raw fields, download `ExperimentalDataset.zip` from DOI
`10.5281/zenodo.20794709`, verify SHA-256
`5819f9071c3b3b0b856934602b5e7b487852abe0e0a3a5b1b62eae17720d822f`, materialize it with the
included structure-only script, and run the included raw verifier. That operation is verification,
not a new scorer or claim adjudication.

Do not run the held-out production scorer again. The published outcome remains
`GEOMETRY_INDEXED_TLD_METHOD_NONBINARY_EVIDENCE_VECTOR_ONLY`, with `TLD_DERIVED` blocked and
external validation false.

