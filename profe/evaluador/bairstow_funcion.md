---
funcion: bairstow
firma: "bairstow(a, r0, s0, tol=1e-6, max_iter=100)"
salida: raices
ejemplo: "bairstow(EJ_BA['a'], EJ_BA['r0'], EJ_BA['s0'])"
---

Programa el **método de Bairstow**: extrae del polinomio un factor cuadrático
$x^2 - r x - s$ por medio de dos divisiones sintéticas y una corrección de
Newton de dos variables; cuando convergen $r$ y $s$, calcula las dos raíces de
ese factor, **deflacta** el polinomio (baja dos grados) y repite hasta agotar
el grado.

Tu función recibe:

* `a` — la lista de coeficientes **de mayor a menor grado** (el polinomio
  tiene grado $n = \text{len}(a)-1$)
* `r0, s0` — el factor cuadrático inicial $x^2 - r x - s$
* `tol` — la tolerancia del criterio de paro (por omisión `1e-6`)
* `max_iter` — el número máximo de iteraciones por factor (por omisión `100`)

y devuelve **una tupla con dos elementos**: `(lista_de_todas_las_raices, n_iter)`,
donde la lista contiene **todas** las raíces (reales y complejas) y `n_iter`
el número total de iteraciones.
