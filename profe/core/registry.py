# -*- coding: utf-8 -*-
"""
profe/core/registry.py — Catálogo de ejercicios y selección sembrada.

Cada método recibe SOLO las variantes que puede resolver: Müller necesita una
función y tres puntos iniciales; Bairstow, un polinomio y un factor
cuadrático de arranque. La selección usa el RNG del alumno, así que el
ejercicio es reproducible.
"""
from .modelos import _ej_bairstow_lti, _ej_muller_vibraciones
from .solvers import resolver

# Ejercicios disponibles por método (preguntas automáticas)
EJERCICIOS = {
    'MULLER': [_ej_muller_vibraciones],
    'BAIRSTOW': [_ej_bairstow_lti],
}

# Ejercicios específicos para la actividad realizada a mano
MANO_FABRICA = {
    'MULLER': [_ej_muller_vibraciones],
    'BAIRSTOW': [_ej_bairstow_lti],
}

NOMBRE_METODO = {
    'MULLER': 'Método de Müller',
    'BAIRSTOW': 'Método de Bairstow',
}

# Nombre EXACTO de la función que debe programar el alumno. Tiene que
# coincidir con la firma que anuncia su ficha de `profe/evaluador/`, porque el
# cuaderno declara esa función y la tarea la busca por nombre.
NOMBRE_FUNCION = {
    'MULLER': 'muller',
    'BAIRSTOW': 'bairstow',
}

METODOS_MANO = ('MULLER', 'BAIRSTOW')

# Qué se reporta en cada actividad a mano: una tupla (etiqueta, de dónde sale
# el valor de referencia). En Müller es la primera aproximación x3; en
# Bairstow, la corrección (Δr, Δs) del factor cuadrático. `cuaderno.py`
# imprime la lista y compara componente a componente.
MANO_REPORTE = {
    'MULLER': (
        ('x3', lambda ej: ej['x3']),
    ),
    'BAIRSTOW': (
        ('Δr', lambda ej: ej['dr']),
        ('Δs', lambda ej: ej['ds']),
    ),
}


def _sortear(fabricas, metodo, rng, es=None):
    """Sortea una variante con el RNG del alumno y la deja resuelta."""
    idx = int(rng.integers(0, len(fabricas)))
    return resolver(metodo, fabricas[idx](rng), es=es)


def elegir(metodo: str, rng, es=None):
    """Selecciona un ejercicio aleatorio del catálogo según el método y el RNG del alumno."""
    return _sortear(EJERCICIOS[metodo], metodo, rng, es=es)


def elegir_mano(metodo: str, rng, es=None):
    """Selecciona un ejercicio para la actividad manual según el método y el RNG del alumno."""
    return _sortear(MANO_FABRICA[metodo], metodo, rng, es=es)
