# Visual encoding

Classification precedes rendering. Raw computed cells carry their classification, eligibility,
source identity, and failure link before either 2D or 3D code receives them. Interpolation is
nearest or bilinear display-only sampling and never creates an observation or enters a metric.

The TLD I Notebook 13 view places registered alpha conditions on x and endpoint families on y. The
Notebook 14 and combined views place registered timeline position on x and trial on y. Color encodes
the stored classification. Cells after a trial's terminal event are visibly `UNRESOLVED`, marked
`observed=false`, and linked to `NOT_OBSERVED_AFTER_TERMINAL` failure records; they are not filled
from neighboring points.

The browser keeps the source DOI, historical-lane label, preregistration pass/fail count,
independent-verifier state, claim badge, raw point identity, and blockers visible. The historical
and synthetic engines never share an evidentiary label. The 3D surface is an alternate rendering of
the same stored classifications and cannot change them.
