# Pre-confirmation input-codec correction

Attempt 1 stopped after four completed development cases when case 5 was
already covered by inherited weights. The residual `order_bits_hex` stores
little-endian bytes, not the conventional hexadecimal spelling of an integer.
The original sampler misread that encoding. No confirmation search ran.

The original freeze, manifest, runner and log are preserved. Version 2 changes
only the input decoder and associated fresh artifact paths. It cross-checks
every residual bit against the supplied boolean matrix using a strict
standard-library NPY reader. This checks data encoding, not mathematical
validity of the reported global union counts. The same seeded sampling rule,
case counts, search algorithm and budgets are retained. No attempt-1 gain
is counted. New claims use only version-2 reconstructed certificates.
