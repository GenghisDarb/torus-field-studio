# O(2) / Z2 monodromy derivation

Write an O(2) transition as `(theta,s)`, with `s` in `{+1,-1}`, and freeze
`(theta,s)*(phi,t) = (theta + s phi mod 2pi, s t)`. On a complex coordinate,
`(theta,+1)` acts as `z -> exp(i theta) z`; `(theta,-1)` acts as
`z -> exp(i theta) conjugate(z)`. Edge transitions must be measured or supplied
by a declared chart/frame registration; an unannotated complex or vector field
does not identify them.

Under endpoint frame changes, edge transitions transform by the usual endpoint
gauge action and closed-loop monodromy changes by conjugacy. The determinant
product `s_loop` is conjugacy invariant. `s_loop=-1` is an orientation-reversing
loop and evaluates the first Stiefel-Whitney obstruction on that loop. For an
orientation-reversing conjugacy class, a raw rotation angle is not generally a
gauge-invariant scalar, so the parity bit is the robust result unless a stronger
gauge anchor is preregistered.

One reflection gives `s_loop=-1`; two give `+1`. The orientation double cover is
the cover associated with the kernel of this Z2 character: a reversing loop
closes only after two lifts. This says "twice the loop", not 28 samples and not
a universal physical period.
