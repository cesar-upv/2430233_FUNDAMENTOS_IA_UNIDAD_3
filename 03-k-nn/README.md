# K vecinos más cercanos

El [notebook](knn_manual_colab.ipynb) implementa KNN por búsqueda exhaustiva. Compara la distancia euclidiana, la de Manhattan y la suma de ambas mediante datos sintéticos, matrices de confusión y regiones de decisión.

## Ejecutar el notebook

En Google Colab, sube `knn_manual_colab.ipynb` y ejecuta todas las celdas en orden. Para abrirlo localmente con Python 3.12 y `uv`, ejecuta el siguiente comando desde esta carpeta.

```bash
uv run --no-project --python 3.12 --with notebook --with numpy --with matplotlib --with scikit-learn python -m notebook knn_manual_colab.ipynb
```

El cuaderno fija la semilla de los experimentos. Usa scikit-learn para generar datos con `make_blobs` y calcula la votación, la exactitud y las matrices de confusión con su propio código.
