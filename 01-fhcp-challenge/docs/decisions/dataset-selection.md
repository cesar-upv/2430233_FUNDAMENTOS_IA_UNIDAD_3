# Selección de instancias FHCP y procedencia

**Estado:** decisión propuesta para revisión en el [issue #16](https://github.com/ZapataFrame/FHCP-Challenge/issues/16) (M2).
**Responsable:** Diego Eduardo Zapata Aguilar · @ZapataFrame.

## Contexto y decisión

A partir de la [investigación de formatos](../research/fhcp-challenge.md), se seleccionan nueve instancias del [FHCP Challenge Set oficial](https://sites.flinders.edu.au/flinders-hamiltonian-cycle-project/fhcp-challenge-set/). El [manifiesto](fhcp-instances.json) fija miembros, fechas UTC de descarga, tamaños, metadatos observados y SHA-256 de archivos y miembros. Los hashes se calculan sobre bytes originales, incluidos finales de línea.

| Uso | Miembros (vértices) | Justificación |
| --- | --- | --- |
| Pruebas de humo | graph1 (66), graph2 (70) | Dos entradas pequeñas para comprobar carga y ciclo conocido; no son evidencia de rendimiento. Familia no identificada. |
| Ajuste | graph58 (396), graph268 (1644) | Contraste entre casi ciclo y vértices de alto grado; permiten ajustar sin consultar resultados de evaluación. |
| Evaluación | graph48 (338), graph175 (1014) | Motivo de tamaño 16 en dos escalas. |
| Evaluación | graph74 (462), graph479 (2772) | Familia de campanas en dos escalas. |
| Evaluación de escala | graph1001 (9528) | Estructura por bloques; analizar por separado para distinguir costo de escala. |

Los rasgos se atribuyen al [relato de Cohen y Coudert](https://interstices.info/le-defi-des-1001-graphes/), no se infieren del identificador ni de la dimensión. El [artículo de Haythorpe](https://arxiv.org/abs/1902.10352v1) describe la variedad estructural del conjunto. Mantener juntos los motivos documentados reduce el solapamiento conocido entre ajuste y evaluación; no demuestra independencia estructural completa. El subconjunto es intencional y no representa estadísticamente los 1001 grafos.

Se descartó usar solo los grafos más pequeños, porque limitaría tamaño y variedad, y usar el conjunto completo como requisito inicial, porque aumentaría el costo antes de conocer el entorno. Congelar IDs y configuración antes de evaluar. Si un caso reservado se usa para ajustar, declararlo y revisar la partición antes de la comparación. Semillas, límites y protocolo comparativo se acuerdan en M6.

## Fuente de datos y consecuencias

- **Fuente habitual:** usar los grafos seleccionados por el manifiesto en `data/raw/FHCPCS/` del checkout. `data/raw/FHCPCS_sols/` contiene los certificados de referencia y se reserva para comprobación independiente; no es una entrada del solver ni del ajuste.
- **Integridad:** los 18 miembros seleccionados de la copia versionada coinciden byte por byte, mediante SHA-256, con los miembros extraídos de los paquetes oficiales. Esta comprobación cubre solo la selección. Para reproducir el trabajo basta un checkout que conserve esos hashes; si un hash difiere, detener el uso de esa copia e investigar.
- **Recuperación alternativa:** si falta la copia versionada o se quiere auditar la procedencia, usar la receta de abajo y comprobar ambos paquetes y todos los miembros seleccionados. Usar `instances/` y `certificates/` de esa recuperación como pareja, sin mezclar copias ni reemplazar los originales versionados.
- **Almacenamiento:** conservar el dataset ya versionado. Las recuperaciones agregan unos 20 MB por ejecución y quedan excluidas mediante `/data/raw/fhcp-*/`. No forzar su inclusión con `git add -f`. Esto permite recuperar y auditar sin duplicar el dataset en Git ni cambiar la copia del equipo.

## Recuperación y conservación

Desde la raíz del repositorio, con Bash, curl, jq, sha256sum y bsdtar con soporte 7z. Cada recuperación crea un directorio nuevo; conserva los dos comprimidos intactos. Solo los miembros explícitos del manifiesto se extraen a rutas predefinidas, sin ejecutar una extracción general.

```bash
set -euo pipefail
manifest=docs/decisions/fhcp-instances.json
mkdir -p data/raw
root=$(mktemp -d data/raw/fhcp-XXXXXX)
mkdir -p "$root"/{archives,instances,certificates}

for kind in graphs certificates; do
    name=$(jq -er --arg k "$kind" '.archives[$k].filename' "$manifest")
    url=$(jq -er --arg k "$kind" '.archives[$k].url' "$manifest")
    hash=$(jq -er --arg k "$kind" '.archives[$k].sha256' "$manifest")
    curl --fail --location --silent --show-error --output "$root/archives/$name.part" "$url"
    printf '%s  %s\n' "$hash" "$root/archives/$name.part" | sha256sum --check
    mv "$root/archives/$name.part" "$root/archives/$name"
done

jq -er '.instances[] | [.archive_member, .sha256, .certificate.archive_member, .certificate.sha256] | @tsv' "$manifest" |
while IFS=$'\t' read -r graph graph_hash tour tour_hash; do
    [[ "$graph" =~ ^graph[0-9]+\.hcp$ && "$tour" == "$graph.tou" ]]
    bsdtar -xOf "$root/archives/FHCPCS.7z" "$graph" > "$root/instances/$graph"
    bsdtar -xOf "$root/archives/FHCPCS_sols.7z" "$tour" > "$root/certificates/$tour"
    printf '%s  %s\n' "$graph_hash" "$root/instances/$graph" | sha256sum --check
    printf '%s  %s\n' "$tour_hash" "$root/certificates/$tour" | sha256sum --check
done
printf 'Recuperación verificada: %s\n' "$root"
```

Si una verificación falla, detener el uso de esa copia e investigar antes de cambiar el manifiesto. Cualquier transformación posterior se guarda en `data/processed/` con referencia al hash original.

## Comprobaciones

Los nueve miembros HCP se inspeccionaron en la descarga fechada en el manifiesto: formato EDGE_LIST, etiquetas en el rango declarado y aristas sin bucles ni duplicados. Se comprobó de forma puntual que cada tour tiene la misma dimensión, cubre exactamente las etiquetas esperadas y utiliza aristas existentes, incluido el cierre. Esta comprobación documental no implementa el parser o validador de M3 ni ejecuta solvers.
