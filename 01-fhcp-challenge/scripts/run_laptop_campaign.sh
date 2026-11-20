#!/usr/bin/env bash
# Launch the v3 laptop campaign locally, or resume the explicitly supplied UUID.
set -euo pipefail

if [[ $# -gt 1 ]]; then
    printf 'Uso: bash scripts/run_laptop_campaign.sh [--check|--help|CAMPAIGN_DIRECTORY]\n' >&2
    exit 2
fi
if [[ ${1:-} == --help ]]; then
    printf '%s\n' \
        'Uso: bash scripts/run_laptop_campaign.sh [--check|CAMPAIGN_DIRECTORY]' \
        'Sin argumento: crea una campaña v3 nueva y la ejecuta.' \
        '--check: comprueba equipo, recursos y bloqueo de suspensión sin buscar.' \
        'Con directorio: continúa esa campaña; no sustituye intentos anteriores.' \
        'Requiere protocolo v3 aceptado y commit limpio para ejecutar búsqueda.'
    exit 0
fi
if [[ ${1:-} == --* ]]; then
    if [[ $1 != --check ]]; then
        printf 'Opción desconocida: %s\n' "$1" >&2
        exit 2
    fi
fi

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$project_root"
python_path="$project_root/.venv/bin/python"
config_path=experiments/configs/benchmark-v3.json
if [[ ! -x $python_path ]]; then
    printf 'Falta el entorno virtual del proyecto: %s\n' "$python_path" >&2
    exit 1
fi
if ! command -v systemd-inhibit >/dev/null; then
    printf 'No se encontró systemd-inhibit; revisar prevención de suspensión.\n' >&2
    exit 1
fi

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
"$python_path" -m src.cli.benchmark_campaign check --config "$config_path"
systemd-inhibit --what=sleep --mode=block --why='FHCP readiness check' /usr/bin/true
if [[ ${1:-} == --check ]]; then
    printf 'Equipo, recursos y bloqueo de suspensión comprobados. No se ejecutó búsqueda.\n'
    exit 0
fi

if [[ $# -eq 0 ]]; then
    campaign_directory=$("$python_path" -m src.cli.benchmark_campaign prepare --config "$config_path")
else
    campaign_directory=$1
fi
if [[ ! -f $campaign_directory/manifest.json ]]; then
    printf 'No se encontró el manifiesto: %s/manifest.json\n' "$campaign_directory" >&2
    exit 1
fi
printf 'Campaña: %s\nLog: %s/console.log\n' "$campaign_directory" "$campaign_directory"
printf 'Si se pausa, revisar la causa y continuar con este mismo directorio.\n'
systemd-inhibit --what=sleep --mode=block --why='FHCP M6 laptop campaign' \
    "$python_path" -u -m src.cli.benchmark_campaign run "$campaign_directory" \
    2>&1 | tee -a "$campaign_directory/console.log"
