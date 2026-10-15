# -*- coding: utf-8 -*-
"""
profe/verificar_tarea.py — Verificación del motor sobre muchos números de control.

Comprueba que, para cada NC:

  1. la tarea se construye y suma 100 puntos, con los slots y tipos de
     `config/config.yaml`;
  2. un alumno perfecto saca 100 / 100 y uno que devuelve un número fijo
     pierde EXACTAMENTE los puntos de las preguntas de programación;
  3. las preguntas de la tabla piden el MISMO ejercicio que la actividad a
     mano (misma semilla) y sus soluciones son las del solver;
  4. la respuesta de vectores tiene tantas casillas como valores se califican;
  5. la realimentación de las actividades a mano acierta cuando el alumno
     reporta los valores de referencia;
  6. los ejercicios CAMBIAN de un NC a otro (nadie tiene el mismo).

Uso:  python profe/verificar_tarea.py [n_NC]
"""
import contextlib
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from profe.config import obtener_configuracion                      # noqa: E402
from profe.core import MANO_REPORTE, elegir_mano, obtener_rng       # noqa: E402
from profe.core.evaluator import Tarea                              # noqa: E402
from profe.core.solvers import bairstow, muller                     # noqa: E402
from profe.ui import cuaderno                                       # noqa: E402

NC_BASE = 16330000
N_POR_OMISION = 40

alumno_id = None


class MarcoFalso(object):
    def __init__(self, globs):
        self.f_globals = globs


def muller_experto(f, x0, x1, x2, tol=1e-6, max_iter=100):
    return muller(f, x0, x1, x2, tol=tol, max_iter=max_iter)


def bairstow_experto(a, r0, s0, tol=1e-6, max_iter=100):
    return bairstow(a, r0, s0, tol=tol, max_iter=max_iter)


def muller_fijo(f, x0, x1, x2, tol=1e-6, max_iter=100):
    """Lo que hace un alumno que devuelve siempre lo mismo."""
    return 0.0, 1


def bairstow_fijo(a, r0, s0, tol=1e-6, max_iter=100):
    return [0.0], 1


def silencio():
    return contextlib.redirect_stdout(io.StringIO())


def respuesta_perfecta(ex):
    res = {}
    for i, (p, s) in enumerate(zip(ex.preguntas, ex.soluciones), 1):
        if p['tipo'] == 'funcion':
            continue
        res[i] = [float(v) for v in s] if p['tipo'] == 'vector' else s
    return res


def main(n_nc=N_POR_OMISION):
    cfg, _ = obtener_configuracion()
    slots = cfg.get('slots') or []
    total = sum(float(s.get('peso', 0)) for s in slots)
    peso_funcion = sum(float(s['peso']) for s in slots if s.get('tipo') == 'funcion')
    avisos = []
    titulos = set()
    firmas = {'MULLER': set(), 'BAIRSTOW': set()}

    print('Slots: %d   puntos: %g   min para enviar: %g %%'
          % (len(slots), total,
             100.0 * float(cfg['evaluacion']['min_aprobacion'])))
    print('NC revisados: %d\n' % n_nc)
    print('%-10s %-6s %-7s %-7s %-7s %s'
          % ('NC', 'max', 'puntos', 'fijo', 'vector', 'respuestas'))
    print('-' * 74)

    for k in range(n_nc):
        nc = str(NC_BASE + k * 137)
        correo = 'm%s@hermosillo.tecnm.mx' % nc
        ex = Tarea(correo)

        # 1) forma de la tarea -------------------------------------------------
        if ex.maximo != total:
            avisos.append('NC %s: maximo = %g y los slots suman %g'
                          % (nc, ex.maximo, total))
        if len(ex.preguntas) != len(slots):
            avisos.append('NC %s: %d preguntas para %d slots'
                          % (nc, len(ex.preguntas), len(slots)))
        for j, slot in enumerate(slots):
            esperado = {'teorica': 'opcion', 'ejercicio_num': 'simple',
                        'vector': 'vector', 'funcion': 'funcion'}.get(slot.get('tipo'))
            if ex.preguntas[j]['tipo'] != esperado:
                avisos.append('NC %s: la pregunta %d es %r y el slot %r debería dar %r'
                              % (nc, j + 1, ex.preguntas[j]['tipo'], slot.get('tipo'),
                                 esperado))

        # 2) alumno perfecto y alumno tramposo --------------------------------
        resp = respuesta_perfecta(ex)
        marco_ok = MarcoFalso({'muller': muller_experto, 'bairstow': bairstow_experto})
        filas = ex.calificar(resp, marco_ok)
        puntos = sum(f['puntos'] for f in filas)
        if abs(puntos - total) > 1e-9:
            avisos.append('NC %s: el alumno perfecto saca %g de %g'
                          % (nc, puntos, total))

        marco_fijo = MarcoFalso({'muller': muller_fijo, 'bairstow': bairstow_fijo})
        filas_fijo = ex.calificar(resp, marco_fijo)
        puntos_fijo = sum(f['puntos'] for f in filas_fijo)
        if abs((total - puntos_fijo) - peso_funcion) > 1e-9:
            avisos.append('NC %s: el alumno de número fijo pierde %g puntos '
                          'y la programación vale %g'
                          % (nc, total - puntos_fijo, peso_funcion))

        # 3) las preguntas de la tabla usan el ejercicio a mano ---------------
        fila_vector = None
        for i, (p, s) in enumerate(zip(ex.preguntas, ex.soluciones), 1):
            if p['tipo'] == 'funcion':
                continue
            if p.get('_ej') is None:
                continue
            ej = p['_ej']
            titulos.add(ej['titulo'])
            met_slot = slots[i - 1].get('metodo')
            rng = obtener_rng(ex.nc, ex.id_tarea, 'mano', met_slot)
            ref = elegir_mano(met_slot, rng)
            if met_slot == 'BAIRSTOW' and ref['a'] != ej['a']:
                avisos.append('NC %s: la pregunta %d usa otro ejercicio que la '
                              'actividad a mano' % (nc, i))
            if p['tipo'] == 'simple':
                if abs(float(s) - float(ej['x3'])) > 1e-9:
                    avisos.append('NC %s: la solución de %s no es x3'
                                  % (nc, p['titulo']))
            elif p['tipo'] == 'vector':
                fila_vector = s
                ref_drds = [ej['dr'], ej['ds']]
                if len(s) != len(p['etiquetas']):
                    avisos.append('NC %s: %d valores y %d casillas'
                                  % (nc, len(s), len(p['etiquetas'])))
                if max(abs(u - v) for u, v in zip(s, ref_drds)) > 1e-9:
                    avisos.append('NC %s: la solución del vector no es (Δr, Δs)' % nc)

        # 6) variedad: cada NC tiene que recibir ejercicios distintos ---------
        for met in ('MULLER', 'BAIRSTOW'):
            rng_m = obtener_rng(ex.nc, ex.id_tarea, 'mano', met)
            ej = elegir_mano(met, rng_m)
            if met == 'MULLER':
                firmas[met].add((ej['f_latex'], ej['x0'], ej['x1'], ej['x2']))
            else:
                firmas[met].add(tuple(ej['a']))

        print('%-10s %-6g %-7g %-7g %-7s %s'
              % (nc, ex.maximo, puntos, puntos_fijo,
                 ('%g' % fila_vector[0]) if fila_vector else '-',
                 cuerpo_resumen(ex, resp)))

    # 7) variedad -------------------------------------------------------------
    if len(titulos) < 2:
        avisos.append('pocos enunciados distintos entre %d NC: %s'
                      % (n_nc, sorted(titulos)))
    for met, conjunto in firmas.items():
        if len(conjunto) < n_nc // 3:
            avisos.append('%s: solo %d ejercicios distintos en %d NC'
                          % (met, len(conjunto), n_nc))

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


def cuerpo_resumen(ex, resp):
    piezas = []
    for i, p in enumerate(ex.preguntas, 1):
        if p['tipo'] == 'funcion':
            piezas.append('cod')
        elif p['tipo'] == 'opcion':
            piezas.append('opc')
        elif p['tipo'] == 'vector':
            piezas.append('vec')
        else:
            piezas.append('num')
    return ' '.join(piezas)


def revisar_mano():
    """Ejercita el flujo de las actividades a mano (realimentación)."""
    global alumno_id
    problemas = []
    for metodo in ('MULLER', 'BAIRSTOW'):
        alumno_id = 'm16330887@hermosillo.tecnm.mx'
        cuaderno._EXAMEN = None
        with silencio():
            with silencio():
                cuaderno.mano_enunciado(metodo)
            ej = cuaderno._MANO_EJ[metodo]
            ref = [float(fn(ej)) for _etq, fn in MANO_REPORTE[metodo]]
            cuaderno.mano_comprueba(metodo, ref)
            ok_ref = cuaderno._MANO_RES.get(metodo)
            cuaderno.mano_comprueba(metodo, [v + 1.0 for v in ref])
            ok_mal = cuaderno._MANO_RES.get(metodo)
            # Lista incompleta: ejercita el camino que avisa "faltan valores".
            cuaderno.mano_comprueba(metodo, ref[:-1])
            ok_corto = cuaderno._MANO_RES.get(metodo)
        if not ok_ref:
            problemas.append('%s: la referencia no se acepta' % metodo)
        if ok_mal:
            problemas.append('%s: se acepta una respuesta equivocada' % metodo)
        if ok_corto:
            problemas.append('%s: se acepta una lista incompleta' % metodo)
        print('%-10s a mano: referencia %s  malos %s  incompletos %s'
              % (metodo, 'OK' if ok_ref else 'FALLA', 'OK' if not ok_mal else 'NO',
                 'OK' if not ok_corto else 'NO'))
    return problemas


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else N_POR_OMISION
    salida = main(n)
    print()
    print('Flujo de las actividades a mano (1 NC):')
    problemas_mano = revisar_mano()
    for p in problemas_mano:
        print('AVISO: %s' % p)
    sys.exit(1 if (salida or problemas_mano) else 0)
