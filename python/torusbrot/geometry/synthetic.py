from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import NDArray

from torusbrot.geometry.channels import coordinate_permutation_null

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SyntheticFixture:
    fixture_id: str
    title: str
    field_kind: str
    field: FloatArray
    ground_truth_structure: str
    binary_target_present: bool
    expected_direction: str
    expected_invariant_or_equivariant_behavior: str
    expected_valid_projections: tuple[str, ...]
    expected_invalid_projections: tuple[str, ...]
    compatible_nulls: tuple[str, ...]
    incompatible_nulls: tuple[str, ...]
    expected_operation_depth_semantics: str
    expected_scale_semantics: str
    expected_perturbation_fingerprint: str
    parent_model: str = "INDEPENDENT_SYNTHETIC_PARENTS"

    def registry_dict(self) -> dict[str, object]:
        value = asdict(self)
        value.pop("field")
        value["shape"] = list(self.field.shape)
        value["dtype"] = str(self.field.dtype)
        return value


def _grid(size: int = 32) -> tuple[FloatArray, FloatArray]:
    axis = np.linspace(-1.0, 1.0, size, dtype=np.float64)
    return np.meshgrid(axis, axis, indexing="xy")


def _smooth(field: FloatArray, rounds: int = 4) -> FloatArray:
    result = np.asarray(field, dtype=np.float64).copy()
    for _ in range(rounds):
        result = (
            result
            + np.roll(result, 1, axis=0)
            + np.roll(result, -1, axis=0)
            + np.roll(result, 1, axis=1)
            + np.roll(result, -1, axis=1)
        ) / 5.0
    return result


def _vortex(x: FloatArray, y: FloatArray, x0: float = 0.0, sign: float = 1.0) -> FloatArray:
    dx = x - x0
    radius2 = dx * dx + y * y + 0.02
    envelope = np.exp(-2.0 * radius2)
    return np.stack((-sign * y * envelope / radius2, sign * dx * envelope / radius2), axis=-1)


def _phase_randomize(field: FloatArray, rng: np.random.Generator) -> FloatArray:
    spectrum = np.fft.rfft2(field)
    phases = rng.uniform(-np.pi, np.pi, spectrum.shape)
    phases[0, 0] = np.angle(spectrum[0, 0])
    surrogate = np.abs(spectrum) * np.exp(1j * phases)
    return np.fft.irfft2(surrogate, s=field.shape).real


def _ring_graph(nodes: int = 24) -> FloatArray:
    graph = np.zeros((nodes, nodes), dtype=np.float64)
    for index in range(nodes):
        for offset in (1, 2):
            other = (index + offset) % nodes
            graph[index, other] = graph[other, index] = 1.0
    return graph


def _random_graph_same_edges(graph: FloatArray, rng: np.random.Generator) -> FloatArray:
    edges = int(np.sum(graph) // 2)
    pairs = np.asarray(np.triu_indices(len(graph), 1)).T
    selected = rng.choice(len(pairs), size=edges, replace=False)
    result = np.zeros_like(graph)
    for left, right in pairs[selected]:
        result[left, right] = result[right, left] = 1.0
    return result


def build_synthetic_fixtures(seed: int = 300) -> list[SyntheticFixture]:
    rng = np.random.default_rng(seed)
    x, y = _grid()
    radius = np.sqrt(x * x + y * y)
    iid = rng.normal(size=x.shape)
    colored = _smooth(rng.normal(size=x.shape), 6)
    isotropic_wave = np.cos(8.0 * np.pi * radius) * np.exp(-0.7 * radius)
    anisotropic_wave = np.sin(7.0 * np.pi * x + 2.0 * np.pi * y)
    single_vortex = _vortex(x, y)
    vortex_pair = _vortex(x, y, -0.35, 1.0) + _vortex(x, y, 0.35, -1.0)
    shedding = np.stack(
        (
            np.sin(4.0 * np.pi * x) * np.cos(2.0 * np.pi * y),
            -np.cos(4.0 * np.pi * x) * np.sin(2.0 * np.pi * y),
        ),
        axis=-1,
    )
    diffusive = _smooth(np.exp(-10.0 * ((x + 0.25) ** 2 + (y - 0.1) ** 2)), 8)
    wave_equation = np.sin(5.0 * np.pi * x) * np.cos(5.0 * np.pi * y)
    coupled = np.stack(
        (np.sin(4.0 * np.pi * x) * np.cos(2.0 * np.pi * y), np.cos(4.0 * np.pi * x + 0.7)),
        axis=-1,
    )
    bursts = np.zeros_like(x)
    for center_x, center_y, amplitude in ((-0.5, -0.2, 1.0), (0.1, 0.4, 0.8), (0.55, -0.45, 1.2)):
        bursts += amplitude * np.exp(-35.0 * ((x - center_x) ** 2 + (y - center_y) ** 2))
    ar2 = np.zeros(32, dtype=np.float64)
    innovations = rng.normal(scale=0.2, size=32)
    for index in range(2, 32):
        ar2[index] = 1.4 * ar2[index - 1] - 0.65 * ar2[index - 2] + innovations[index]
    ar2_space = np.asarray([np.roll(ar2, offset // 4) for offset in range(32)])
    common = np.sin(np.linspace(0.0, 8.0 * np.pi, 32))
    loadings = np.linspace(0.5, 1.5, 32)[:, None]
    common_factor = loadings * common[None, :] + rng.normal(scale=0.08, size=(32, 32))
    independent_parent = anisotropic_wave + rng.normal(scale=0.12, size=x.shape)
    nested_replicate = isotropic_wave + _smooth(rng.normal(scale=0.15, size=x.shape), 2)
    homology_ring = np.exp(-80.0 * (radius - 0.55) ** 2)
    target_graph = _ring_graph()
    null_graph = _random_graph_same_edges(target_graph, rng)
    rotated = np.rot90(anisotropic_wave)
    downsampled = anisotropic_wave[::2, ::2].repeat(2, axis=0).repeat(2, axis=1)
    phase_randomized = _phase_randomize(anisotropic_wave, rng)
    truncated = np.pad(anisotropic_wave[4:-4, 4:-4], 4, mode="constant")
    missing = anisotropic_wave.copy()
    missing_mask = rng.random(missing.shape) < 0.12
    missing[missing_mask] = float(np.mean(missing[~missing_mask]))
    degraded = anisotropic_wave[::4, ::4].repeat(4, axis=0).repeat(4, axis=1)
    checkerboard = (-1.0) ** (np.indices(x.shape).sum(axis=0))

    def fixture(
        number: int,
        title: str,
        kind: str,
        field: FloatArray,
        truth: str,
        present: bool,
        direction: str = "UPPER",
        behavior: str = "coordinate rotations preserve calibrated effect direction",
        valid: tuple[str, ...] = ("neighbor_coherence", "spectral_concentration"),
        invalid: tuple[str, ...] = ("unregistered_flattening",),
        compatible: tuple[str, ...] = ("coordinate_permutation",),
        incompatible: tuple[str, ...] = ("constant_replacement",),
        fingerprint: str = (
            "order shuffle strong; noise graded; rotation invariant; resolution graded"
        ),
    ) -> SyntheticFixture:
        return SyntheticFixture(
            fixture_id=f"SYN-{number:02d}",
            title=title,
            field_kind=kind,
            field=np.asarray(field, dtype=np.float64),
            ground_truth_structure=truth,
            binary_target_present=present,
            expected_direction=direction,
            expected_invariant_or_equivariant_behavior=behavior,
            expected_valid_projections=valid,
            expected_invalid_projections=invalid,
            compatible_nulls=compatible,
            incompatible_nulls=incompatible,
            expected_operation_depth_semantics="NOT_APPLICABLE_NO_RECURSIVE_OPERATOR",
            expected_scale_semantics="APPLICABLE_GEOMETRIC_OR_MODAL_SCALE",
            expected_perturbation_fingerprint=fingerprint,
        )

    return [
        fixture(
            1, "IID scalar field", "SCALAR_FIELD_2D", iid, "exchangeable null field", False, "NONE"
        ),
        fixture(
            2,
            "Colored Gaussian random field",
            "SCALAR_FIELD_2D",
            colored,
            "finite-range spatial correlation",
            True,
        ),
        fixture(
            3, "Isotropic wave field", "SCALAR_FIELD_2D", isotropic_wave, "radial wavefronts", True
        ),
        fixture(
            4,
            "Anisotropic wave field",
            "SCALAR_FIELD_2D",
            anisotropic_wave,
            "oriented plane wave",
            True,
        ),
        fixture(
            5,
            "Single vortex vector field",
            "VECTOR_FIELD_2D",
            single_vortex,
            "one signed circulation center",
            True,
        ),
        fixture(
            6,
            "Counter-rotating vortex pair",
            "VECTOR_FIELD_2D",
            vortex_pair,
            "two opposite circulation centers",
            True,
        ),
        fixture(
            7,
            "Vortex shedding field",
            "VECTOR_FIELD_2D",
            shedding,
            "alternating coherent vector field",
            True,
        ),
        fixture(
            8,
            "Diffusive scalar field",
            "SCALAR_FIELD_2D",
            diffusive,
            "smooth diffusion kernel",
            True,
        ),
        fixture(
            9,
            "Wave-equation scalar field",
            "SCALAR_FIELD_2D",
            wave_equation,
            "separable standing wave",
            True,
        ),
        fixture(
            10,
            "Coupled two-fluid-like field",
            "MULTIMODAL_COUPLED_FIELD",
            coupled,
            "coupled component phases",
            True,
        ),
        fixture(
            11,
            "Bursty event-and-recovery field",
            "SPATIOTEMPORAL_SCALAR_FIELD",
            bursts,
            "localized burst geometry",
            True,
        ),
        fixture(
            12,
            "Spatially embedded AR(2) field",
            "SPATIOTEMPORAL_SCALAR_FIELD",
            ar2_space,
            "oscillatory temporal recurrence",
            True,
        ),
        fixture(
            13,
            "Common-factor sensor field",
            "CORRELATION_GEOMETRY",
            common_factor,
            "shared latent factor",
            True,
        ),
        fixture(
            14,
            "Independent-parent field ensemble",
            "SCALAR_FIELD_2D",
            independent_parent,
            "parent-stable wave relation",
            True,
        ),
        fixture(
            15,
            "Nested replicate field ensemble",
            "SCALAR_FIELD_2D",
            nested_replicate,
            "nested replicate wave relation",
            True,
        ),
        fixture(
            16,
            "Known persistent-homology ring",
            "MANIFOLD_SAMPLES",
            homology_ring,
            "one annular hole",
            True,
        ),
        fixture(
            17,
            "Graph manifold target curve",
            "GRAPH_GEOMETRY",
            target_graph,
            "ring-lattice graph curve",
            True,
            valid=("graph_spectral_gap", "graph_triangle_clustering"),
            compatible=("edge_count_preserving_rewire",),
        ),
        fixture(
            18,
            "Null-like matched graph",
            "GRAPH_GEOMETRY",
            null_graph,
            "edge-count matched random graph",
            False,
            "NONE",
            valid=("graph_spectral_gap", "graph_triangle_clustering"),
            compatible=("edge_count_preserving_rewire",),
        ),
        fixture(
            19,
            "Coordinate-rotated equivalent",
            "SCALAR_FIELD_2D",
            rotated,
            "rotated plane wave",
            True,
            behavior="effect is rotation-invariant; orientation endpoint is equivariant",
        ),
        fixture(
            20,
            "Resampled equivalent field",
            "SCALAR_FIELD_2D",
            downsampled,
            "resampled plane wave",
            True,
            behavior="effect direction survives registered resampling tolerance",
        ),
        fixture(
            21,
            "Phase-randomized field",
            "SCALAR_FIELD_2D",
            phase_randomized,
            "phase relation destroyed while spectrum retained",
            False,
            "CHANNEL_DEPENDENT",
            fingerprint="phase channel collapses; spectrum control remains",
        ),
        fixture(
            22,
            "Boundary-truncated field",
            "SCALAR_FIELD_2D",
            truncated,
            "plane wave with registered boundary loss",
            True,
            fingerprint="boundary crop graded; shuffle strong; rotation conditional",
        ),
        fixture(
            23,
            "Missingness-matched field",
            "SCALAR_FIELD_2D",
            missing,
            "plane wave under registered missingness",
            True,
            fingerprint="missingness graded within frozen mask bound",
        ),
        fixture(
            24,
            "Resolution-degraded field",
            "SCALAR_FIELD_2D",
            degraded,
            "plane wave below native resolution",
            True,
            fingerprint="resolution response graded and may become inconclusive",
        ),
        fixture(
            25,
            "One-channel adversarial checkerboard",
            "SCALAR_FIELD_2D",
            checkerboard,
            "engineered channel disagreement",
            False,
            "CHANNEL_DEPENDENT",
            fingerprint=(
                "spectral channel high; signed neighbor channel opposite; conjunction must reject"
            ),
        ),
    ]


def parent_and_null_ensembles(
    fixture: SyntheticFixture,
    *,
    parent_count: int = 12,
    null_children: int = 127,
    seed: int = 300,
) -> tuple[list[FloatArray], list[list[FloatArray]]]:
    rng = np.random.default_rng(seed + int(fixture.fixture_id.split("-")[1]))
    parents: list[FloatArray] = []
    nulls: list[list[FloatArray]] = []
    for _ in range(parent_count):
        if fixture.field_kind == "GRAPH_GEOMETRY":
            parent = fixture.field.copy()
        else:
            scale = max(float(np.std(fixture.field)), 1.0) * 0.04
            parent = fixture.field + rng.normal(scale=scale, size=fixture.field.shape)
        parents.append(np.asarray(parent, dtype=np.float64))
        nulls.append([coordinate_permutation_null(parent, rng) for _ in range(null_children)])
    return parents, nulls
