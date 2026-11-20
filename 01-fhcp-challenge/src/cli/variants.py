"""CLI options and RunRecord metadata for the integrated solver variants."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from src.algorithms import abc, annealing, ant_system, differential, genetic, particle_swarm
from src.algorithms.execution import SolverResult


@dataclass(frozen=True)
class Variant:
    family: str
    name: str
    module: str
    iteration_unit: str
    initialization: str
    ties: Mapping[str, str]
    options: tuple[str, ...]
    resolve: Callable[[Mapping[str, object]], dict]
    solve: Callable[..., SolverResult]
    uses_real_keys: bool = False
    optional_options: tuple[str, ...] = ()


VARIANTS = {
    "ga": Variant(
        "GA", genetic.GA_VARIANT, "genetic", "generation", "independent_uniform_permutations",
        {"tournament": "lowest_population_index", "elites": "stable_order"},
        ("population_size", "tournament_size", "crossover_rate", "mutation_rate", "elite_count"),
        genetic.resolve_ga_parameters, genetic.solve_ga,
        optional_options=("initialization", "guided_move_rate"),
    ),
    "sa": Variant(
        "SA", annealing.SA_VARIANT, "annealing", "move", "uniform_permutation",
        {"current": "accept_equal_cost"},
        ("initial_temperature", "cooling_factor", "minimum_temperature", "moves_per_temperature"),
        annealing.resolve_sa_parameters, annealing.solve_sa,
        optional_options=("initialization", "guided_move_rate", "cost_mode", "incremental_check_interval", "reheat_after"),
    ),
    "as": Variant(
        "ACO", ant_system.AS_VARIANT, "ant_system", "round", "constant_pheromone_uniform_ant_starts",
        {"construction": "sample_in_ascending_vertex_order"},
        ("ant_count", "alpha", "beta", "rho", "q", "epsilon",
         "initial_pheromone", "pheromone_min", "pheromone_max"),
        ant_system.resolve_as_parameters, ant_system.solve_as,
        optional_options=("construction", "pheromone_storage"),
    ),
    "abc": Variant(
        "ABC", abc.ABC_VARIANT, "abc", "abc_cycle", "independent_uniform_permutations",
        {"source": "keep_current_on_equal_cost", "scout": "lowest_source_index_at_max_trials"},
        ("source_count", "limit"), abc.resolve_abc_parameters, abc.solve_abc,
        optional_options=("initialization", "guided_move_rate", "cost_mode", "incremental_check_interval"),
    ),
    "de": Variant(
        "DE", differential.DE_VARIANT, "differential", "generation", "uniform_real_keys_0_1",
        {"target": "keep_current_on_equal_cost", "decoder": "lowest_vertex_index"},
        ("population_size", "differential_weight", "crossover_rate"),
        differential.resolve_de_parameters, differential.solve_de, uses_real_keys=True, optional_options=("initialization",),
    ),
    "pso": Variant(
        "PSO", particle_swarm.PSO_VARIANT, "particle_swarm", "round",
        "uniform_real_keys_0_1_and_centered_uniform_velocities_with_optional_clip",
        {"personal": "keep_previous_on_equal_cost", "global": "first_seen", "decoder": "lowest_vertex_index"},
        ("swarm_size", "inertia", "cognitive_coefficient", "social_coefficient", "velocity_limit"),
        particle_swarm.resolve_pso_parameters, particle_swarm.solve_pso, uses_real_keys=True, optional_options=("initialization",),
    ),
}

CONFIGURATION_ERRORS = (
    genetic.GAConfigurationError, annealing.SAConfigurationError, ant_system.ASConfigurationError,
    abc.ABCConfigurationError, differential.DEConfigurationError, particle_swarm.PSOConfigurationError,
)

INTEGER_OPTIONS = frozenset({
    "population_size", "tournament_size", "elite_count", "moves_per_temperature",
    "ant_count", "source_count", "limit", "swarm_size", "incremental_check_interval", "reheat_after",
})


STRING_OPTIONS = {
    "initialization": ("uniform", "greedy"),
    "construction": ("all_vertices", "neighbor_guided"),
    "cost_mode": ("full", "incremental"),
    "pheromone_storage": ("all_pairs", "edges"),
}


def effective_variant(spec: Variant, parameters: Mapping) -> Variant:
    """Identify opt-in search policies separately from the frozen v1 variants."""
    greedy = parameters.get("initialization") == "greedy"
    guided = parameters.get("guided_move_rate", 0) > 0
    construction = parameters.get("construction") == "neighbor_guided"
    enhanced = (parameters.get("cost_mode") == "incremental" or parameters.get("reheat_after", 0) > 0
                or parameters.get("pheromone_storage") == "edges")
    if not (greedy or guided or construction or enhanced):
        return spec
    initialization = spec.initialization
    if greedy:
        initialization = "minimum_remaining_degree_greedy_permutations"
        if spec.uses_real_keys:
            initialization += "_encoded_as_rank_keys"
    if construction:
        initialization = "constant_pheromone_neighbor_guided_ant_tours"
    suffix = "_enhanced_v3" if enhanced else "_graph_guided_v2"
    return replace(spec, name=spec.name.removesuffix("_v1") + suffix,
                   initialization=initialization)
