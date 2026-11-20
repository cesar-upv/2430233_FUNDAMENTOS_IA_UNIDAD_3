"""Verify each new CLI family against a bounded, verified FHCP instance."""

from hashlib import sha256
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.cli import __main__ as cli


@pytest.mark.parametrize(
    "algorithm,family,variant,module,unit,options,parameters,real_keys",
    [
        ("sa", "SA", "geometric_swap_v1", "annealing", "move",
         "--initial-temperature 2 --cooling-factor 0.8 --minimum-temperature 0 --moves-per-temperature 2",
         {"initial_temperature": 2.0, "cooling_factor": 0.8,
          "minimum_temperature": 0.0, "moves_per_temperature": 2}, False),
        ("as", "ACO", "ant_system_missing_pairs_v1", "ant_system", "round",
         "--ant-count 2 --alpha 1 --beta 2 --rho 0.3 --q 1 --epsilon 0.1 "
         "--initial-pheromone 1 --pheromone-min 0.01 --pheromone-max 10",
         {"ant_count": 2, "alpha": 1.0, "beta": 2.0, "rho": 0.3, "q": 1.0, "epsilon": 0.1,
          "initial_pheromone": 1.0, "pheromone_min": 0.01, "pheromone_max": 10.0}, False),
        ("abc", "ABC", "sequential_partner_swap_v1", "abc", "abc_cycle",
         "--source-count 2 --limit 3", {"source_count": 2, "limit": 3}, False),
        ("de", "DE", "rand_1_bin_real_keys_v1", "differential", "generation",
         "--population-size 4 --differential-weight 0.5 --crossover-rate 0.8",
         {"population_size": 4, "differential_weight": 0.5, "crossover_rate": 0.8}, True),
        ("pso", "PSO", "global_real_keys_v1", "particle_swarm", "round",
         "--swarm-size 3 --inertia 0.7 --cognitive-coefficient 1 --social-coefficient 1",
         {"swarm_size": 3, "inertia": 0.7, "cognitive_coefficient": 1.0,
          "social_coefficient": 1.0, "velocity_limit": None}, True),
    ],
)
def test_selected_family_runs_and_rejects_incompatible_options(
    algorithm, family, variant, module, unit, options, parameters, real_keys, capsys, monkeypatch,
):
    args = ["--instance", "graph1", "--seed", "17", "--max-evaluations", "9",
            "--algorithm", algorithm, "--variant", variant, *options.split()]
    assert cli.main(args) == 0
    output = capsys.readouterr()
    assert output.err == ""
    record = json.loads(output.out)
    procedure = record["procedure"]
    assert (procedure["family"], procedure["variant"], procedure["iteration_unit"]) == (family, variant, unit)
    assert procedure["parameters"] == parameters
    assert procedure["initialization"] and procedure["tie_policy"]["best"] == "first_seen"
    src = Path(__file__).resolve().parents[1] / "src"
    def version(path):
        return "sha256:" + sha256((src / path).read_bytes()).hexdigest()
    assert procedure["implementation_version"] == version(f"algorithms/{module}.py")
    assert procedure["decoder_version"] == (version("algorithms/real_keys.py") if real_keys else None)
    assert procedure["instrumentation_version"] == version("algorithms/execution.py")
    assert record["instance"]["id"] == "graph1" and record["instance"]["sha256"]
    result = record["result"]
    assert result["counters"]["iteration_unit"] == unit
    assert 0 < result["counters"]["evaluations_completed"] <= 9
    assert result["status"] in {"success", "exhausted"}

    def forbidden(*args, **kwargs):
        pytest.fail("Rejected configuration started loading the graph")

    monkeypatch.setattr(cli, "load_fhcp_graph", forbidden)
    assert cli.main([*args, "--tournament-size", "2"]) == 2
    rejected = json.loads(capsys.readouterr().out)
    assert rejected["procedure"]["parameters"] is None
    assert rejected["result"]["error"]["code"] == "incompatible_parameter"
    assert rejected["result"]["counters"]["iteration_unit"] == unit
    assert rejected["result"]["counters"]["evaluations_started"] == 0


def test_rejects_mismatched_variant(capsys):
    assert cli.main(["--instance", "graph1", "--seed", "17", "--max-evaluations", "1",
                     "--algorithm", "abc", "--variant", "geometric_swap_v1"]) == 2
    result = json.loads(capsys.readouterr().out)["result"]
    assert result["error"]["code"] == "invalid_variant"
    assert result["counters"]["evaluations_started"] == 0



ROOT = Path(__file__).resolve().parents[1]
COMMON = ['--instance', 'graph1', '--seed', '17', '--max-evaluations', '20']


def test_each_solver_emits_its_metadata_and_a_verified_attempt(cli_solver_case, tmp_path):
    name, flags, family, unit, module = cli_solver_case
    proc = subprocess.run(
        [sys.executable, '-m', 'src.cli', *COMMON, '--algorithm', name, *flags, '--output-dir', str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ''
    record = json.loads(proc.stdout)
    procedure = record['procedure']
    assert procedure['family'] == family
    assert procedure['iteration_unit'] == unit
    assert record['result']['counters']['iteration_unit'] == unit
    assert procedure['implementation_version'] == 'sha256:' + sha256((ROOT / 'src/algorithms' / module).read_bytes()).hexdigest()
    assert procedure['initialization'] and procedure['tie_policy']
    if name in ('de', 'pso'):
        assert procedure['decoder_version'] == 'sha256:' + sha256((ROOT / 'src/algorithms/real_keys.py').read_bytes()).hexdigest()
    else:
        assert procedure['decoder_version'] is None
    assert record['instance']['id'] == 'graph1'
    assert record['instance']['sha256']
    assert record['result']['status'] in ('success', 'exhausted')
    assert record['result']['counters']['evaluations_started'] <= 20
    saved = tmp_path / record['run']['run_id'] / 'run.json'
    assert json.loads(saved.read_text()) == record


def test_foreign_parameters_are_rejected_before_loading(cli_solver_case, monkeypatch, capsys):
    name, flags, family, unit, _ = cli_solver_case
    foreign = ['--ant-count', '4'] if name == 'abc' else ['--source-count', '4']
    def unexpected_load(*args, **kwargs):
        raise AssertionError('Loading started before configuration validation.')

    monkeypatch.setattr(cli, 'load_fhcp_graph', unexpected_load)
    assert cli.main([*COMMON, '--algorithm', name, *flags, *foreign]) == 2
    record = json.loads(capsys.readouterr().out)
    assert record['procedure']['family'] == family
    assert record['result']['error']['code'] == 'incompatible_parameter'
    assert record['result']['counters']['evaluations_started'] == 0
    assert record['result']['counters']['iteration_unit'] == unit
    assert record['procedure']['parameters'] is None


def test_invalid_budget_retains_selected_unit_and_parameters(cli_solver_case, capsys):
    name, flags, family, unit, _ = cli_solver_case
    assert cli.main([*COMMON, '--algorithm', name, *flags, '--max-evaluations', '0']) == 2
    record = json.loads(capsys.readouterr().out)
    assert record['procedure']['family'] == family
    assert record['procedure']['parameters'] is not None
    assert record['result']['error']['code'] == 'invalid_budget'
    assert record['result']['counters']['iteration_unit'] == unit


def test_missing_parameters_return_an_attempt_for_the_selected_solver(cli_solver_case, capsys):
    name, _, family, unit, _ = cli_solver_case
    assert cli.main([*COMMON, '--algorithm', name]) == 2
    record = json.loads(capsys.readouterr().out)
    assert record['procedure']['family'] == family
    assert record['result']['error']['code'] == 'missing_parameter'
    assert record['result']['counters']['iteration_unit'] == unit


def test_record_builder_preserves_default_ga_callers():
    from src.algorithms.execution import Budget
    from src.cli.run_record import build_record

    record = build_record(
        ROOT, run_id='compatibility-check', started_at_utc='2026-11-12T00:00:00+00:00',
        instance_id='graph1', graph=None, parameters=None, seed=17,
        budget=Budget(max_evaluations=1),
    )
    assert record['procedure']['family'] == 'GA'
    assert record['procedure']['iteration_unit'] == 'generation'
