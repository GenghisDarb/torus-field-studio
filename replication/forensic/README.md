# v0.2.2 external forensic replication add-on

This add-on verifies the additive v0.2.2 forensic package without changing the immutable
v0.2.1 result. Start from a clean checkout of tag `v0.2.2`, install its wheel, place the
release assets in one directory, and run `verify.py --assets <directory>`.

The verifier checks the release checksum file, audits the forensic TBX with the installed
package, checks the exact v0.2.1 reproduction receipt, confirms the 30/30 independent critic
mutations, and rejects any promotion of `TLD_DERIVED` or `EXTERNALLY_VALIDATED`.

This package does not select a new domain, execute a revised method, or reinterpret the
post-hoc reverse-direction surface as preregistered evidence.
