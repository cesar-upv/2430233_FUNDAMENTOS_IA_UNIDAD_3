"""Graph-aware search contracts: legality, edge guidance, budgets and provenance."""
import json

import numpy as np
import pytest

from src.algorithms.execution import Budget, SolverRun, start_run
from src.algorithms.graph_guidance import greedy_keys, greedy_route, guided_inversion
from src.algorithms.real_keys import decode_real_keys
from src.cli import __main__ as cli
from src.cli.variants import VARIANTS, effective_variant
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph, GraphError

PARAMETERS = {
    'ga': dict(population_size=6, tournament_size=2, mutation_rate=1),
    'sa': dict(initial_temperature=2, cooling_factor=0.95, minimum_temperature=1e-6,
               moves_per_temperature=50),
    'as': dict(ant_count=4, alpha=1, beta=4, rho=0.2, q=1, epsilon=0.05,
               initial_pheromone=1, pheromone_min=0.1, pheromone_max=10),
    'abc': dict(source_count=4, limit=3),
    'de': dict(population_size=4, differential_weight=0.8, crossover_rate=0.8),
    'pso': dict(swarm_size=4, inertia=0.5, cognitive_coefficient=1, social_coefficient=1),
}


def cycle(n=8):
    return Graph(range(n), [(i, i+1) for i in range(n-1)] + [(0, n-1)])


def runtime(graph, seed=1, clock=lambda: 0, budget=None):
    run = start_run(graph, seed=seed, budget=budget or Budget(max_evaluations=100),
                    iteration_unit='move', clock=clock)
    assert isinstance(run, SolverRun)
    assert run.begin_phase('initialization', 1)
    return run


def edges(route):
    return {frozenset((u, route[(i+1) % len(route)])) for i,u in enumerate(route)}


@pytest.mark.parametrize('seed', range(12))
def test_greedy_follows_real_cycle_and_decodes_identically(seed):
    graph=cycle()
    route=greedy_route(graph,runtime(graph,seed))
    assert validate_cycle(graph,route).valid
    keys=greedy_keys(graph,runtime(graph,seed))
    assert decode_real_keys(graph.vertex_count(),keys)==route


def test_blocked_greedy_jumps_without_losing_vertices_or_claiming_success():
    graph=Graph(range(7), [(0,1),(1,2),(3,4)])
    run=runtime(graph)
    route=greedy_route(graph,run)
    assert sorted(route)==list(range(7))
    assert evaluate_cost(graph,route)>0
    assert not validate_cycle(graph,route).valid
    assert run.finish().counters.algorithm_counters['greedy_jumps']>0


@pytest.mark.parametrize('seed', range(24))
def test_guided_inversion_preserves_input_and_creates_a_real_adjacency(seed):
    graph=cycle()
    route=tuple(int(v) for v in np.random.default_rng(seed).permutation(8))
    before=tuple(route);run=runtime(graph,seed)
    child=guided_inversion(graph,route,run)
    assert route==before and sorted(child)==list(range(8))
    if run.finish().counters.algorithm_counters.get('guided_inversions',0):
        real={frozenset(edge) for edge in graph.edges()}
        assert (edges(child)-edges(route)) & real


@pytest.mark.parametrize('route', [(0,1,1,3,4,5,6,7), (0,1,2), (0,1,2,3,4,5,6,10)])
def test_guided_rejects_illegal_candidates(route):
    graph=cycle()
    with pytest.raises(GraphError):
        guided_inversion(graph,route,runtime(graph))


@pytest.mark.parametrize('operator', [greedy_route,greedy_keys])
def test_construction_can_stop_before_evaluating_a_prefix(operator):
    graph=cycle(50)
    ticks=iter(range(1000))
    run=runtime(graph,clock=lambda: next(ticks),budget=Budget(max_elapsed_ns=12,max_evaluations=10))
    assert operator(graph,run) is None
    result=run.finish()
    assert result.stop_reason=='time_limit'
    assert result.best_route is None and result.counters.evaluations_completed==0


def test_guided_move_can_stop_before_evaluation():
    graph=cycle(50);ticks=iter(range(1000))
    run=runtime(graph,clock=lambda:next(ticks),budget=Budget(max_elapsed_ns=3,max_evaluations=10))
    assert guided_inversion(graph,tuple(range(0,50,2))+tuple(range(1,50,2)),run) is None
    assert run.finish().counters.evaluations_completed==0


@pytest.mark.parametrize('algorithm',PARAMETERS)
def test_each_opt_in_solver_certifies_known_cycle_on_last_allowed_evaluation(algorithm):
    params={**PARAMETERS[algorithm],**({'construction':'neighbor_guided'} if algorithm=='as'
                                    else {'initialization':'greedy'})}
    if algorithm in ('ga','sa','abc'):
        params['guided_move_rate']=0.5
    graph=cycle()
    result=VARIANTS[algorithm].solve(graph,parameters=params,seed=3,
                                   budget=Budget(max_evaluations=1),clock=lambda:0)
    assert result.status=='success' and result.success_within_budget
    assert result.counters.evaluations_completed==1
    assert result.best_cost==0 and validate_cycle(graph,result.best_route).valid


@pytest.mark.parametrize('algorithm',PARAMETERS)
def test_opt_in_is_reproducible_and_preserves_evaluation_limit(algorithm):
    # A leaf makes this graph non-Hamiltonian; never require a heuristic to prove it.
    graph=Graph(range(8), [(i,i+1) for i in range(7)]+[(1,4),(2,6)])
    params={**PARAMETERS[algorithm],**({'construction':'neighbor_guided'} if algorithm=='as'
                                    else {'initialization':'greedy'})}
    if algorithm in ('ga','sa','abc'):
        params['guided_move_rate']=0.5
    def solve():return VARIANTS[algorithm].solve(graph,parameters=params,seed=13,
                                               budget=Budget(max_evaluations=60),clock=lambda:0)
    first,second=solve(),solve()
    assert first==second and first.status=='exhausted'
    assert first.counters.evaluations_completed==60
    assert sorted(first.best_route)==list(range(8))
    assert evaluate_cost(graph,first.best_route)==first.best_cost>0


@pytest.mark.parametrize('algorithm',['ga','sa','abc'])
def test_guided_moves_are_used_during_search(algorithm):
    graph=Graph(range(8),[(i,i+1) for i in range(7)]+[(1,4),(2,6)])
    result=VARIANTS[algorithm].solve(graph,parameters={**PARAMETERS[algorithm], 'guided_move_rate':1},
                                    seed=5,budget=Budget(max_evaluations=50),clock=lambda:0)
    assert result.status=='exhausted'
    assert result.counters.algorithm_counters.get('guided_inversions',0)>0
    assert evaluate_cost(graph,result.best_route)==result.best_cost


@pytest.mark.parametrize('algorithm',PARAMETERS)
def test_explicit_legacy_policies_consume_same_random_trajectory(algorithm):
    graph=Graph(range(8),[(i,i+1) for i in range(7)]+[(1,4),(2,6)])
    params=PARAMETERS[algorithm]
    options=({'construction':'all_vertices'} if algorithm=='as' else {'initialization':'uniform'})
    if algorithm in ('ga','sa','abc'):options['guided_move_rate']=0
    def solve(p):return VARIANTS[algorithm].solve(graph,parameters=p,seed=5,
                                                 budget=Budget(max_evaluations=50),clock=lambda:0)
    assert solve(params)==solve({**params,**options})
    assert effective_variant(VARIANTS[algorithm],{**params,**options})==VARIANTS[algorithm]


@pytest.mark.parametrize('algorithm',PARAMETERS)
@pytest.mark.parametrize('value',[None,True,[], 'unknown'])
def test_invalid_search_policy_is_rejected_before_clock(algorithm,value):
    field='construction' if algorithm=='as' else 'initialization'
    def clock():pytest.fail('Clock started before rejecting invalid options')
    result=VARIANTS[algorithm].solve(cycle(),parameters={**PARAMETERS[algorithm],field:value},
                                    seed=1,budget=Budget(max_evaluations=5),clock=clock)
    assert result.stop_reason=='invalid_config' and result.error.detail['parameter']==field


@pytest.mark.parametrize('algorithm',['ga','sa','abc'])
@pytest.mark.parametrize('rate',[True,-0.1,1.1,float('nan'),float('inf'),'0.5'])
def test_invalid_guidance_rate_is_rejected(algorithm,rate):
    result=VARIANTS[algorithm].solve(cycle(),parameters={**PARAMETERS[algorithm],'guided_move_rate':rate},
                                    seed=1,budget=Budget(max_evaluations=5))
    assert result.stop_reason=='invalid_config' and result.error.detail['parameter']=='guided_move_rate'


@pytest.mark.parametrize('algorithm',PARAMETERS)
def test_cli_records_effective_variant_and_operator_hash(algorithm,monkeypatch,capsys):
    monkeypatch.setattr(cli,'load_fhcp_graph',lambda *a,**kw:cycle())
    args=['--instance','graph2','--seed','3','--algorithm',algorithm,'--max-evaluations','1']
    for key,value in PARAMETERS[algorithm].items():args += ['--'+key.replace('_','-'),str(value)]
    args += ['--construction','neighbor_guided'] if algorithm=='as' else ['--initialization','greedy']
    assert cli.main(args)==0
    record=json.loads(capsys.readouterr().out)
    assert record['procedure']['variant'].endswith('_graph_guided_v2')
    assert record['procedure']['search_operator_version'].startswith('sha256:')
    assert record['result']['validation']['valid']


@pytest.mark.parametrize('algorithm',PARAMETERS)
def test_time_limit_interrupts_graph_aware_initialization_without_prefix_fitness(algorithm):
    ticks=iter(range(10000))
    params={**PARAMETERS[algorithm],**({'construction':'neighbor_guided'} if algorithm=='as'
                                    else {'initialization':'greedy'})}
    result=VARIANTS[algorithm].solve(cycle(120),parameters=params,seed=1,
                                    budget=Budget(max_evaluations=10,max_elapsed_ns=50),
                                    clock=lambda:next(ticks))
    assert result.status=='exhausted' and result.stop_reason=='time_limit'
    assert result.best_route is None and result.counters.evaluations_completed==0


def test_neighbor_guided_ants_can_jump_across_disconnected_components():
    graph=Graph(range(6),[(0,1),(1,2),(3,4),(4,5)])
    result=VARIANTS['as'].solve(graph,parameters={**PARAMETERS['as'],'construction':'neighbor_guided'},
                              seed=1,budget=Budget(max_evaluations=5),clock=lambda:0)
    assert result.status=='exhausted'
    assert sorted(result.best_route)==list(range(6))
    assert evaluate_cost(graph,result.best_route)==result.best_cost>0
    assert result.counters.algorithm_counters['neighbor_guided_jumps']>0
