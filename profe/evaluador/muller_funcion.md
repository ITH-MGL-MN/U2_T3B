---
funcion: muller
firma: "muller(f, x0, x1, x2, tol=1e-6, max_iter=100)"
salida: escalar
ejemplo: "muller(EJ_MU['f'], EJ_MU['x0'], EJ_MU['x1'], EJ_MU['x2'])"
---

Programa el **método de Müller**: con tres puntos iniciales $(x_0, x_1, x_2)$
ajustas una parábola que pasa por los tres y saltas a la raíz de esa parábola
más cercana a $x_2$; repites hasta converger. Como la raíz puede ser compleja,
usa aritmética compleja (`cmath.sqrt`).

Tu función recibe:

* `f` — la función a la que buscas la raíz (una lambda o `def` que recibe `x`)
* `x0, x1, x2` — los tres puntos iniciales
* `tol` — la tolerancia del criterio de paro (por omisión `1e-6`)
* `max_iter` — el número máximo de iteraciones (por omisión `100`)

y devuelve **una tupla con dos elementos**: `(raiz, n_iter)`.
