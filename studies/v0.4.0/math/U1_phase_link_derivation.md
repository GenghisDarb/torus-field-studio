# U(1) phase-link derivation

Let nonzero complex samples be `z_i = rho_i exp(i theta_i)` on vertices of an
oriented graph. Define `q_ij = z_j conjugate(z_i) / |z_j conjugate(z_i)|`.
Under a local frame change `z_i -> exp(i chi_i) z_i`,
`q_ij -> exp(i(chi_j-chi_i)) q_ij`. The ordered product around a closed
plaquette cancels every endpoint gauge factor. However, because these links
are derived from vertex values alone, the same product telescopes identically
to one wherever every vertex is nonzero. Its principal `H_p` is therefore
algebraically trivial, not a nontrivial connection holonomy.

The discrete winding is `w_p = sum wrap(Arg(q_ij))/(2pi)`. Integer meaning
requires a nonzero continuous boundary field and adequate sampling; an edge
increment near the branch cut makes the discrete estimate instrument-limited.
It is invariant to a global phase offset, but an arbitrary vertex-wise U(1)
rephasing can change branch assignments. Nontrivial locally gauge-invariant
holonomy requires independently supplied connection links, not pure-gauge
links reconstructed only from `z`.
Plaquettes touching a zero, missing sample, or undeclared interpolation are
ineligible. A coordinate reflection reverses boundary orientation; complex
conjugation also reverses phase. The implementation must freeze whether either
or both actions define the representation.

This construction measures U(1) winding. It does not produce a parity bit,
nonorientability, 14-step law, 28-step law, or spinorial 4pi return.
