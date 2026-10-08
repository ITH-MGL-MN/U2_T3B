# -*- coding: utf-8 -*-
"""
probador.py — Herramienta local para inspeccionar un ejercicio por NC.

    python probador.py                        # NC y método por omisión
    python probador.py 16330887 MULLER        # número de control y método
    python probador.py 16330887 BAIRSTOW mano # el de la actividad a mano

Muestra el enunciado tal como lo ve el alumno y los valores de referencia que
usa el motor para calificar (x3 en Müller; Δr, Δs en Bairstow).
"""
import sys

from profe.config import buscar, obtener_configuracion
from profe.core import (MANO_REPORTE, METODOS_MANO, NOMBRE_METODO, elegir,
                        elegir_mano, obtener_rng)

NC_POR_OMISION = '16330887'
METODO_POR_OMISION = 'MULLER'


def id_tarea():
    cfg, _ = obtener_configuracion()
    return buscar(cfg, 'tarea.id', 'U2_T3B')


def _fmt(v):
    try:
        return '%g' % float(v)
    except (TypeError, ValueError):
        return str(v)


def probar_ejercicio(nc=NC_POR_OMISION, metodo=METODO_POR_OMISION, mano=False):
    metodo = metodo.upper()
    if metodo not in METODOS_MANO:
        print('Método desconocido: %r (usa uno de %s)'
              % (metodo, ', '.join(METODOS_MANO)))
        return 1

    tarea = id_tarea()
    partes = (nc, tarea, 'mano', metodo) if mano else (nc, tarea, metodo)
    rng = obtener_rng(*partes)
    ej = elegir_mano(metodo, rng) if mano else elegir(metodo, rng)

    print('=' * 68)
    print(' %s | NC: %s | %s' % (NOMBRE_METODO[metodo], nc,
                                 'actividad a mano' if mano else 'preguntas automáticas'))
    print('=' * 68)
    print('\nTÍTULO   : %s' % ej['titulo'])
    print('INCÓGNITA: %s [%s]' % (ej.get('incognita', '-'), ej.get('unidad', '-')))
    if metodo == 'MULLER':
        print('FUNCIÓN  : f(ω) = %s' % ej.get('f_latex', ''))
        print('PUNTOS   : x0 = %s, x1 = %s, x2 = %s'
              % (_fmt(ej['x0']), _fmt(ej['x1']), _fmt(ej['x2'])))
    else:
        print('POLINOMIO: a = %s' % ej['a'])
        print('ARRANQUE : r0 = %s, s0 = %s' % (_fmt(ej['r0']), _fmt(ej['s0'])))

    print('\n--- ENUNCIADO QUE VE EL ALUMNO ---')
    print(ej['contexto'].strip())
    print('----------------------------------')

    print('\nRespuestas de referencia (lo que se califica):')
    for etq, fn in MANO_REPORTE[metodo]:
        print('   %-8s = %.10g' % (etq, float(fn(ej))))
    if metodo == 'MULLER':
        print('   raíz (convergida) = %s   (%d iteraciones)'
              % (_fmt(ej['raiz']), ej['n_iter']))
    else:
        print('   raíces (convergidas) = %s   (%d iteraciones)'
              % (ej['raices'], ej['n_iter']))
    return 0


if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    nc = args[0] if args else NC_POR_OMISION
    metodo = args[1].upper() if len(args) > 1 else METODO_POR_OMISION
    mano = len(args) > 2 and args[2].lower().startswith('mano')
    sys.exit(probar_ejercicio(nc, metodo, mano))
