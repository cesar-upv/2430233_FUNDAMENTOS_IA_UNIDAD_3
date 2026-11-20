"""Build descriptive tables from an independently audited combine directory."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    durations = [r["process_seconds"] for r in rows if r["process_seconds"] is not None]
    costs = [r["best_cost"] for r in rows if r["best_cost"] is not None]
    successes = sum(r["certified_success"] for r in rows)
    return {
        "attempted": len(rows),
        "successes": successes,
        "success_rate_attempted": successes / len(rows) if rows else None,
        "solved_graphs": len({r["instance"] for r in rows if r["certified_success"]}),
        "exhausted": sum(r["status"] == "exhausted" for r in rows),
        "errors": sum(r["status"] == "error" for r in rows),
        "external_timeouts": sum(r["stop_reason"] == "external_timeout" for r in rows),
        "process_seconds_available": len(durations),
        "process_seconds_sum": sum(durations),
        "mean_process_seconds": statistics.mean(durations) if durations else None,
        "costs_available": len(costs),
        "best_cost": min(costs) if costs else None,
        "median_cost": statistics.median(costs) if costs else None,
    }


def build(combined, packages_path, output):
    plan = read(combined / "plan.json")
    summary = read(combined / "summary.json")
    packages = read(packages_path)
    if packages["plan_sha256"] != summary["plan_sha256"]:
        raise ValueError("Package manifest and combined plan differ.")
    owners = {}
    for member, graphs in plan["assignments"].items():
        for graph in graphs:
            if graph in owners:
                raise ValueError("Overlapping graph assignments.")
            owners[graph] = member
    rows = [json.loads(line) for line in (combined / "attempts.jsonl").read_text().splitlines()]
    keys = [(r["instance"], r["algorithm"], r["seed"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Repeated attempts.")
    algorithms = [s["algorithm"] for s in plan["solvers"]]
    expected_keys = {(graph, algorithm, seed) for graph in owners
                     for algorithm in algorithms for seed in plan["seeds"]}
    if not set(keys) <= expected_keys:
        raise ValueError("Attempts outside the frozen plan.")
    totals = aggregate(rows)
    for field in ("attempted", "successes", "errors"):
        if totals[field] != summary[field]:
            raise ValueError(f"Combined total mismatch: {field}")
    solved = sorted({r["instance"] for r in rows if r["certified_success"]},
                    key=lambda g: int(g.removeprefix("graph")))
    if solved != summary["solved_graph_ids"] or len(solved) != summary["distinct_solved_graphs"]:
        raise ValueError("Certified graph inventory mismatch.")
    cells = defaultdict(list)
    by_graph = defaultdict(list)
    by_member = defaultdict(list)
    for row in rows:
        cells[(row["instance"], row["algorithm"])].append(row)
        by_graph[row["instance"]].append(row)
        by_member[owners[row["instance"]]].append(row)
    for cell in summary["cells"]:
        actual = aggregate(cells[(cell["instance"], cell["algorithm"])])
        for field in ("attempted", "successes", "errors", "external_timeouts", "best_cost", "median_cost"):
            if actual[field] != cell[field]:
                raise ValueError(f"Cell mismatch: {cell['instance']}/{cell['algorithm']}/{field}")
        if cell["pending"] != cell["planned"] - actual["attempted"]:
            raise ValueError("Pending count mismatch.")
    per_graph_planned = len(algorithms) * len(plan["seeds"])
    graph_rows = []
    for graph in sorted(owners, key=lambda g: int(g.removeprefix("graph"))):
        entry = next(e for e in plan["instances"] if e["id"] == graph)
        group = by_graph[graph]
        metrics = aggregate(group)
        graph_rows.append({"instance": graph, "member": owners[graph],
                           "vertices": entry["dimension"], "edges": entry["edge_count"],
                           "planned": per_graph_planned,
                           "pending": per_graph_planned - len(group),
                           "coverage": "complete" if len(group) == per_graph_planned else "partial" if group else "not_started",
                           **metrics})
    complete = {r["instance"] for r in graph_rows if r["coverage"] == "complete"}
    member_rows = []
    for member, graphs in plan["assignments"].items():
        group = by_member[member]
        member_rows.append({"member": member, "assigned_graphs": len(graphs),
                            "complete_graphs": len(set(graphs) & complete),
                            "partial_graphs": sum(bool(by_graph[g]) and g not in complete for g in graphs),
                            "pending": len(graphs) * per_graph_planned - len(group),
                            **aggregate(group)})
    for package in packages["packages"]:
        if len(by_member[package["member"]]) != package["expected_attempts"]:
            raise ValueError("Package cut differs from combined attempts.")
    algorithm_rows = []
    for member in ["ALL", *plan["assignments"]]:
        selected = rows if member == "ALL" else by_member[member]
        for scope in ("all_admitted", "complete_graphs_only"):
            group = selected if scope == "all_admitted" else [r for r in selected if r["instance"] in complete]
            for algorithm in algorithms:
                algorithm_rows.append({"member": member, "scope": scope, "algorithm": algorithm,
                                       **aggregate([r for r in group if r["algorithm"] == algorithm])})
    flattened = [{"member": owners[r["instance"]], "instance": r["instance"],
                  "algorithm": r["algorithm"], "seed": r["seed"], "status": r["status"],
                  "stop_reason": r["stop_reason"], "certified_success": r["certified_success"],
                  "best_cost": r["best_cost"], "process_seconds": r["process_seconds"],
                  "solver_ns": r["solver_ns"]} for r in rows]
    coverage = Counter(r["coverage"] for r in graph_rows)
    result = {"plan_sha256": summary["plan_sha256"], "execution_revision": packages["execution_revision"],
              "planned": summary["planned"], "pending": summary["planned"] - len(rows),
              "original_goal": plan["goal_distinct_solved_graphs"],
              "closing_expectation_approximate": 20,
              "expectation_provenance": "Arturo's instruction at closing; not a preregistered target",
              "scope_decision": "Close this partial delivery without further searches; retain pending combinations",
              "coverage": dict(coverage), "solved_graph_ids": solved, **totals,
              "input_sha256": {name: hashlib.sha256((combined / name).read_bytes()).hexdigest()
                               for name in ("plan.json", "inputs.json", "attempts.jsonl", "summary.json")}}
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "by-graph.csv", graph_rows)
    write_csv(output / "by-member.csv", member_rows)
    write_csv(output / "by-algorithm.csv", algorithm_rows)
    write_csv(output / "attempts.csv", flattened)
    (output / "totals.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    text = "# Evaluación distribuida: tablas del corte final\n\n"
    text += f"{len(rows):,} intentos; {totals['successes']} éxitos; {len(solved)} grafos distintos certificados; {totals['errors']} incidencias.\n\n"
    text += "## Por integrante\n\n| Integrante | Intentos | Grafos completos | Parciales | Resueltos | Éxitos | Incidencias | Pendientes |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    for r in member_rows:
        text += f"| {r['member']} | {r['attempted']} | {r['complete_graphs']} | {r['partial_graphs']} | {r['solved_graphs']} | {r['successes']} | {r['errors']} | {r['pending']} |\n"
    text += f"\n## Por algoritmo: {len(complete)} grafos con las {per_graph_planned} combinaciones conciliadas\n\n"
    text += "La cobertura es balanceada por algoritmo; los errores permanecen en el denominador. Los equipos tienen hardware distinto.\n\n"
    text += "| Algoritmo | Intentos | Éxitos | Grafos resueltos | Incidencias | Media de proceso (s) | Duraciones disponibles |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
    for r in algorithm_rows:
        if r["member"] == "ALL" and r["scope"] == "complete_graphs_only":
            mean = f"{r['mean_process_seconds']:.3f}" if r["mean_process_seconds"] is not None else "—"
            text += f"| {r['algorithm'].upper()} | {r['attempted']} | {r['successes']} | {r['solved_graphs']} | {r['errors']} | {mean} | {r['process_seconds_available']} |\n"
    text += "\n## Cada grafo iniciado\n\n| Grafo | Integrante | Vértices | Intentos | Éxitos | Resuelto | Incidencias | Pendientes |\n| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |\n"
    for r in graph_rows:
        if r["attempted"]:
            text += f"| {r['instance']} | {r['member']} | {r['vertices']} | {r['attempted']}/60 | {r['successes']} | {'Sí' if r['solved_graphs'] else 'Sin certificado'} | {r['errors']} | {r['pending']} |\n"
    text += "\n`by-graph.csv` conserva también los grafos sin iniciar; `by-algorithm.csv` separa equipo y cobertura. Los agotamientos no prueban ausencia de ciclo. Las medias incluyen procesos censurados e incidencias con duración disponible y no son tiempos medios hasta resolver. La suma de procesos no es duración calendario.\n"
    (output / "tables.md").write_text(text, encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.combined, args.packages, args.output), indent=2))
