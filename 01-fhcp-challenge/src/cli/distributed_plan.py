"""Fixed, portable experiment plans independent of the historical M6 coordinator."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import struct
import sys
from uuid import uuid4

import numpy as np

from .variants import VARIANTS

ROOT = Path(__file__).resolve().parents[2]
CATALOG = 'docs/decisions/fhcp-catalog.json'
PRESETS = 'experiments/configs/search-enhanced-v3-presets.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    value = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
    canonical(value)
    return value


def source_inventory(root=ROOT):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / 'src').rglob('*.py'))}


def runtime():
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'numpy': np.__version__, 'gil_enabled': getattr(sys, '_is_gil_enabled', lambda: True)(),
            'bits': struct.calcsize('P') * 8,
            'architecture': {'amd64': 'x86_64'}.get(platform.machine().lower(), platform.machine().lower())}


def partition(entries, members, graph_quotas=None):
    """Balance graph counts first and approximate n+m work second; never split a graph."""
    assigned = {member: [] for member in members}
    load = {member: 0 for member in members}
    targets = None
    if graph_quotas:
        if (set(graph_quotas) - set(members)
                or any(type(n) is not int or n < 1 for n in graph_quotas.values())):
            raise ValueError('Graph quotas must be positive integers for known members.')
        others = [m for m in members if m not in graph_quotas]
        remaining = len(entries) - sum(graph_quotas.values())
        if remaining < len(others) or (not others and remaining != 0):
            raise ValueError('Graph quotas leave an invalid remainder.')
        targets = dict(graph_quotas)
        if others:
            base, extra = divmod(remaining, len(others))
            targets.update({m: base + (i < extra) for i, m in enumerate(others)})
    for entry in sorted(entries, key=lambda e: (-(e['dimension'] + e['edge_count']), e['id'])):
        if targets is None:
            member = min(members, key=lambda m: (len(assigned[m]), load[m], members.index(m)))
        else:
            eligible = [m for m in members if len(assigned[m]) < targets[m]]
            member = min(eligible, key=lambda m: (len(assigned[m]) / targets[m],
                                                 load[m] / targets[m], members.index(m)))
        assigned[member].append(entry['id'])
        load[member] += entry['dimension'] + entry['edge_count']
    for instances in assigned.values():
        instances.sort(key=lambda name: int(name.removeprefix('graph')))
    return assigned


def make_plan(members, root=ROOT, *, expected_count=1001, graph_quotas=None):
    if (not members or len({m.casefold() for m in members}) != len(members) or len(members) > expected_count
            or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', m) for m in members)):
        raise ValueError('Provide unique GitHub logins or explicit member identifiers.')
    catalog = read_json(root / CATALOG)
    entries = catalog['instances']
    ids = {e['id'] for e in entries}
    if len(entries) != expected_count or ids != {f'graph{i}' for i in range(1, expected_count + 1)}:
        raise ValueError('Full catalog must contain exactly graph1 through graph1001.')
    solvers = read_json(root / PRESETS)['solvers']
    for solver in solvers:
        solver['parameters'] = VARIANTS[solver['algorithm']].resolve(solver['parameters'])
    plan = {'schema': 'fhcp-distributed-plan/1', 'campaign_id': str(uuid4()),
            'created_utc': datetime.now(UTC).isoformat(),
            'purpose': 'Candidate queue targeting 60 distinct certified graphs; includes historical M6 instances',
            'goal_distinct_solved_graphs': 60,
            'catalog': {'path': CATALOG, 'sha256': sha256((root / CATALOG).read_bytes()).hexdigest()},
            'instances': entries, 'assignments': partition(entries, members, graph_quotas), 'solvers': solvers,
            'requested_graph_counts': dict(graph_quotas or {}),
            'seeds': list(range(1001, 1011)), 'budget': {'max_elapsed_ns': 60_000_000_000,
                                                      'max_evaluations': None, 'max_iterations': None},
            'process_timeout_seconds': 120, 'source_sha256': source_inventory(root),
            'runtime': runtime(), 'workers_per_machine': 1, 'native_threads': 1}
    plan['plan_sha256'] = digest(plan)
    validate_plan(plan)
    return plan


def validate_plan(plan):
    body = {k: v for k, v in plan.items() if k != 'plan_sha256'}
    if plan.get('schema') != 'fhcp-distributed-plan/1' or digest(body) != plan.get('plan_sha256'):
        raise ValueError('Plan identity/hash mismatch.')
    if not re.fullmatch(r'[0-9a-f-]{36}', plan['campaign_id']):
        raise ValueError('Invalid campaign identifier.')
    goal = plan.get('goal_distinct_solved_graphs', 60)
    if type(goal) is not int or goal < 1:
        raise ValueError('Distinct solved graph goal must be positive.')
    ids = [entry['id'] for entry in plan['instances']]
    assigned = [name for instances in plan['assignments'].values() for name in instances]
    if len(ids) != len(set(ids)) or sorted(ids) != sorted(assigned):
        raise ValueError('Assignments must cover every graph exactly once.')
    if any(not re.fullmatch(r'graph[1-9][0-9]*', name) for name in ids):
        raise ValueError('Invalid graph identifier.')
    if (not plan['assignments'] or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', m)
                                     for m in plan['assignments'])):
        raise ValueError('Invalid member identifier.')
    if len({m.casefold() for m in plan['assignments']}) != len(plan['assignments']):
        raise ValueError('Member identifiers must differ on case-insensitive filesystems.')
    for member, count in plan.get('requested_graph_counts', {}).items():
        if type(count) is not int or count < 1 or len(plan['assignments'].get(member, [])) != count:
            raise ValueError('Assignments differ from the requested graph quotas.')
    if [s['algorithm'] for s in plan['solvers']] != list(VARIANTS):
        raise ValueError('The plan must run all six solver families.')
    for solver in plan['solvers']:
        if VARIANTS[solver['algorithm']].resolve(solver['parameters']) != solver['parameters']:
            raise ValueError('Noncanonical solver parameters.')
    seeds = plan['seeds']
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int or not 0 <= s < 2**64 for s in seeds):
        raise ValueError('Invalid or duplicate seeds.')
    budget = plan['budget']
    if (type(budget['max_elapsed_ns']) is not int or budget['max_elapsed_ns'] <= 0
            or budget['max_evaluations'] is not None or budget['max_iterations'] is not None
            or plan['process_timeout_seconds'] <= budget['max_elapsed_ns'] / 1e9):
        raise ValueError('Invalid time budget or external timeout.')
    if plan['workers_per_machine'] != 1 or plan['native_threads'] != 1:
        raise ValueError('Only sequential single-native-thread campaigns are supported.')


def check_installation(plan, root=ROOT):
    validate_plan(plan)
    if source_inventory(root) != plan['source_sha256']:
        raise ValueError('Source code changed; use the exact version used to prepare the plan.')
    if runtime() != plan['runtime']:
        raise ValueError('Python/NumPy/architecture differs from the frozen runtime.')
    catalog_path = root / plan['catalog']['path']
    if not catalog_path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Catalog must be inside the checkout.')
    if sha256(catalog_path.read_bytes()).hexdigest() != plan['catalog']['sha256']:
        raise ValueError('Catalog changed.')
    if read_json(catalog_path)['instances'] != plan['instances']:
        raise ValueError('Plan/catalog entries differ.')


def attempt_keys(plan, member):
    for instance in plan['assignments'][member]:
        for seed in plan['seeds']:
            for solver in plan['solvers']:
                yield instance, solver['algorithm'], seed


def attempt_name(key):
    return f'{key[0]}-{key[1]}-{key[2]}'
