---
funcion: bairstow
firma: "bairstow(a, r0, s0, tol=1e-6, max_iter=100)"
salida: raices
ejemplo: "bairstow([1, 6, 11, 6], -2.5, -1.5)"
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

En cada iteración: `b_k = a_k + r·b_{k-1} + s·b_{k-2}` (primera división),
`c_k = b_k + r·c_{k-1} + s·c_{k-2}` (segunda), y con
$c_1{=}c_{n-1},\ c_2{=}c_{n-2},\ c_3{=}c_{n-3}$ y $b_1{=}b_{n-1},\ b_0{=}b_n$
resuelves el sistema $2\times2$ para $(\Delta r, \Delta s)$ y actualizas
$r \leftarrow r + \Delta r$, $s \leftarrow s + \Delta s$.

Con `bairstow([1, 6, 11, 6], -2.5, -1.5)` debe devolver las raíces $-1$, $-2$
y $-3$ (el polinomio es $(x+1)(x+2)(x+3)$).
