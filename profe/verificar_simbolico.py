# -*- coding: utf-8 -*-
"""
profe/verificar_simbolico.py — Verificación matemática de la Tarea 3B.

Comprueba, con sympy y numpy, que:

  1. `solvers.muller` converge a una raíz (|f(raíz)| ~ 0) de polinomios con
     raíces enteras conocidas;
  2. `solvers.bairstow` devuelve TODAS las raíces (reales y complejas) y estas
     coinciden con `numpy.roots`, en cualquier orden;
  3. `bairstow_paso` es autoconsistente: su (Δr, Δs) resuelve el sistema 2x2
     que se arma con los b y c que él mismo calculó;
  4. el POLINOMIO QUE MUESTRA EL ENUNCIADO es el mismo con el que se calcula
     (la función `f` coincide con su LaTeX, y los coeficientes de Bairstow
     coinciden con su `$$P(x) = ...$$`).

Uso:  python profe/verificar_simbolico.py
"""
import os
import re
import sys

import numpy as np
import sympy as sp

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from profe.core import elegir_mano, obtener_rng                  # noqa: E402
from profe.core.solvers import bairstow, bairstow_paso, muller    # noqa: E402

X = sp.Symbol('x')
CASOS = 120
POLINOMIO_MULLER = re.compile(r'\$\$f\(\\omega\) = (.+?) = 0\$\$', re.S)
POLINOMIO_BAIRSTOW = re.compile(r'\$\$P\(x\) = (.+?) = 0\$\$', re.S)


def latex_a_sympy(texto):
    """`x^{3} - 13x - 12` -> polinomio de sympy (en la variable x)."""
    texto = texto.strip().replace('\\,', '')
    texto = texto.replace('\\omega', 'x')
    texto = re.sub(r'\^\{(\d+)\}', r'**\1', texto)
    texto = re.sub(r'(\d)\s*([a-zA-Z])', r'\1*\2', texto)
    return sp.expand(sp.sympify(texto))


def main():
    avisos = []

    # 1) Müller contra raíces enteras ------------------------------------
    fallas_muller = 0
    for s in range(CASOS):
        rng = np.random.default_rng(s)
        p, q, t = (int(rng.integers(1, 4)) for _ in range(3))
        a = [1, -(p + q + t), p * q + p * t + q * t, -p * q * t]

        def f(x, _a=a):
            return x**3 + _a[1] * x**2 + _a[2] * x + _a[3]

        raiz, nit = muller(f, p + 1.0, p + 1.5, p + 1.2, tol=1e-9, max_iter=200)
        if abs(f(raiz)) > 1e-6:
            fallas_muller += 1
            avisos.append('muller no converge: a=%s -> |f(%s)|=%g'
                          % (a, raiz, abs(f(raiz))))
    print('Müller: %d cubos con raíces enteras' % CASOS)
    print('   fallos de convergencia = %d' % fallas_muller)

    # 2) Bairstow contra numpy.roots --------------------------------------
    fallas_b = 0
    for s in range(CASOS):
        rng = np.random.default_rng(1000 + s)
        p, q, t = (int(rng.integers(1, 4)) for _ in range(3))
        if p == q == t:
            t += 1
        a = [1, p + q + t, p * q + p * t + q * t, p * q * t]
        raices, nit = bairstow(a, -(p + q) + 0.5, -(p * q) + 0.5,
                               tol=1e-9, max_iter=200)
        ref = sorted(np.roots(a), key=lambda z: (round(z.real, 6), round(z.imag, 6)))
        got = sorted(raices, key=lambda z: (round(z.real, 6), round(z.imag, 6)))
        if len(got) != len(ref) or any(abs(complex(g) - complex(r)) > 1e-5
                                       for g, r in zip(got, ref)):
            fallas_b += 1
            avisos.append('bairstow no da las raíces de %s: %s' % (a, got))
    print('Bairstow: %d cubos contra numpy.roots' % CASOS)
    print('   fallos = %d' % fallas_b)

    # 3) bairstow_paso autoconsistente ------------------------------------
    a = [1, 6, 11, 6]
    r, s = -2.5, -1.5
    paso = bairstow_paso(a, r, s)
    b, c = paso['b'], paso['c']
    n = len(a) - 1
    b0, b1 = b[n], b[n - 1]
    c1, c2, c3 = c[n - 1], c[n - 2], c[n - 3]
    det = c2 * c2 - c1 * c3
    dr = (b0 * c3 - b1 * c2) / det
    ds = (b1 * c1 - b0 * c2) / det
    if abs(dr - paso['dr']) > 1e-12 or abs(ds - paso['ds']) > 1e-12:
        avisos.append('bairstow_paso inconsistente con su propio sistema 2x2')

    # 4) el polinomio del ENUNCIADO coincide con el que se calcula ---------
    revisados = 0
    for metodo in ('MULLER', 'BAIRSTOW'):
        for nc in ('16330887', '21150001', '19999999', '18000001', '20060042'):
            rng_m = obtener_rng(nc, 'U2_T3B', 'mano', metodo)
            ej = elegir_mano(metodo, rng_m)
            revisados += 1
            if metodo == 'MULLER':
                m = POLINOMIO_MULLER.search(ej['contexto'])
                if not m:
                    avisos.append('MULLER/%s: el enunciado no muestra $$f(ω)=...$$' % nc)
                    continue
                P = latex_a_sympy(m.group(1))
                for xv in (0.0, 1.0, 2.0, 3.0):
                    if abs(float(P.subs(X, xv)) - ej['f'](xv)) > 1e-9:
                        avisos.append('MULLER/%s: f y su LaTeX no coinciden en x=%g'
                                      % (nc, xv))
                        break
            else:
                m = POLINOMIO_BAIRSTOW.search(ej['contexto'])
                if not m:
                    avisos.append('BAIRSTOW/%s: el enunciado no muestra $$P(x)=...$$' % nc)
                    continue
                P = latex_a_sympy(m.group(1))
                n = len(ej['a']) - 1
                ref = sp.expand(sum(sp.Rational(c) * X ** (n - i)
                                    for i, c in enumerate(ej['a'])))
                if sp.expand(P - ref) != 0:
                    avisos.append('BAIRSTOW/%s: el enunciado dice %s y los '
                                  'coeficientes son %s'
                                  % (nc, m.group(1), ej['a']))
    print('Polinomios del enunciado re-parseados: %d' % revisados)

    print()
    print('=' * 74)
    if avisos:
        for aviso in avisos[:25]:
            print('AVISO: %s' % aviso)
        print(' RESULTADO: %d AVISOS' % len(avisos))
        print('=' * 74)
        return 1
    print(' RESULTADO: TODO OK  (0 avisos)')
    print('=' * 74)
    return 0


if __name__ == '__main__':
    sys.exit(main())
