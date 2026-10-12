"""matlab_like — precarga NumPy / Matplotlib / SciPy con sabor a MATLAB.

La celda 1 del cuaderno lo ejecuta con `exec(..., globals())`, así que todo lo
que se defina aquí queda a mano del alumno:

    x = linspace(0, 10, 100)
    plot(x, sin(x))

A diferencia de la versión anterior, NO se usa `from numpy import *`:

  * ese import metía 804 nombres en el cuaderno, y
  * pisaba funciones de Python (`max`, `min`, `sum`, `abs`, `round`, `any`,
    `all`, `bool`) con las de NumPy, donde los argumentos significan otra cosa
    (`np.max(a, b)` lee `b` como un EJE, no como otro número).

Ahora se importa SOLO lo que hace falta, nombre por nombre; los 7 nombres que
NumPy comparte con Python (`abs`, `all`, `any`, `max`, `min`, `round`, `sum`)
se redefinen al final para que funcionen con números, con arreglos y con
objetos de SymPy; `bool` se deja el de Python (en NumPy sigue `np.bool_`); y
`np` / `plt` siguen disponibles para todo lo demás.
"""

import builtins as _py
import sys as _sys

import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
#  NumPy, nombre por nombre
# ---------------------------------------------------------------------
from numpy import (
    # arreglos y construcción
    array, arange, linspace, logspace, zeros, ones, eye, full,
    # matemáticas elemento a elemento
    sqrt, exp, log, log10, log2, sin, cos, tan, arcsin, arccos, arctan,
    arctan2, degrees, radians, sign,
    # constantes
    pi, e, inf, nan,
    # estadística y agregación
    mean, median, std, var, percentile, cumsum, diff, sort, argsort, ravel,
    # comparación y selección
    maximum, minimum, equal, clip, isfinite, isnan, pad,
    # polinomios y utilidades numéricas
    polyval, polyfit, roots, spacing, finfo, dot, c_, real, imag, reshape,
    transpose,
    # tipos numéricos
    float32, float64, int32, int64,
)

# ---------------------------------------------------------------------
#  Álgebra lineal y EDOs
# ---------------------------------------------------------------------
from numpy.linalg import det

try:
    from scipy.integrate import odeint, quad, solve_ivp
except ImportError:                                   # scipy es opcional
    pass

# ---------------------------------------------------------------------
#  Gráficas
# ---------------------------------------------------------------------
from matplotlib.pyplot import (
    axis, axhline, axvline, bar, boxplot, colorbar, figure, grid, hist,
    legend, loglog, plot, scatter, semilogx, semilogy, show, step,
    subplot, subplots, suptitle, text, tight_layout, title, xlabel, xlim,
    ylabel, ylim,
)

# Configuración visual estilo MATLAB
np.set_printoptions(precision=4, suppress=True, linewidth=120)
plt.rcParams['figure.figsize'] = (8, 6)

# Alias cortos estilo MATLAB
lin = linspace


# =====================================================================
#  Los nombres que NumPy comparte con Python
# =====================================================================
# `abs`, `all`, `any`, `max`, `min`, `round` y `sum` existen en NumPy Y en
# Python, con significados distintos. Importar las de NumPy rompía el cuaderno:
#
#     max(5, 200000)      -> AxisError: axis 200000 is out of bounds
#     max(x, 1e-12)       -> devolvía `x` sin avisar (1e-12 pasaba a ser el eje 0)
#     abs(sp.Symbol('x')) -> TypeError: SymPy no define __abs__
#
# Las de abajo miran el TIPO de la entrada y eligen:
#
#     escalares de Python/NumPy -> la de Python
#     arreglos y listas         -> la de NumPy (elemento a elemento)
#     objetos de SymPy          -> la de SymPy (simbólico)
#
# así que se usan igual que en MATLAB y que en Python:
#
#     max(a, b)            # el mayor de dos escalares, o elemento a elemento
#     max(secuencia)       # el mayor de la secuencia
#     max(a, axis=0)       # reducción por eje (NumPy)
#     max(secuencia, key=...)# igual que Python
#     max(x, y)            # Max(x, y) si x o y son de SymPy
#
# `bool` NO se reemplaza: se deja el de Python (en NumPy sigue `np.bool_`).
# =====================================================================
def _es_sympy(v):
    """¿Es un objeto de SymPy? (sin importar SymPy: mira de dónde viene)."""
    return type(v).__module__.split('.')[0] == 'sympy'


def _sympy():
    """El módulo SymPy, SOLO si el cuaderno ya lo importó."""
    return _sys.modules.get('sympy')


def _es_arreglo(v):
    return isinstance(v, np.ndarray)


def _es_secuencia(v):
    """Listas, tuplas y rangos: NumPy los convierte en arreglo."""
    return isinstance(v, (list, tuple, range))


def _es_escalar(v):
    return np.isscalar(v)


def _hay_sympy(args):
    """¿Algún argumento (o algún elemento de una lista) es de SymPy?"""
    for a in args:
        if _es_sympy(a):
            return True
        if _es_secuencia(a) and _py.any(_es_sympy(v) for v in a):
            return True
    return False


def _max_min(de_python, de_numpy, elemento_a_elemento, de_sympy, args, kwargs):
    # key= y default= son de la función de Python: max(secuencia, key=len)
    if 'key' in kwargs or 'default' in kwargs:
        return de_python(*args, **kwargs)
    # axis=, out=, keepdims=... son de NumPy: es una reducción
    if _py.any(k in kwargs for k in
               ('axis', 'out', 'keepdims', 'initial', 'where')):
        return de_numpy(*args, **kwargs)
    # Si hay SymPy de por medio, el resultado es simbólico
    if _hay_sympy(args):
        sp = _sympy()
        valores = args[0] if len(args) == 1 and _es_secuencia(args[0]) else args
        return de_sympy(sp, valores)
    # Un solo argumento: el mayor/menor de la secuencia
    if len(args) == 1:
        if _es_arreglo(args[0]) or _es_secuencia(args[0]):
            return de_numpy(args[0])
        return de_python(args[0])
    # Dos argumentos: escalares -> comparar; con un arreglo -> elemento a elemento
    if len(args) == 2:
        if _es_escalar(args[0]) and _es_escalar(args[1]):
            return de_python(*args)
        return elemento_a_elemento(*args)
    # Tres o más: comparar, como la función de Python
    return de_python(*args)


def max(*args, **kwargs):
    """max(a, b) / max(secuencia) / max(a, axis=...) — Python, NumPy y SymPy."""
    return _max_min(_py.max, np.max, np.maximum,
                    lambda sp, valores: sp.Max(*valores), args, kwargs)


def min(*args, **kwargs):
    """min(a, b) / min(secuencia) / min(a, axis=...) — Python, NumPy y SymPy."""
    return _max_min(_py.min, np.min, np.minimum,
                    lambda sp, valores: sp.Min(*valores), args, kwargs)


def abs(x, *args):
    """abs(x) — valor absoluto (elemento a elemento en arreglos, |x| en SymPy)."""
    if _es_sympy(x):
        return _sympy().Abs(x)
    if _es_arreglo(x) or _es_secuencia(x):
        return np.abs(x)
    return _py.abs(x, *args)


def round(x, ndigits=None):
    """round(x[, n]) — a n decimales (elemento a elemento en arreglos)."""
    if _es_arreglo(x) or _es_secuencia(x):
        return np.round(x, 0 if ndigits is None else ndigits)
    if ndigits is None:
        return _py.round(x)
    return _py.round(x, ndigits)


def sum(iterable, *args, **kwargs):
    """sum(iterable[, inicio]) — suma; en arreglos reduce (acepta axis=)."""
    if _es_arreglo(iterable) or kwargs:
        return np.sum(iterable, *args, **kwargs)
    return _py.sum(iterable, *args)


def any(iterable, *args, **kwargs):
    """any(iterable) — ¿alguno es verdadero? (en arreglos acepta axis=)."""
    if _es_arreglo(iterable) or kwargs:
        return np.any(iterable, *args, **kwargs)
    return _py.any(iterable)


def all(iterable, *args, **kwargs):
    """all(iterable) — ¿todos verdaderos? (en arreglos acepta axis=)."""
    if _es_arreglo(iterable) or kwargs:
        return np.all(iterable, *args, **kwargs)
    return _py.all(iterable)
