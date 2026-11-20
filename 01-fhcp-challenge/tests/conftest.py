"""Small in-memory graph fixtures, independent of FHCP files and readers."""

import pytest

from src.graphs import Graph


@pytest.fixture
def example_graph():
    """The nonconsecutive-label example accepted in contract #17."""
    return Graph(
        [10, 20, 30, 40, 50],
        [(10, 20), (20, 30), (30, 40), (40, 50), (10, 50), (10, 30), (20, 40)],
    )


@pytest.fixture(params=[
    pytest.param(
        ('ga',
         ['--population-size', '8', '--tournament-size', '3'],
         'GA',
         'generation',
         'genetic.py'),
        id='ga'
    ),
    pytest.param(
        ('sa',
         ['--initial-temperature',
          '2',
          '--cooling-factor',
          '0.9',
          '--minimum-temperature',
          '0',
          '--moves-per-temperature',
          '10'],
         'SA',
         'move',
         'annealing.py'),
        id='sa'
    ),
    pytest.param(
        ('as',
         ['--ant-count',
          '4',
          '--alpha',
          '1',
          '--beta',
          '2',
          '--rho',
          '0.2',
          '--q',
          '1',
          '--epsilon',
          '0.05',
          '--initial-pheromone',
          '1',
          '--pheromone-min',
          '0.1',
          '--pheromone-max',
          '10'],
         'ACO',
         'round',
         'ant_system.py'),
        id='as'
    ),
    pytest.param(
        ('abc', ['--source-count', '4', '--limit', '5'], 'ABC', 'abc_cycle', 'abc.py'),
        id='abc'
    ),
    pytest.param(
        ('de',
         ['--population-size', '4', '--differential-weight', '0.5', '--crossover-rate', '0.8'],
         'DE',
         'generation',
         'differential.py'),
        id='de'
    ),
    pytest.param(
        ('pso',
         ['--swarm-size',
          '4',
          '--inertia',
          '0.5',
          '--cognitive-coefficient',
          '1',
          '--social-coefficient',
          '1'],
         'PSO',
         'round',
         'particle_swarm.py'),
        id='pso'
    ),
])
def cli_solver_case(request):
    """Small explicit configurations for public CLI integration checks."""
    return request.param
