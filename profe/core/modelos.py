# -*- coding: utf-8 -*-
"""
profe/core/modelos.py — Fábricas de ejercicios de la Tarea 3B.

Cada fábrica sortea sus datos con el RNG del alumno (a través de los rangos
declarados en `profe/ejercicios/<nombre>.md`) y devuelve un diccionario con:

  * MULLER    `f` (la función), `x0`, `x1`, `x2` (los tres puntos iniciales)
              y `f_latex` (la función formateada para el enunciado)
  * BAIRSTOW  `a` (coeficientes del polinomio característico) y `r0`, `s0`
              (el factor cuadrático inicial  x^2 - r x - s)

Los números son ENTEROS (o a lo más un decimal en los puntos y arranques): la
actividad es a mano y con calculadora. La referencia del paso suelto
(`x3`, o `dr`/`ds`) la agrega `profe.core.solvers.resolver()`.
"""
from profe.core.helpers import _fmt, _poly_latex
from profe.core.markdown_loader import cargar_ejercicio_md, sustituir


def _func_poli(a):
    """f(x) = a_n x^n + ... + a_0 (versión término a término, para Müller)."""
    n = len(a) - 1

    def f(x):
        total = 0.0
        for i, c in enumerate(a):
            total += c * x ** (n - i)
        return total
    return f


# ---------------------------------------------------------------------
#  MÜLLER: parábola por tres puntos -> x3
# ---------------------------------------------------------------------
def _ej_muller_vibraciones(rng):
    """f(ω) = ω^3 - 13·ω - c  (resonancia de un chasis), raíz cerca de ω=4.

    b se fija en -13 y los tres puntos STRADDLEN la raíz (x0 por debajo, x1 por
    arriba), así la parábola cruza el eje y su x3 es SIEMPRE real: es el número
    que el alumno calcula a mano.
    """
    meta, ctx, d = cargar_ejercicio_md('muller_vibraciones.md', rng)
    b, c = -13, int(d['c'])
    a = [1, 0, b, -c]     # f(ω) = ω^3 - 13ω - c  (raíz positiva cerca de 4)
    f = _func_poli(a)
    x0, x1, x2 = d['x0'], d['x1'], d['x2']
    ctx = sustituir(ctx, polinomio=_poly_latex(a, var='\\omega'),
                    x0=_fmt(x0, 1), x1=_fmt(x1, 1), x2=_fmt(x2, 1))
    return {
        **meta,
        'contexto': ctx,
        'f': f,
        'f_latex': _poly_latex(a, var='\\omega'),
        'x0': float(x0), 'x1': float(x1), 'x2': float(x2),
        'datos': [],
    }


# ---------------------------------------------------------------------
#  BAIRSTOW: factor cuadrático x^2 - r x - s de un polinomio característico
# ---------------------------------------------------------------------
def _ej_bairstow_lti(rng):
    """P(s) = (s+p)(s+q)(s+t), polos estables; extrae el factor (s+p)(s+q)."""
    meta, ctx, d = cargar_ejercicio_md('bairstow_lti.md', rng)
    p, q, t = int(d['p']), int(d['q']), int(d['t'])
    if p == q == t:
        t += 1   # una raíz triple degenera el sistema 2x2 de Bairstow
    # (s+p)(s+q)(s+t) = s^3 + a2 s^2 + a1 s + a0
    a = [1, p + q + t, p * q + p * t + q * t, p * q * t]
    # Factor objetivo (s+p)(s+q) = s^2 + (p+q)s + pq  ->  x^2 - r x - s
    # con  r = -(p+q), s = -pq. El arranque es una perturbación de ese factor.
    r0 = -(p + q) + 0.5
    s0 = -(p * q) + 0.5
    ctx = sustituir(ctx, polinomio=_poly_latex(a, var='x'),
                    r0=_fmt(r0, 1), s0=_fmt(s0, 1))
    return {
        **meta,
        'contexto': ctx,
        'a': [float(c) for c in a],
        'r0': float(r0), 's0': float(s0),
        'grado': 3,
        'datos': [],
    }
