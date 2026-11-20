"""Independent checks for delta fitness, reheating and O(m) pheromone storage."""
from dataclasses import asdict
from itertools import permutations
import json

import numpy as np
import pytest

from src.algorithms import annealing, ant_system
from src.algorithms.execution import Budget, SolverRun, start_run
from src.algorithms.local_moves import RouteMove
from src.algorithms.sparse_pheromone import initialize_sparse
from src.cli import __main__ as cli
from src.cli.variants import VARIANTS, effective_variant
from src.evaluation import evaluate_cost, validate_cycle
from src.graphs import Graph

SA = dict(initial_temperature=2, cooling_factor=0.95, minimum_temperature=1e-6,
          moves_per_temperature=10)
ABC = dict(source_count=4, limit=5)
AS = dict(ant_count=3, alpha=1, beta=2, rho=0.3, q=1.7, epsilon=0.05,
          initial_pheromone=1.5, pheromone_min=0.2, pheromone_max=2)


def path_graph(n=8):
    return Graph(range(n), [(i,i+1) for i in range(n-1)])


def make_run(graph,budget=None,clock=lambda:0):
    run=start_run(graph,seed=3,budget=budget or Budget(max_evaluations=50),
                  iteration_unit='move',clock=clock)
    assert isinstance(run,SolverRun)
    return run


@pytest.mark.parametrize('n',range(3,8))
def test_all_swap_and_reversal_boundaries_match_full_cost(n):
    # Include sparse, complete and disconnected graphs; closure is implicit.
    pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
    graphs=[Graph(range(n),pairs),Graph(range(n),[]),
            Graph(range(n),[edge for k,edge in enumerate(pairs) if k%3!=0])]
    routes=list(permutations(range(n)))[:18]
    for graph in graphs:
        for route in routes:
            cost=evaluate_cost(graph,route)
            for i in range(n):
                for j in range(n):
                    for move in [RouteMove('swap',i,j),RouteMove('inversion',min(i,j),max(i,j))]:
                        child=move.apply(route)
                        assert sorted(child)==list(range(n))
                        assert move.cost_after(graph,route,cost)==evaluate_cost(graph,child)


@pytest.mark.parametrize('move',[RouteMove('swap',1,70),RouteMove('inversion',2,90)])
def test_delta_queries_only_changed_edges(move,monkeypatch):
    graph=path_graph(100);route=tuple(range(100));cost=evaluate_cost(graph,route)
    calls=[];original=Graph.has_edge
    def count(self,u,v):calls.append((u,v));return original(self,u,v)
    monkeypatch.setattr(Graph,'has_edge',count)
    value=move.cost_after(graph,route,cost)
    assert len(calls)<=(8 if move.kind=='swap' else 4)
    assert value==evaluate_cost(graph,move.apply(route))


@pytest.mark.parametrize('move',[RouteMove('swap',-1,2),RouteMove('inversion',3,1),
                                  RouteMove('invalid',1,2),RouteMove('swap',True,2)])
def test_invalid_move_descriptors_are_rejected(move):
    with pytest.raises(ValueError):move.apply(tuple(range(5)))


def test_runtime_counts_full_and_incremental_without_double_reservation():
    graph=path_graph();route=tuple(range(8));run=make_run(graph,Budget(max_evaluations=3))
    assert run.begin_phase('search',3)
    first=run.evaluate(route,evaluate_cost);run.record_item()
    move=RouteMove('swap',2,5);child=move.apply(route)
    assert run.evaluate_incremental(child,lambda g,r:move.cost_after(g,route,first),check_interval=1)==evaluate_cost(graph,child)
    run.record_item()
    run.evaluate(route,evaluate_cost);run.record_item()
    result=run.finish();c=result.counters
    assert (c.evaluations_started,c.evaluations_completed,c.full_evaluations,c.incremental_evaluations)==(3,3,2,1)
    assert c.algorithm_counters['incremental_full_checks']==1


def test_wrong_zero_delta_is_rejected_before_success_certification():
    graph=path_graph();run=make_run(graph);assert run.begin_phase('search',1)
    assert run.evaluate_incremental(tuple(range(8)),lambda g,r:0) is None
    result=run.finish()
    assert result.status=='error' and result.stop_reason=='fitness_validation_mismatch'
    assert result.error.code=='incremental_cost_mismatch'
    assert result.counters.evaluations_started==1 and result.counters.evaluations_completed==0
    assert not result.success_within_budget and result.counters.validations_started==0


def test_periodic_check_detects_wrong_nonimproving_delta():
    graph=path_graph();route=tuple(range(8));run=make_run(graph);assert run.begin_phase('search',2)
    run.evaluate(route,evaluate_cost)
    assert run.evaluate_incremental(route,lambda g,r:2,check_interval=1) is None
    assert run.finish().error.code=='incremental_cost_mismatch'


@pytest.mark.parametrize('algorithm,params',[('sa',SA),('abc',ABC)])
@pytest.mark.parametrize('guided',[0,0.5,1])
def test_incremental_preserves_full_search_trajectory(algorithm,params,guided):
    graph=Graph(range(8),[(i,i+1) for i in range(7)]+[(1,4),(2,6)])
    params={**params,'initialization':'greedy','guided_move_rate':guided}
    def solve(extra):return VARIANTS[algorithm].solve(graph,parameters={**params,**extra},seed=13,
                                                     budget=Budget(max_evaluations=160),clock=lambda:0)
    full=solve({});incremental=solve({'cost_mode':'incremental','incremental_check_interval':7})
    assert (full.best_route,full.best_cost,full.status)==(incremental.best_route,incremental.best_cost,incremental.status)
    c=incremental.counters
    assert c.incremental_evaluations>0 and c.full_evaluations+c.incremental_evaluations==c.evaluations_completed==160
    assert evaluate_cost(graph,incremental.best_route)==incremental.best_cost
    repeat=solve({'cost_mode':'incremental','incremental_check_interval':7});assert repeat==incremental


def test_sa_reheats_after_stagnation_and_keeps_budget():
    graph=Graph(range(6),[])
    params={**SA,'cost_mode':'incremental','reheat_after':3}
    result=VARIANTS['sa'].solve(graph,parameters=params,seed=3,budget=Budget(max_evaluations=11),clock=lambda:0)
    assert result.status=='exhausted' and result.counters.evaluations_completed==11
    assert result.counters.algorithm_counters['reheats']==result.counters.restarts==3
    assert result.best_cost==6


def test_sa_reheats_at_temperature_floor_instead_of_ending_early():
    graph=Graph(range(6),[]);params={**SA,'minimum_temperature':1.9,'cooling_factor':0.5,'moves_per_temperature':1}
    def solve(extra):return VARIANTS['sa'].solve(graph,parameters={**params,**extra},seed=3,
                                                budget=Budget(max_evaluations=7),clock=lambda:0)
    old=solve({});new=solve({'reheat_after':100})
    assert old.stop_reason=='algorithm_stop' and old.counters.evaluations_completed==2
    assert new.stop_reason=='evaluation_limit' and new.counters.evaluations_completed==7
    assert new.counters.algorithm_counters['reheats']==6


def test_reheating_restores_best_route_after_accepting_a_worse_move(monkeypatch):
    graph=path_graph();best=tuple(range(8));inputs=[]
    monkeypatch.setattr(annealing,'initialize_route',lambda n,rng:best)
    def swap(route,**kw):inputs.append(route);return RouteMove('swap',2,5).apply(route)
    monkeypatch.setattr(annealing,'swap_mutation',swap)
    monkeypatch.setattr(annealing,'_accept_move',lambda *args:True)
    result=annealing.solve_sa(graph,parameters={**SA,'reheat_after':1},seed=3,
                              budget=Budget(max_evaluations=4),clock=lambda:0)
    assert inputs==[best,best,best] and result.best_route==best
    assert result.counters.restarts==3


def test_sparse_updates_match_independent_dictionary_formula():
    graph=Graph(range(6),[(0,1),(1,2),(2,3),(3,4),(4,5),(0,5),(1,4)])
    run=make_run(graph);pheromone=initialize_sparse(graph,1.5,0.2,run)
    tours=[(tuple(range(6)),evaluate_cost(graph,tuple(range(6)))),
           ((0,2,1,3,5,4),evaluate_cost(graph,(0,2,1,3,5,4)))]
    expected={frozenset(edge):1.5*(1-AS['rho']) for edge in graph.edges()}
    for route,cost in tours:
        for i,u in enumerate(route):
            edge=frozenset((u,route[(i+1)%6]))
            if edge in expected:expected[edge]+=AS['q']/(1+cost)
    assert run.begin_phase('round',1)
    assert ant_system._update_pheromone(6,pheromone,tours,AS,run)
    assert len(pheromone.values)==len(pheromone.edge_index)==graph.edge_count()
    for (u,v) in graph.edges():
        assert pheromone.value(u,v)==pytest.approx(min(AS['pheromone_max'],max(AS['pheromone_min'],expected[frozenset((u,v))])))
        assert pheromone.value(u,v)==pheromone.value(v,u)
    assert pheromone.value(0,2)==0.2 and pheromone.index(0,2) is None
    assert run.finish().counters.algorithm_counters['pheromone_missing_deposits_skipped']>0


def test_sparse_initialization_never_allocates_all_pairs(monkeypatch):
    graph=path_graph(10000);run=make_run(graph)
    original=np.empty;allocations=[]
    def empty(size,*args,**kwargs):allocations.append(size);return original(size,*args,**kwargs)
    monkeypatch.setattr(np,'empty',empty)
    pheromone=initialize_sparse(graph,1,0.1,run)
    assert allocations==[9999] and pheromone.values.nbytes==9999*8
    assert len(pheromone.edge_index)==9999


def test_sparse_solver_does_not_call_dense_allocator(monkeypatch):
    monkeypatch.setattr(ant_system,'_allocate_pheromone',lambda *a:pytest.fail('Dense allocation attempted'))
    graph=Graph(range(6),[])
    result=ant_system.solve_as(graph,parameters={**AS,'construction':'neighbor_guided','pheromone_storage':'edges'},
                              seed=1,budget=Budget(max_evaluations=5),clock=lambda:0)
    assert result.status=='exhausted' and result.best_cost==6
    assert result.counters.evaluations_completed==5


def test_sparse_and_dense_guided_ants_have_same_candidate_trajectory():
    graph=Graph(range(8),[(i,i+1) for i in range(7)]+[(1,4),(2,6)])
    params={**AS,'construction':'neighbor_guided'}
    def solve(extra):return ant_system.solve_as(graph,parameters={**params,**extra},seed=4,
                                                budget=Budget(max_evaluations=80),clock=lambda:0)
    dense=solve({});sparse=solve({'pheromone_storage':'edges'})
    assert (dense.best_route,dense.best_cost,dense.status)==(sparse.best_route,sparse.best_cost,sparse.status)
    assert sparse==solve({'pheromone_storage':'edges'})
    assert evaluate_cost(graph,sparse.best_route)==sparse.best_cost


@pytest.mark.parametrize('algorithm,params,options',[
    ('sa',SA,{'cost_mode':'incremental','reheat_after':3}),
    ('abc',ABC,{'cost_mode':'incremental'}),
    ('as',AS,{'pheromone_storage':'edges','construction':'neighbor_guided'})])
def test_enhanced_cli_records_parameters_counters_and_source_hashes(algorithm,params,options,monkeypatch,capsys):
    graph=path_graph();monkeypatch.setattr(cli,'load_fhcp_graph',lambda *a,**kw:graph)
    args=['--instance','graph2','--algorithm',algorithm,'--seed','3','--max-evaluations','20']
    for key,value in {**params,**options}.items():args+=['--'+key.replace('_','-'),str(value)]
    assert cli.main(args)==0;record=json.loads(capsys.readouterr().out)
    assert record['procedure']['variant'].endswith('_enhanced_v3')
    field='pheromone_storage_version' if algorithm=='as' else 'local_moves_version'
    assert record['procedure'][field].startswith('sha256:')
    assert record['result']['counters']['evaluations_completed']==20


@pytest.mark.parametrize('algorithm,params,field,value',[
    ('sa',SA,'reheat_after',True),('sa',SA,'reheat_after',-1),
    ('sa',SA,'cost_mode','unknown'),('abc',ABC,'incremental_check_interval',0),
    ('abc',ABC,'incremental_check_interval',2),('as',AS,'pheromone_storage',[]),
    ('as',AS,'pheromone_storage','unknown')])
def test_invalid_enhancement_options_rejected_before_clock(algorithm,params,field,value):
    def clock():pytest.fail('Clock used before configuration rejection')
    result=VARIANTS[algorithm].solve(path_graph(),parameters={**params,field:value},seed=1,
                                    budget=Budget(max_evaluations=5),clock=clock)
    assert result.stop_reason=='invalid_config' and result.error.detail['parameter']==field


@pytest.mark.parametrize('algorithm,params,extra',[
    ('sa',SA,{'cost_mode':'full','reheat_after':0}),('abc',ABC,{'cost_mode':'full'}),
    ('as',AS,{'pheromone_storage':'all_pairs'})])
def test_disabled_enhancements_preserve_previous_behavior(algorithm,params,extra):
    graph=path_graph()
    def solve(p):return VARIANTS[algorithm].solve(graph,parameters=p,seed=3,
                                                budget=Budget(max_evaluations=30),clock=lambda:0)
    assert solve(params)==solve({**params,**extra})
    assert effective_variant(VARIANTS[algorithm],extra)==VARIANTS[algorithm]


def test_incremental_zero_on_last_reservation_is_independently_certified():
    graph=Graph(range(4),[(0,1),(1,2),(2,3),(0,3)])
    route=(0,2,1,3);move=RouteMove('swap',1,2)
    run=make_run(graph,Budget(max_evaluations=2));assert run.begin_phase('search',2)
    cost=run.evaluate(route,evaluate_cost);run.record_item()
    assert run.evaluate_incremental(move.apply(route),lambda g,r:move.cost_after(g,route,cost))==0
    run.record_item();result=run.certify_best()
    assert result.status=='success' and result.validation.valid
    assert (result.counters.full_evaluations,result.counters.incremental_evaluations)==(1,1)
    assert result.counters.validations_completed==1


def test_late_incremental_zero_does_not_become_a_success():
    graph=Graph(range(4),[(0,1),(1,2),(2,3),(0,3)]);now=[0]
    run=make_run(graph,Budget(max_evaluations=2,max_elapsed_ns=10),clock=lambda:now[0])
    assert run.begin_phase('search',1)
    def late(g,route):now[0]=10;return 0
    assert run.evaluate_incremental(tuple(range(4)),late)==0
    result=run.certify_best()
    assert result.status=='exhausted' and result.stop_reason=='time_limit'
    assert not result.success_within_budget and result.counters.validations_started==0


def test_reheating_does_not_reset_iteration_budget():
    graph=Graph(range(6),[])
    result=annealing.solve_sa(graph,parameters={**SA,'reheat_after':1,'cost_mode':'incremental'},
                              seed=1,budget=Budget(max_iterations=3),clock=lambda:0)
    assert result.stop_reason=='iteration_limit'
    assert result.counters.iterations_completed==3 and result.counters.evaluations_completed==4
    assert result.counters.restarts==3


def test_sparse_initialization_preserves_partial_phase_on_timeout():
    graph=path_graph(120);ticks=iter(range(10000))
    run=make_run(graph,Budget(max_elapsed_ns=20),clock=lambda:next(ticks))
    assert initialize_sparse(graph,1,0.1,run) is None
    result=run.finish()
    assert result.stop_reason=='time_limit' and result.counters.evaluations_completed==0
    phase=result.counters.partial_iteration
    assert phase.phase=='initialization' and phase.completed_items<phase.planned_items
