# Migration Benchmark Corpus

This corpus is a fixed, benign workload for regression tests and local timing
comparisons. `cases.json` records each input's source family, upstream syntax
version, complexity class, operation, and expected output marker.

The version labels identify the syntax generation represented by each sample;
they do not certify every released runtime. The corpus deliberately includes
valid, complex, unsupported/fallback, and malformed-but-harmless inputs. Source
files are parsed or converted only; tests never execute the sample scripts or
apply generated infrastructure changes.

Keep the manifest and files stable when comparing performance. Add a new case
instead of changing an existing one when the workload must evolve.
