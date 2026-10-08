# -*- coding: utf-8 -*-
"""Genera U2_T3B.ipynb a partir de celdas nuevas + las celdas de A reutilizadas."""
import json

RUTA_A = r'o:\Mi unidad\CursoMN\U2_T3A\U2_T3A.ipynb'
RUTA_B = r'o:\Mi unidad\CursoMN\U2_T3B\U2_T3B.ipynb'

A = json.load(open(RUTA_A, encoding='utf-8'))


def src(c):
    s = c['source']
    return s if isinstance(s, str) else ''.join(s)


celda_config = next(c for c in A['cells']
                    if c['cell_type'] == 'code' and 'MODO_MOTOR' in src(c))
celda_id = next(c for c in A['cells']
                if c['cell_type'] == 'code' and 'generar_tarea(alumno_id)' in src(c))
celda_id_md = next(c for c in A['cells']
                   if c['cell_type'] == 'markdown' and 'Identifícate' in src(c))

CONFIG = src(celda_config).replace('U2_T3A', 'U2_T3B')
IDENT = src(celda_id)
IDENT_MD = src(celda_id_md)

MD = 'markdown'
PY = 'code'

celdas = []


def md(texto):
    celdas.append((MD, texto))


def py(texto):
    celdas.append((PY, texto))


# ============================== PORTADA =================================
md("""# U2_T3B · Métodos para raíces complejas: Müller y Bairstow

### Interpolación parabólica y factores cuadráticos

## ¿Qué vas a aprender?

Los métodos cerrados (bisección, falsa posición) y la secante solo encuentran
raíces **reales**: la línea que trazan en el plano real nunca toca una raíz
compleja. Aquí programas dos métodos que sí pueden: **Müller**, que ajusta una
**parábola** por tres puntos, y **Bairstow**, que extrae **factores
cuadráticos** de dos en dos. De paso aprendes a **deflactar** para encontrar
todas las raíces de un polinomio.

| # | Pregunta | Tipo | Puntos |
|---|---|---|---|
| 1 | Müller: la parábola por tres puntos | opción múltiple | 10 |
| 2 | Bairstow: factor cuadrático y deflación | opción múltiple | 10 |
| 3 | Programar `muller(f, x0, x1, x2, ...)` | código (casos ocultos) | 25 |
| 4 | La primera aproximación $\\omega_3$ | numérica | 10 |
| 5 | Programar `bairstow(a, r0, s0, ...)` | código (casos ocultos) | 25 |
| 6 | La corrección $(\\Delta r, \\Delta s)$ | 2 casillas | 10 |
| 7 | Comparación con `numpy.roots` | opción múltiple | 10 |

$$\\text{Calificación} = 0.70\\,(\\text{automático}) + 0.30\\,(\\text{2 actividades a mano})$$

Se requiere **$\\ge 90\\%$** de los 100 puntos automáticos para poder enviar.
""")

# ============================== CELDA 1 (config) =========================
py(CONFIG)

# ============================== IDENTIFICACIÓN ===========================
md(IDENT_MD)
py(IDENT)

# ============================== §1 MÜLLER ================================
md("""---
# 1 · Müller: una parábola por tres puntos

Los métodos **cerrados** y la **secante** trazan una línea entre dos puntos y
buscan dónde cruza el eje $x$. Eso solo sirve cuando la raíz es **real**: una
recta en el plano real nunca toca una raíz compleja.

El **método de Müller** reemplaza la recta por una **parábola** que pasa por
**tres** puntos $(x_0, x_1, x_2)$:

$$f_2(x) = a\\,(x - x_2)^2 + b\\,(x - x_2) + c$$

Al resolver $f_2(x) = 0$ la raíz **puede salir compleja** (cuando
$b^2 - 4ac < 0$), y el método la sigue iterando en el plano complejo. Por eso
Müller encuentra raíces que los métodos anteriores no pueden.

### Las diferencias y los coeficientes

Con $h_0 = x_1 - x_0$, $h_1 = x_2 - x_1$ y las pendientes incrementales
$\\delta_0 = \\frac{f(x_1)-f(x_0)}{h_0}$,
$\\delta_1 = \\frac{f(x_2)-f(x_1)}{h_1}$:

$$c = f(x_2),\\qquad a = \\frac{\\delta_1 - \\delta_0}{h_1 + h_0},\\qquad b = a\\,h_1 + \\delta_1$$

y la nueva aproximación es

$$x_3 = x_2 + \\frac{-2c}{b \\pm \\sqrt{b^2 - 4ac}}$$

eligiendo el signo $\\pm$ que **maximice la magnitud del denominador** (así se
toma la raíz de la parábola más cercana a $x_2$ y se evita la cancelación por
resta). Luego se desplazan los puntos $x_0 \\leftarrow x_1$, $x_1 \\leftarrow x_2$,
$x_2 \\leftarrow x_3$ y se repite.
""")

py("""#@title 🧪 Laboratorio · un paso de Müller, a la vista
import cmath

# Un polinomio cualquiera con una raíz real cerca de 4 (NO es el tuyo).
def f(x):
    return x**3 - 13*x - 12        # raíces: -3, -1, 4

x0, x1, x2 = 3.2, 4.8, 4.1

f0, f1, f2 = f(x0), f(x1), f(x2)
h0, h1 = x1 - x0, x2 - x1
d0, d1 = (f1 - f0) / h0, (f2 - f1) / h1
a = (d1 - d0) / (h1 + h0)
b = a * h1 + d1
c = f2

print("f(x0..x2) = %.4f, %.4f, %.4f" % (f0, f1, f2))
print("h0 = %.3f   h1 = %.3f   d0 = %.4f   d1 = %.4f" % (h0, h1, d0, d1))
print("parábola:  a = %.4f   b = %.4f   c = %.4f" % (a, b, c))

disc = cmath.sqrt(b*b - 4*a*c)
den = b + disc if abs(b + disc) > abs(b - disc) else b - disc
x3 = x2 - 2*c / den
print("x3 =", x3, "   (discriminante =", disc, ")")

# Y ahora la iteración completa, hasta la raíz:
raiz, nit = muller_referencia(f, x0, x1, x2, tol=1e-9)
print()
print("Müller converge a  x = %.6f  en %d iteraciones" % (raiz, nit))
print("  |f(x)| = %.2e" % abs(f(raiz)))
""")

py("""#@title 🧪 Pregunta 1 · Müller: la parábola por tres puntos
pregunta(1)
""")

# ============================== §2 BAIRSTOW ==============================
md("""---
# 2 · Bairstow: extraer un factor cuadrático

En lugar de buscar las raíces de una en una, Bairstow extrae del polinomio un
**factor cuadrático** $x^2 - r x - s$, y con él saca **dos raíces a la vez**
(reales o complejas conjugadas). Ajusta $r$ y $s$ con un **Newton de dos
variables**:

1. **Primera división** por $x^2 - r x - s$:
   $b_k = a_k + r\\,b_{k-1} + s\\,b_{k-2}$ (el residuo son los dos últimos:
   $b_1$ y $b_0$).
2. **Segunda división** sobre los $b_k$:
   $c_k = b_k + r\\,c_{k-1} + s\\,c_{k-2}$ (dan las derivadas parciales del
   residuo).
3. **Sistema $2\\times 2$** (con $c_1, c_2, c_3$ y $b_1, b_0$):

$$\\begin{bmatrix} c_2 & c_3 \\\\ c_1 & c_2 \\end{bmatrix}
\\begin{bmatrix} \\Delta r \\\\ \\Delta s \\end{bmatrix} =
\\begin{bmatrix} -b_1 \\\\ -b_0 \\end{bmatrix}$$

4. Actualiza $r \\leftarrow r + \\Delta r$, $s \\leftarrow s + \\Delta s$ y repite.
5. Al converger, las dos raíces del factor son
   $x_{1,2} = \\frac{r \\pm \\sqrt{r^2 + 4s}}{2}$; **deflacta** (baja dos
   grados) y repite con el polinomio reducido hasta agotar el grado.
""")

py("""#@title 🧪 Laboratorio · Bairstow paso a paso y todas las raíces

# Un polinomio cualquiera con raíces reales (NO es el tuyo).
a = [1, 6, 11, 6]              # (x+1)(x+2)(x+3)
r, s = -2.5, -1.5              # factor inicial  x^2 - r x - s

n = len(a) - 1
b = [0.0] * (n + 1); b[0] = a[0]; b[1] = a[1] + r * b[0]
for k in range(2, n + 1):
    b[k] = a[k] + r * b[k - 1] + s * b[k - 2]

c = [0.0] * (n + 1); c[0] = b[0]; c[1] = b[1] + r * c[0]
for k in range(2, n + 1):
    c[k] = b[k] + r * c[k - 1] + s * c[k - 2]

b0, b1 = b[n], b[n - 1]
c1, c2, c3 = c[n - 1], c[n - 2], c[n - 3]
D = c2 * c2 - c1 * c3
dr = (b0 * c3 - b1 * c2) / D
ds = (b1 * c1 - b0 * c2) / D

print("b =", b, "    c =", c)
print("Δr = %.6f    Δs = %.6f" % (dr, ds))
print("factor corregido:  r = %.6f,  s = %.6f" % (r + dr, s + ds))

# Todas las raíces, por Bairstow y por numpy.roots:
clave = lambda z: (complex(z).real, complex(z).imag)
raices, nit = bairstow_referencia(a, r, s, tol=1e-9)
print()
print("Bairstow   :", sorted(raices, key=clave))
print("numpy.roots :", sorted(raices_de(a), key=clave))
print("  (%d iteraciones)" % nit)
""")

py("""#@title 🧪 Pregunta 2 · Bairstow: factor cuadrático y deflación
pregunta(2)
""")

# ============================== §3 MÜLLER A MANO =========================
md("""---
# 3 · Actividad a mano · Müller: la primera aproximación $\\omega_3$

Aquí abajo está **tu** función y tus tres puntos iniciales. Vas a calcular, a
mano y con calculadora:

1. Evalúa $f$ en los tres puntos.
2. Calcula $h_0, h_1$ y las pendientes $\\delta_0, \\delta_1$.
3. Arma la parábola ($a, b, c$) y calcula
   $x_3 = x_2 + \\frac{-2c}{b \\pm \\sqrt{b^2-4ac}}$ eligiendo el signo que dé
   el mayor denominador.

Después reporta $\\omega_3$ en la celda que sigue. **No redondees los pasos
intermedios**.
""")

py("""#@title ✏️✅ Müller · actividad a mano, práctica y preguntas
EJ_MU = mano_enunciado('MULLER')
""")

py("""# ---------------------------------------------------------------------
#  Escribe aqui tu PRIMERA aproximación y vuelve a ejecutar esta celda.
# ---------------------------------------------------------------------
MIS_MU = [0.0]          # <-- [omega_3]

mano_comprueba('MULLER', MIS_MU)
""")

md("""---
### 💻 Pregunta 3 · programa el método de Müller

```python
muller(f, x0, x1, x2, tol=1e-6, max_iter=100)  ->  (raiz, n_iter)
```

* `f` — la función a la que buscas la raíz; `x0, x1, x2` — los tres puntos
  iniciales;
* devuelve la raíz (real o compleja) y el número de iteraciones.
""")

py("""#@title Pregunta 3 · programar muller con casos ocultos
pregunta(3)
""")

py("""# --- Práctica: programa el método de Müller --------------------------
import cmath

def muller(f, x0, x1, x2, tol=1e-6, max_iter=100):
    # 1) h0 = x1-x0 ; h1 = x2-x1
    # 2) d0 = (f(x1)-f(x0))/h0 ; d1 = (f(x2)-f(x1))/h1
    # 3) a = (d1-d0)/(h1+h0) ; b = a*h1 + d1 ; c = f(x2)
    # 4) disc = cmath.sqrt(b*b - 4*a*c) ; elige el signo que haga mayor |b ± disc|
    # 5) x3 = x2 - 2*c/(b ± disc) ; desplaza x0,x1,x2 = x1,x2,x3 y repite
    # 6) detente cuando |f(x3)| < tol (o |x3-x2| < tol) o llegues a max_iter
    # return (raiz, n_iter)
    raise NotImplementedError("Completa la función muller")   # borra esta línea


# --- Prueba con TU ejercicio -----------------------------------------
try:
    raiz, nit = muller(EJ_MU['f'], EJ_MU['x0'], EJ_MU['x1'], EJ_MU['x2'])
    print("raíz ≈", raiz, "   |f(raíz)| =", abs(EJ_MU['f'](raiz)), "  (%d iter)" % nit)
except NotImplementedError as exc:
    print("Todavía no terminas la función:", exc)
except Exception as exc:
    print("Tu función falló:", exc)
""")

md("""---
### ✏️ Pregunta 4 · la primera aproximación de tu ejercicio

Ya calculaste $\\omega_3$ a mano y programaste el método. Contesta con el número
de **tu** ejercicio (el mismo que reportaste en `MIS_MU`).
""")

py("""pregunta(4)      # la primera aproximación omega_3
""")

# ============================== §4 BAIRSTOW A MANO =======================
md("""---
# 4 · Bairstow: el factor cuadrático y su corrección

Con el **método de Bairstow** extraes del polinomio un factor $x^2 - r x - s$.
Vas a calcular **una iteración** a mano:

1. **Primera división** por $x^2 - r x - s$ (obtienes $b_k$ y el residuo).
2. **Segunda división** sobre los $b_k$ (obtienes $c_k$).
3. Resuelve el sistema $2\\times 2$ para la corrección $(\\Delta r, \\Delta s)$.

Después reporta $\\Delta r$ y $\\Delta s$ en la celda que sigue.
""")

py("""#@title ✏️✅ Bairstow · actividad a mano y pregunta
EJ_BA = mano_enunciado('BAIRSTOW')
""")

py("""# ---------------------------------------------------------------------
#  Escribe aqui los DOS valores de la corrección, en el orden del
#  enunciado: primero Δr y luego Δs.
# ---------------------------------------------------------------------
MIS_BA = [0.0, 0.0]          # <-- [Δr, Δs]

mano_comprueba('BAIRSTOW', MIS_BA)
""")

md("""---
### 💻 Pregunta 5 · programa el método de Bairstow

```python
bairstow(a, r0, s0, tol=1e-6, max_iter=100)  ->  (lista_de_raices, n_iter)
```

* `a` — la lista de coeficientes de mayor a menor grado; `r0, s0` — el factor
  cuadrático inicial;
* devuelve TODAS las raíces (reales y complejas) y el total de iteraciones.
""")

py("""#@title Pregunta 5 · programar bairstow con casos ocultos
pregunta(5)
""")

py("""# --- Práctica: programa el método de Bairstow ------------------------
def bairstow(a, r0, s0, tol=1e-6, max_iter=100):
    # Mientras quede un polinomio de grado >= 3:
    #   1) itera: dos divisiones sintéticas -> (Δr, Δs) -> actualiza r, s
    #   2) al converger, las raíces del factor son (r ± sqrt(r^2+4s))/2
    #   3) deflacta (baja 2 grados) y repite
    # Al final resuelve lo que queda (lineal o cuadrático) directamente.
    # return (lista_de_todas_las_raices, n_iter)
    raise NotImplementedError("Completa la función bairstow")   # borra esta línea


# --- Prueba con TU ejercicio -----------------------------------------
try:
    clave = lambda z: (complex(z).real, complex(z).imag)
    raices, nit = bairstow(EJ_BA['a'], EJ_BA['r0'], EJ_BA['s0'])
    print("raíces =", sorted(raices, key=clave), "  (%d iter)" % nit)
    print("numpy  =", sorted(raices_de(EJ_BA['a']), key=clave))
except NotImplementedError as exc:
    print("Todavía no terminas la función:", exc)
except Exception as exc:
    print("Tu función falló:", exc)
""")

md("""---
### ✏️ Pregunta 6 · la corrección de tu ejercicio

Ya calculaste $(\\Delta r, \\Delta s)$ a mano. Contesta con los dos números de
**tu** ejercicio (los mismos que reportaste en `MIS_BA`).
""")

py("""pregunta(6)      # la corrección (Δr, Δs)
""")

# ============================== §5 CONCLUSIONES ==========================
md("""---
# 5 · Conclusiones

## Lo que hay que llevarse

1. **Los métodos cerrados y la secante no hallan raíces complejas**: la recta
   que trazan en el plano real nunca cruza una raíz compleja. Müller lo resuelve
   con una **parábola** (cuyas raíces sí pueden ser complejas) y Bairstow con un
   **factor cuadrático**.
2. **Müller es la secante con un punto más**: en lugar de una recta por dos
   puntos, una parábola por tres. La nueva aproximación es
   $x_3 = x_2 - \\frac{2c}{b \\pm \\sqrt{b^2-4ac}}$, con el signo que maximiza el
   denominador.
3. **Bairstow es un Newton de dos variables sobre $(r, s)$**: las dos divisiones
   sintéticas dan el residuo y su Jacobiano, y la corrección sale de un sistema
   $2\\times 2$.
4. **Deflactar** (bajar el grado tras cada factor) es lo que permite encontrar
   **todas** las raíces sin volver a caer en las ya encontradas.
5. **`numpy.roots`** hace todo esto por ti y más rápido: programar los métodos
   sirve para **entenderlos** y para cuando no tengas `numpy` (un
   microcontrolador, por ejemplo).

## Autoevaluación rápida

* ¿Por qué la secante no puede acercarse a una raíz compleja?
* ¿Qué pasa en Müller si $b^2 - 4ac < 0$?
* ¿Qué son $c_1, c_2, c_3$ en el sistema de Bairstow?
* Si al deflactar el residuo no es cero, ¿qué significa?
* ¿Cuándo conviene tu propio método frente a `numpy.roots`?

---

### ✏️ Pregunta 7
""")

py("""#@title 🧪 Pregunta 7 · comparación con numpy.roots
pregunta(7)
""")

# ============================== §6 ENTREGA ===============================
md("""---
# 6 · Entrega

## Antes de enviar

1. **Revisa tus 7 preguntas.** Si alguna está en blanco el sistema la cuenta
   como error.
2. **Completa `muller` y `bairstow`.** Se prueban con polinomios que nunca ves.
3. **Imprime la hoja de trabajo manual** (celda de abajo). Va junto con tu
   cuaderno: ahí aparecen los valores que reportaste y los de referencia, para
   que tu profesor califique rápido las 2 rúbricas (30 % de la calificación).
4. Necesitas **$\\ge 90\\%$** de los 100 puntos automáticos para poder enviar.

| Sección | Actividad a mano | ¿La reportaste? |
|---|---|---|
| 3 | Müller: la primera aproximación $\\omega_3$ | `MIS_MU` |
| 4 | Bairstow: la corrección $(\\Delta r, \\Delta s)$ | `MIS_BA` |

---

## Las tres celdas del final

| Celda | Qué hace | Cuántas veces |
|---|---|---|
| 📝 **Calificar** | revisa tus respuestas y te dice cuántos puntos llevas. **No envía nada.** | las que quieras |
| 📤 **Enviar** | manda tu calificación a la hoja del profesor. | **solo 2 intentos** |
| 🔎 **Comprobar** | lee lo que la hoja ya tiene guardado de ti. **No envía nada.** | las que quieras |

La **nota final** es $0.70\\,(\\text{automático})+0.30\\,(\\text{manual})$. **Calificar
no gasta intentos**: corrige y vuelve a calificar las veces que necesites antes de
enviar.
""")

py("""#@title 📋 Hoja de trabajo manual (entrégala con tu cuaderno)
hoja_manual()
""")

py("""#@title 📝 Calificar (sin enviar) — úsala las veces que quieras
puntos, maximo = calificar()
""")

py("""#@title 📤 Enviar la calificación (máximo 2 intentos)
enviar(alumno_id)
""")

py("""#@title 🔎 Comprobar lo que ya está guardado (no envía nada)
consultar_calificacion()
""")


# ============================== ESCRIBIR ================================
def a_celda(tipo, texto):
    fuente = texto.splitlines(keepends=True)
    if tipo == MD:
        return {'cell_type': 'markdown', 'metadata': {}, 'source': fuente}
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {},
            'outputs': [], 'source': fuente}


nb = {
    'cells': [a_celda(t, s) for t, s in celdas],
    'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'},
    },
    'nbformat': 4,
    'nbformat_minor': 5,
}

json.dump(nb, open(RUTA_B, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('Escrito', RUTA_B, 'con', len(nb['cells']), 'celdas')
