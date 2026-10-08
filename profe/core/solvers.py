# -*- coding: utf-8 -*-
"""
profe/core/solvers.py — Algoritmos de referencia de la Tarea 3B.

Dos métodos iterativos para raíces (reales y complejas):

  MULLER     ajusta una parábola por tres puntos y salta a su raíz más
             cercana; con aritmética compleja encuentra raíces complejas.
  BAIRSTOW   extrae factores cuadráticos x^2 - r x - s por pares (Newton 2x2
             sobre las dos divisiones sintéticas) y deflacta hasta agotar
             el grado.

Cada uno, además de la función completa, expone su PASO SUELTO
(`muller_paso` y `bairstow_paso`), que es lo que el alumno calcula a mano en
la actividad: la parábola + x3, o las dos divisiones + (Δr, Δs).
"""
import cmath


MAX_ITER = 100
ES_DEFECTO = 1e-6   # tolerancia por omisión de los métodos iterativos


def _real(z):
    """Un complejo a float si su parte imaginaria es redondeo (|Im| ~ 0)."""
    z = complex(z)
    if abs(z.imag) <= 1e-12 * max(1.0, abs(z.real)):
        return float(z.real)
    return z


# =====================================================================
#  MÜLLER
# =====================================================================
def muller_paso(f, x0, x1, x2):
    """
    Un paso de Müller: la parábola por (x0,f0),(x1,f1),(x2,f2) y su raíz más
    cercana a x2.

    Devuelve las diferencias y los coeficientes de la parábola, además de x3:

        h0, h1, d0, d1          diferencias y pendientes incrementales
        a_par, b_par, c_par     parábola f2(x) = a(x-x2)^2 + b(x-x2) + c
        x3                      la aproximación siguiente (real o compleja)
    """
    f0, f1, f2 = complex(f(x0)), complex(f(x1)), complex(f(x2))
    h0 = x1 - x0
    h1 = x2 - x1
    d0 = (f1 - f0) / h0
    d1 = (f2 - f1) / h1
    a_par = (d1 - d0) / (h1 + h0)
    b_par = a_par * h1 + d1
    c_par = f2

    # El signo se elige para que el denominador tenga la mayor magnitud: así
    # se toma la raíz de la parábola más cercana a x2 (estabilidad numérica).
    disc = cmath.sqrt(b_par * b_par - 4.0 * a_par * c_par)
    den = b_par + disc if abs(b_par + disc) > abs(b_par - disc) else b_par - disc
    dx = -2.0 * c_par / den
    x3 = x2 + dx

    return {
        'h0': _real(h0), 'h1': _real(h1),
        'd0': _real(d0), 'd1': _real(d1),
        'a_par': _real(a_par), 'b_par': _real(b_par),
        'c_par': _real(c_par), 'x3': _real(x3),
    }


def muller(f, x0, x1, x2, tol=1e-6, max_iter=MAX_ITER):
    """
    Método de Müller completo:  (raíz, n_iteraciones).

    Devuelve la raíz (real o compleja, según convenga) y el número de
    iteraciones. Con tres puntos iniciales y aritmética compleja converge a
    raíces que el método de la secante no puede alcanzar.
    """
    x0, x1, x2 = complex(x0), complex(x1), complex(x2)
    for it in range(1, int(max_iter) + 1):
        paso = muller_paso(f, x0, x1, x2)
        x3 = paso['x3']
        if abs(f(x3)) < tol or abs(x3 - x2) < tol * max(1.0, abs(x3)):
            return _real(x3), it
        x0, x1, x2 = x1, x2, x3
    return _real(x2), int(max_iter)


# =====================================================================
#  BAIRSTOW
# =====================================================================
def bairstow_paso(a, r, s):
    """
    Un paso de Bairstow: dos divisiones sintéticas cuadráticas y la
    corrección (Δr, Δs) del factor  x^2 - r x - s.

    Devuelve las dos filas de la división (`b` y `c`), la corrección y el
    factor corregido:

        b, c               primera y segunda división sintética
        dr, ds             la corrección de Newton 2x2
        r_new, s_new       r + dr, s + ds
    """
    n = len(a) - 1

    # 1) primera división:  b_k = a_k + r b_{k-1} + s b_{k-2}
    b = [0.0] * (n + 1)
    b[0] = a[0]
    if n >= 1:
        b[1] = a[1] + r * b[0]
    for k in range(2, n + 1):
        b[k] = a[k] + r * b[k - 1] + s * b[k - 2]

    # 2) segunda división (sobre los b):  c_k = b_k + r c_{k-1} + s c_{k-2}
    c = [0.0] * (n + 1)
    c[0] = b[0]
    if n >= 1:
        c[1] = b[1] + r * c[0]
    for k in range(2, n + 1):
        c[k] = b[k] + r * c[k - 1] + s * c[k - 2]

    # 3) sistema 2x2  [ c2 c3 ; c1 c2 ][Δr ; Δs] = [ -b1 ; -b0 ]
    b0, b1 = b[n], b[n - 1]
    c1, c2, c3 = c[n - 1], c[n - 2], c[n - 3]
    det = c2 * c2 - c1 * c3
    dr = (b0 * c3 - b1 * c2) / det
    ds = (b1 * c1 - b0 * c2) / det

    return {'b': b, 'c': c, 'dr': dr, 'ds': ds,
            'r_new': r + dr, 's_new': s + ds}


def _raices_factor(r, s):
    """Las dos raíces de  x^2 - r x - s = 0."""
    disc = cmath.sqrt(r * r + 4.0 * s)
    return _real((r + disc) / 2.0), _real((r - disc) / 2.0)


def _raices_quadratica(a):
    """Raíces de  a[0] x^2 + a[1] x + a[2] = 0."""
    A, B, C = a[0], a[1], a[2]
    disc = cmath.sqrt(B * B - 4.0 * A * C)
    return _real((-B + disc) / (2.0 * A)), _real((-B - disc) / (2.0 * A))


def bairstow(a, r0, s0, tol=1e-6, max_iter=MAX_ITER):
    """
    Método de Bairstow completo:  (lista_de_todas_las_raices, n_iter).

    Extrae un factor cuadrático x^2 - r x - s, deflacta el polinomio (baja 2
    grados) y repite hasta agotarlo; al final resuelve lo que queda (lineal o
    cuadrático) de forma directa. Devuelve TODAS las raíces (reales y
    complejas) y el número total de iteraciones.
    """
    a = [float(c) for c in a]
    r, s = float(r0), float(s0)
    raices, n_iter = [], 0

    while len(a) > 3:
        n = len(a) - 1
        b = None
        for _ in range(int(max_iter)):
            paso = bairstow_paso(a, r, s)
            r, s = paso['r_new'], paso['s_new']
            b = paso['b']
            n_iter += 1
            if (abs(paso['dr']) < tol * max(1.0, abs(r))
                    and abs(paso['ds']) < tol * max(1.0, abs(s))):
                break
        raices.extend(_raices_factor(r, s))
        # Deflactar: el cociente son los b sin los dos últimos (el residuo).
        a = b[:n - 1]
        r, s = -0.5, -0.5

    if len(a) == 3:
        raices.extend(_raices_quadratica(a))
    elif len(a) == 2:
        raices.append(_real(-a[1] / a[0]))

    return raices, n_iter


# =====================================================================
#  RESOLUCIÓN DE UN EJERCICIO (la referencia que califica)
# =====================================================================
def resolver(metodo, ej, es=None):
    """
    Deja en el diccionario del ejercicio la referencia del paso a mano:

        MULLER    -> ej['x3']  (y la raíz completa, ej['raiz'])
        BAIRSTOW  -> ej['dr'], ej['ds']  (y todas las raíces, ej['raices'])
    """
    if metodo == 'MULLER':
        paso = muller_paso(ej['f'], ej['x0'], ej['x1'], ej['x2'])
        ej['x3'] = _real(paso['x3'])
        ej['_paso'] = paso
        ej['raiz'], ej['n_iter'] = muller(
            ej['f'], ej['x0'], ej['x1'], ej['x2'], tol=1e-9, max_iter=200)
    elif metodo == 'BAIRSTOW':
        paso = bairstow_paso(ej['a'], ej['r0'], ej['s0'])
        ej['dr'] = float(paso['dr'])
        ej['ds'] = float(paso['ds'])
        ej['_paso'] = paso
        ej['raices'], ej['n_iter'] = bairstow(
            ej['a'], ej['r0'], ej['s0'], tol=1e-9, max_iter=200)
    else:
        raise ValueError('Método desconocido: %s' % (metodo,))
    return ej
