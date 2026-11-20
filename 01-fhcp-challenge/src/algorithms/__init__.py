"""Search primitives shared by solver implementations."""

from .abc import ABC_VARIANT, ABCConfigurationError, resolve_abc_parameters, solve_abc
from .permutation import initialize_route, order_crossover, swap_mutation
from .genetic import GA_VARIANT, GAConfigurationError, resolve_ga_parameters, solve_ga
from .annealing import SA_VARIANT, SAConfigurationError, resolve_sa_parameters, solve_sa
from .real_keys import KeyDecodingError, decode_real_keys
from .differential import DE_VARIANT, DEConfigurationError, resolve_de_parameters, solve_de
from .particle_swarm import PSO_VARIANT, PSOConfigurationError, resolve_pso_parameters, solve_pso
from .ant_system import AS_VARIANT, ASConfigurationError, resolve_as_parameters, solve_as

__all__ = [
    "ABC_VARIANT", "ABCConfigurationError", "resolve_abc_parameters", "solve_abc",
    "GA_VARIANT", "GAConfigurationError", "resolve_ga_parameters", "solve_ga",
    "SA_VARIANT", "SAConfigurationError", "resolve_sa_parameters", "solve_sa",
    "initialize_route", "order_crossover", "swap_mutation",
    "KeyDecodingError", "decode_real_keys",
    "DE_VARIANT", "DEConfigurationError", "resolve_de_parameters", "solve_de",
    "PSO_VARIANT", "PSOConfigurationError", "resolve_pso_parameters", "solve_pso",
    "AS_VARIANT", "ASConfigurationError", "resolve_as_parameters", "solve_as",
]
