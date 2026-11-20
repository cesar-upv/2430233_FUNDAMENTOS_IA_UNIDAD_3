# Entregables de investigación

Copia la [plantilla](../templates/research-deliverable.md) a la ruta indicada en tu issue. Para el #1, desde la raíz del repositorio:

```bash
cp docs/templates/research-deliverable.md docs/research/graph-theory.md
```

## Citas y bibliografía

Registra las fuentes en [references.bib](references.bib), bajo el bloque de tu issue. El archivo incluye ejemplos para libros, artículos, ponencias y páginas web. Si una fuente ya existe, reutiliza su entrada.

Usa claves estables con apellido o entidad, año y título abreviado en inglés, sin espacios ni acentos. Distingue ediciones diferentes. Separa autores con `and`, conserva los títulos originales y registra DOI o URL; para páginas web, incluye la fecha de consulta en `note`.

Cita en el desarrollo con `[@clave]` o `[@clave, p. 25]`. En **Referencias**, lista las claves citadas y enlaza el `.bib` compartido.

GitHub muestra las claves sin procesarlas. Al generar el informe se aplicará el [estilo IEEE](https://procomm.ieee.org/transactions-of-professional-communication/for-prospective-authors/guidelines-to-follow/guidelines-for-preparing-references/) con los datos del `.bib`.

## Capturas

Guarda las imágenes en `evidence/<clave>.png` o `.jpg`, según su formato. Si necesitas otra captura de la misma fuente, añade un sufijo: `<clave>-details.png`.

- **Libro:** portada y, si hace falta identificar la edición, página editorial.
- **Artículo o ponencia:** primera página o ficha oficial con título, autores y datos de publicación.
- **Página web o documento institucional:** encabezado con título y entidad responsable; registra la URL en el `.bib`.

En **Anexo de referencias**, incluye una ficha por clave con fecha de captura, descripción e imagen. La plantilla contiene un ejemplo comentado.

## Entrega

Incluye el documento, las entradas bibliográficas y las capturas en el mismo PR. Puedes indicar **captura pendiente** en avances parciales; completa las evidencias antes de cerrar el issue. El flujo de entrega está en [CONTRIBUTING.md](../../CONTRIBUTING.md).
