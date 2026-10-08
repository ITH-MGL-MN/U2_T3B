---
funcion: muller
firma: "muller(f, x0, x1, x2, tol=1e-6, max_iter=100)"
salida: escalar
ejemplo: "muller(lambda x: x**3 - 13*x - 12, 4.0, 5.0, 5.5)"
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

En cada iteración: `h0 = x1-x0`, `h1 = x2-x1`, `d0 = (f(x1)-f(x0))/h0`,
`d1 = (f(x2)-f(x1))/h1`, `a = (d1-d0)/(h1+h0)`, `b = a*h1 + d1`, `c = f(x2)`,
y `x3 = x2 - 2c/(b ± sqrt(b²-4ac))` eligiendo el signo que haga mayor el
denominador; luego desplaza `x0, x1, x2 = x1, x2, x3`.

Con `muller(lambda x: x**3 - 13*x - 12, 4.0, 5.0, 5.5)` debe devolver una raíz
cercana a `4.0` (el polinomio tiene raíces en $-3$, $-1$ y $4$).
