"""Prepare, check, run, combine and package graph-partitioned FHCP campaigns."""

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile

from src.graphs import load_fhcp_graph

from .campaign_evidence import atomic_json, audit_attempt, file_hash, summarize, verify_audit
from .campaign_system import awake, exclusive_lock, observation, process_identity
from .distributed_plan import (
    ROOT, attempt_keys, attempt_name, canonical, check_installation, make_plan,
    read_json, runtime, source_inventory, validate_plan,
)


def verify_inputs(plan, member, root=ROOT):
    check_installation(plan, root)
    if member not in plan['assignments']:
        raise ValueError('Member is not in this plan.')
    assigned = set(plan['assignments'][member])
    for entry in plan['instances']:
        if entry['id'] in assigned:
            path = root / 'data/raw/FHCPCS' / entry['archive_member']
            if path.name != entry['archive_member'] or path.suffix != '.hcp':
                raise ValueError('Invalid catalog member name.')
            if file_hash(path) != entry['sha256']:
                raise ValueError(f'Missing/changed instance: {entry["id"]}')


def child_command(plan, key, root=ROOT):
    solver = next(s for s in plan['solvers'] if s['algorithm'] == key[1])
    command = [sys.executable, '-m', 'src.cli', '--catalog', str(root / plan['catalog']['path']),
               '--instance', key[0], '--algorithm', key[1], '--seed', str(key[2]),
               '--max-elapsed-ns', str(plan['budget']['max_elapsed_ns'])]
    for name, value in solver['parameters'].items():
        command.extend(['--' + name.replace('_', '-'), str(value)])
    return command


def execute_attempt(plan, key, directory, root=ROOT):
    """Durably reserve before launching; a parent crash never causes an implicit retry."""
    directory.mkdir()
    command = child_command(plan, key, root)
    atomic_json(directory / 'intent.json', {'plan_sha256': plan['plan_sha256'], 'key': list(key),
                'started_utc': datetime.now(UTC).isoformat(), 'command': command, 'before': observation()})
    environment = {**os.environ, **{key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                                      'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}}
    started = time.monotonic()
    completion = {'reason': 'finished', 'returncode': None}
    interrupted = False
    process = None
    with (directory / 'stdout.json').open('w', encoding='utf-8') as stdout, (directory / 'stderr.log').open('w', encoding='utf-8') as stderr:
        try:
            process = subprocess.Popen(command, cwd=root, env=environment, stdout=stdout, stderr=stderr)
            atomic_json(directory / 'worker.json', {'pid': process.pid, 'birth': process_identity(process.pid)})
            completion['returncode'] = process.wait(timeout=plan['process_timeout_seconds'])
        except subprocess.TimeoutExpired:
            completion['reason'] = 'external_timeout'
        except KeyboardInterrupt:
            completion['reason'] = 'interrupted'
            interrupted = True
        except OSError as error:
            completion.update(reason='launch_error', detail=str(error))
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process is not None:
                completion['returncode'] = process.returncode
    completion.update(process_seconds=time.monotonic() - started, after=observation())
    atomic_json(directory / 'exit.json', completion)
    return interrupted


def _saved_rows(plan, member, output, root=ROOT, *, recover=False):
    rows = []
    current_name, graph = None, None
    keys = {attempt_name(key): key for key in attempt_keys(plan, member)}
    actual = {p.name for p in (output / 'attempts').iterdir()} if (output / 'attempts').exists() else set()
    if actual - keys.keys():
        raise ValueError('Unknown attempt directories; refusing ambiguous evidence.')
    for name, key in keys.items():
        directory = output / 'attempts' / name
        if not directory.exists():
            continue
        if not (directory / 'intent.json').exists():
            if not recover:
                raise ValueError(f'Interrupted reservation without intent: {directory}')
            atomic_json(directory / 'intent.json', {'key': list(key), 'plan_sha256': plan['plan_sha256'],
                                                    'recovery': 'directory reserved before crash; not rerun'})
        audit_path = directory / 'audit.json'
        if audit_path.exists():
            old = read_json(audit_path)
            verify_audit(directory, old)
        elif not recover:
            raise ValueError(f'Unaudited attempt: {directory}; resume its campaign first.')
        if not audit_path.exists() and not (directory / 'exit.json').exists():
            worker_path = directory / 'worker.json'
            if worker_path.exists():
                worker = read_json(worker_path)
                live = process_identity(worker['pid'])
                if live is not None and (live == worker['birth'] or 'unknown' in (live, worker['birth'])):
                    raise ValueError('An interrupted worker may still be active; wait for it to exit before resuming.')
            else:
                # Cover a parent crash between spawning and recording the PID.
                intent = read_json(directory / 'intent.json')
                if intent.get('started_utc'):
                    age = (datetime.now(UTC) - datetime.fromisoformat(intent['started_utc'])).total_seconds()
                    if age < plan['process_timeout_seconds'] + 5:
                        raise ValueError('Interrupted launch: wait for the process timeout before resuming.')
        if key[0] != current_name:
            current_name = key[0]
            graph = load_fhcp_graph(key[0], root=root, manifest=plan['catalog']['path'])
        row = audit_attempt(directory, plan, key, graph, root)
        if audit_path.exists() and old != row:
            raise ValueError(f'Audit differs from independently recomputed evidence: {directory}')
        if not audit_path.exists():
            atomic_json(audit_path, row)
        rows.append(row)
    return rows


def _identity(plan, member, output, machine, root):
    saved_plan = output / 'plan.json'
    if saved_plan.exists():
        if read_json(saved_plan) != plan:
            raise ValueError('Output belongs to a different plan.')
        identity = read_json(output / 'machine.json')
        if (identity['member'] != member or identity['machine_id'] != machine
                or identity['host'] != platform.node() or identity['runtime'] != runtime()
                or identity['os'] != platform.system()):
            raise ValueError('Machine/member changed; do not mix hardware in a shard.')
        return
    if any(p.name != '.campaign.lock' for p in output.iterdir()):
        raise ValueError('Output is not empty and has no campaign identity.')
    # Identity precedes plan: if preparation is interrupted, inspect/remove only the
    # empty new output rather than silently using an incomplete snapshot.
    atomic_json(output / 'machine.json', {'member': member, 'machine_id': machine,
                'host': platform.node(), 'os': platform.system(), 'runtime': runtime(),
                'platform': platform.platform(), 'cpu': platform.processor(), 'before': observation()})
    snapshot = output / 'source-snapshot'
    for name in plan['source_sha256']:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
    atomic_json(output / 'plan.json', plan)
    (output / 'attempts').mkdir()


def run_campaign(plan, member, output, *, root=ROOT, max_attempts=None, max_seconds=None, machine=None):
    verify_inputs(plan, member, root)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    machine = machine or platform.node()
    if not machine:
        raise ValueError('Provide --machine-id when the OS reports no hostname.')
    # Lock the host's environment as well as this output: two different shards may
    # not run concurrently from the same Python environment.
    host_lock = Path(sys.prefix) / '.fhcp-campaign.lock'
    with exclusive_lock(host_lock), exclusive_lock(output / '.campaign.lock'), awake():
        _identity(plan, member, output, machine, root)
        (output / 'attempts').mkdir(exist_ok=True)
        rows = _saved_rows(plan, member, output, root, recover=True)
        done = {(r['instance'], r['algorithm'], r['seed']) for r in rows}
        started = time.monotonic()
        admitted, reason, graph_id, graph = 0, 'complete', None, None
        summarize(plan, [member], rows, output)
        with (output / 'terminal.log').open('a', encoding='utf-8', buffering=1) as log:
            def report(message):
                print(message, flush=True)
                log.write(message + '\n')
            report(f'RESULTADOS: {output}; conservados={len(done)}')
            try:
                for key in attempt_keys(plan, member):
                    if key in done:
                        continue
                    if ((max_attempts is not None and admitted >= max_attempts)
                            or (max_seconds is not None and time.monotonic() - started >= max_seconds)):
                        reason = 'session_limit'
                        break
                    check_installation(plan, root)
                    resources = observation()
                    if resources['ac_online'] is False:
                        reason = 'ac_disconnected'
                        break
                    if (resources['available_ram_bytes'] is not None
                            and resources['available_ram_bytes'] < 2 * 1024**3):
                        reason = 'low_memory'
                        break
                    if shutil.disk_usage(output).free < 1024**3:
                        reason = 'low_disk'
                        break
                    if key[0] != graph_id:
                        graph_id = key[0]
                        graph = load_fhcp_graph(graph_id, root=root, manifest=plan['catalog']['path'])
                    directory = output / 'attempts' / attempt_name(key)
                    interrupted = execute_attempt(plan, key, directory, root)
                    row = audit_attempt(directory, plan, key, graph, root)
                    atomic_json(directory / 'audit.json', row)
                    rows.append(row)
                    admitted += 1
                    report(f"{len(rows)} {attempt_name(key)}: {row['status']}, costo={row['best_cost']}, certificado={row['certified_success']}")
                    if len(rows) % 25 == 0:
                        summarize(plan, [member], rows, output)
                    if interrupted or row['stop_reason'] == 'invalid_evidence':
                        reason = 'interrupted' if interrupted else 'invalid_evidence'
                        break
            except KeyboardInterrupt:
                reason = 'interrupted'
            except Exception:
                reason = 'coordinator_error'
                raise
            finally:
                summary = summarize(plan, [member], rows, output)
                # Keep session history instead of replacing prior pause reports.
                sessions = output / 'sessions'
                sessions.mkdir(exist_ok=True)
                from uuid import uuid4
                atomic_json(sessions / (uuid4().hex + '.json'), {'at_utc': datetime.now(UTC).isoformat(),
                    'stop_reason': reason, 'new_attempts': admitted, 'total_attempted': len(rows),
                    'session_seconds': time.monotonic() - started})
                report(f"FIN: {reason}; {summary['attempted']}/{summary['planned']}; éxitos={summary['successes']}; grafos distintos resueltos={summary['distinct_solved_graphs']}")
    return summary


def verify_snapshot(plan, directory):
    for name, expected in plan['source_sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not name.startswith('src/'):
            raise ValueError('Invalid source inventory path.')
        if file_hash(directory / 'source-snapshot' / path) != expected:
            raise ValueError('Saved source snapshot changed.')


def combine(plan, inputs, output, root=ROOT):
    check_installation(plan, root)
    directories = [Path(p).resolve() for p in inputs]
    if not directories or len(directories) != len(set(directories)):
        raise ValueError('Provide distinct campaign directories.')
    rows, owners, input_inventory = [], set(), []
    for directory in directories:
        with exclusive_lock(directory / '.campaign.lock'):
            if read_json(directory / 'plan.json') != plan:
                raise ValueError('Campaign plans differ.')
            member = read_json(directory / 'machine.json')['member']
            if member in owners or member not in plan['assignments']:
                raise ValueError('Duplicate or unknown campaign member.')
            verify_snapshot(plan, directory)
            member_rows = _saved_rows(plan, member, directory, root)
            rows.extend(member_rows)
            input_inventory.append({'directory': str(directory), 'member': member,
                                    'machine_sha256': file_hash(directory / 'machine.json'),
                                    'attempt_audits': {attempt_name((r['instance'], r['algorithm'], r['seed'])):
                                        file_hash(directory / 'attempts' / attempt_name((r['instance'], r['algorithm'], r['seed'])) / 'audit.json')
                                        for r in member_rows}})
            owners.add(member)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    atomic_json(output / 'plan.json', plan)
    atomic_json(output / 'inputs.json', {'directories': [str(p) for p in directories], 'members_present': sorted(owners),
                                      'members_missing': sorted(set(plan['assignments']) - owners),
                                      'inventory': input_inventory})
    with (output / 'attempts.jsonl').open('w', encoding='utf-8') as stream:
        for row in rows:
            stream.write(canonical(row).decode('utf-8') + '\n')
    return summarize(plan, list(plan['assignments']), rows, output)


def package(directory, target):
    directory, target = Path(directory).resolve(), Path(target).resolve()
    if target.is_relative_to(directory):
        raise ValueError('ZIP must be outside the campaign directory.')
    if target.exists() or target.with_name(target.name + '.sha256').exists():
        raise FileExistsError('ZIP or checksum already exists; neither will be replaced.')
    plan = read_json(directory / 'plan.json')
    validate_plan(plan)
    with exclusive_lock(directory / '.campaign.lock'):
        verify_snapshot(plan, directory)
        with target.open('xb') as stream:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                for path in sorted(directory.rglob('*')):
                    if path.is_symlink():
                        raise ValueError('Symlinks are not campaign artifacts.')
                    if path.is_file() and path.name != '.campaign.lock':
                        archive.write(path, arcname=directory.name + '/' + path.relative_to(directory).as_posix())
        checksum = file_hash(target)
        target.with_name(target.name + '.sha256').write_text(checksum + '  ' + target.name + '\n', encoding='ascii')
    return checksum


def handoff(plan, output):
    """Write reviewable per-member issue drafts; never contact GitHub here."""
    validate_plan(plan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    seconds = plan['budget']['max_elapsed_ns'] / 1e9
    for member, instances in plan['assignments'].items():
        count = len(instances) * len(plan['solvers']) * len(plan['seeds'])
        text = f'''## Overview

Ejecutar por sesiones la cola de @{member} hasta que el equipo alcance el objetivo global de 60 grafos distintos certificados. No es necesario agotar los 1001 candidatos si se alcanza el objetivo. Ejecutar las seis familias de cada grafo iniciado, incluidos los grafos ya medidos que aparezcan, preservando M6.

- **Responsable:** @{member}
- **Hito:** campaña completa posterior a M6; separada de #71.
- **Depende para cierre de:** publicación y verificación del ejecutador y del plan compartido.
- **Plan:** `{plan['campaign_id']}`; SHA-256 `{plan['plan_sha256']}`.
- **Cobertura:** {len(instances)} grafos candidatos, seis familias, {len(plan['seeds'])} semilla{'s' if len(plan['seeds']) != 1 else ''} ({', '.join(map(str, plan['seeds']))}); {count} intentos si se agota la cola.
- **Presupuesto:** {seconds:g} s de solver por intento, sin límite de evaluaciones; {plan['process_timeout_seconds']:g} s externos incluyendo arranque/carga. Techo de búsqueda: {count * seconds / 3600:.2f} h, más preparación/guardado; no es una predicción medida.
- **Entregable:** ZIP original con plan, perfil de máquina, snapshot, RunRecords, rutas, stderr, auditorías, sesiones y tablas; checksum SHA-256 del ZIP.

### Grafos asignados

{', '.join(instances)}

### Comandos

Usar el archivo de plan compartido en lugar de regenerarlo. Sustituir `PLAN.json` por su ruta real. En Linux:

```bash
.venv/bin/python -m src.cli.distributed_campaign check --plan PLAN.json --member {member}
systemd-inhibit --what=sleep:idle --mode=block --why="Campaña FHCP" .venv/bin/python -u -m src.cli.distributed_campaign run --plan PLAN.json --member {member}
```

En PowerShell, con el entorno y la misma versión de código:

```powershell
.\\.venv\\Scripts\\python.exe -m src.cli.distributed_campaign check --plan PLAN.json --member {member}
.\\.venv\\Scripts\\python.exe -u -m src.cli.distributed_campaign run --plan PLAN.json --member {member}
```

Repetir el mismo comando para reanudar. No editar el plan, borrar intentos ni regenerarlo para el mismo lote. Mantener la terminal y el equipo encendidos; conectar laptops a corriente. Windows inhibe suspensión por inactividad mientras vive el ejecutador; Linux usa el bloqueo anterior. El cierre de tapa, apagado manual y reinicio pueden interrumpirlo.

## Criteria

- [ ] Instalar las versiones fijadas; adjuntar el `check` y verificar la plataforma antes de lanzar el lote completo.
- [ ] Conservar el mismo equipo y código durante el lote; seis algoritmos de cada grafo en el mismo equipo, un proceso a la vez.
- [ ] Conciliar los intentos admitidos y dejar explícitos los candidatos pendientes de la cola de {count} intentos; documentar errores, timeouts e interrupciones sin borrarlos ni reintentarlos silenciosamente.
- [ ] Conservar todos los candidatos y certificar los éxitos con el validador independiente.
- [ ] Adjuntar ZIP + SHA-256 y las tablas; comprobar su recuperación antes de proponer cierre.
- [ ] Incorporar resultados a la agregación conjunta y explicar límites de comparación entre equipos.
'''
        (output / f'{member}.md').write_text(text, encoding='utf-8')
    return len(plan['assignments'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='action', required=True)
    prepare = commands.add_parser('prepare', help='Create one shared plan; does not run solvers')
    prepare.add_argument('--members', required=True, help='comma-separated actual member logins')
    prepare.add_argument('--member-graphs', action='append', default=[], metavar='MEMBER=COUNT',
                         help='explicit graph count for a member; balance the remainder among others')
    prepare.add_argument('--output', type=Path, required=True)
    for name in ('check', 'run'):
        command = commands.add_parser(name)
        command.add_argument('--plan', type=Path, required=True)
        command.add_argument('--member', required=True)
        if name == 'run':
            command.add_argument('--output', type=Path)
            command.add_argument('--machine-id')
            command.add_argument('--max-attempts', type=int)
            command.add_argument('--max-session-minutes', type=float)
    merge = commands.add_parser('combine')
    merge.add_argument('--plan', type=Path, required=True)
    merge.add_argument('--inputs', type=Path, nargs='+', required=True)
    merge.add_argument('--output', type=Path, required=True)
    pack = commands.add_parser('pack')
    pack.add_argument('--input', type=Path, required=True)
    pack.add_argument('--output', type=Path, required=True)
    drafts = commands.add_parser('handoff', help='Write per-member issue drafts without publishing them')
    drafts.add_argument('--plan', type=Path, required=True)
    drafts.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'prepare':
            if args.output.exists():
                raise ValueError('Plan already exists; it will not be replaced.')
            quotas = {}
            for value in args.member_graphs:
                member, separator, count = value.partition('=')
                if not separator or member in quotas:
                    raise ValueError('Expected distinct --member-graphs MEMBER=COUNT values.')
                quotas[member] = int(count)
            plan = make_plan(args.members.split(','), graph_quotas=quotas)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            # The plan file is created exclusively; never silently replace a frozen plan.
            with args.output.open('xb') as stream:
                stream.write(canonical(plan) + b'\n')
            print(f'PLAN: {args.output}; identidad={plan["plan_sha256"]}')
            seconds = plan['budget']['max_elapsed_ns'] / 1e9
            for member, instances in plan['assignments'].items():
                count = len(instances) * len(plan['solvers']) * len(plan['seeds'])
                print(f'{member}: {len(instances)} grafos, {count} intentos; techo de búsqueda={count * seconds / 3600:.2f} h')
            return 0
        if args.action == 'pack':
            print(package(args.input, args.output))
            return 0
        plan = read_json(args.plan)
        if args.action == 'handoff':
            print(f'{handoff(plan, args.output)} borradores; no se crearon issues en GitHub.')
        elif args.action == 'check':
            verify_inputs(plan, args.member)
            print(f'OK: {len(plan["assignments"][args.member])} grafos; no se ejecutaron solvers. {observation()}')
        elif args.action == 'run':
            if ((args.max_attempts is not None and args.max_attempts < 1)
                    or (args.max_session_minutes is not None and not 0 < args.max_session_minutes < float('inf'))):
                raise ValueError('Session limits must be positive finite numbers.')
            output = args.output or ROOT / 'experiments/results' / f'distributed-{plan["campaign_id"]}-{args.member}'
            summary = run_campaign(plan, args.member, output, machine=args.machine_id,
                         max_attempts=args.max_attempts,
                         max_seconds=None if args.max_session_minutes is None else args.max_session_minutes * 60)
            if summary['attempted'] == summary['planned']:
                return 0
            return 3  # Paused with pending attempts; the same command resumes.
        else:
            summary = combine(plan, args.inputs, args.output)
            print(f"{summary['attempted']}/{summary['planned']}; éxitos={summary['successes']}; grafos distintos resueltos={summary['distinct_solved_graphs']}; errores={summary['errors']}")
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(f'campaign_error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
