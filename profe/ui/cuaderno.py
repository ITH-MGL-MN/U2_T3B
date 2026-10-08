# -*- coding: utf-8 -*-
"""
profe/ui/cuaderno.py — API que usa el cuaderno del alumno (Tarea 3B).

El cuaderno NO habla con los módulos internos: llama a estas funciones, que
son la capa de presentación. El motor de `profe.core` solo devuelve datos.

    generar_tarea(alumno_id)      crea MI_TAREA y muestra el encabezado
    pregunta(n)                   muestra la pregunta n y su widget resp_n
    mano_enunciado(metodo)        enunciado + datos de la actividad a mano
    mano_comprueba(metodo, lista) realimentación de lo que reportó el alumno
    mano_solucion(metodo)         valores de referencia de la actividad
    hoja_manual()                 resumen para calificar las 2 rúbricas
    calificar / enviar / ultimo_envio / consultar_calificacion

REGLA de esta entrega: todo el TEXTO visible para el alumno vive en
`config/*.yaml`, `profe/ejercicios/*.md` o `profe/evaluador/*.md`. Aquí solo
hay etiquetas estructurales y formateo; nada de prosa suelta.
"""
import inspect
import json

import numpy as np

from profe.config import buscar, obtener_configuracion
from profe.core import (
    MANO_REPORTE,
    METODOS_MANO,
    NOMBRE_FUNCION,
    NOMBRE_METODO,
    elegir_mano,
)
from profe.core.evaluator import Tarea
from profe.core.helpers import _fmt
from profe.core.seed import extraer_nc, generar_semilla, obtener_rng

# ---------------------------------------------------------------------
#  Estado del cuaderno
# ---------------------------------------------------------------------
_EXAMEN = None             # la tarea que se está resolviendo
_MANO = {}                 # metodo -> valores que reportó el alumno
_MANO_EJ = {}              # metodo -> ejercicio de la actividad a mano
_MANO_RES = {}             # metodo -> True si acertó TODOS los valores
_ULTIMO_ENVIO = None       # resultado del último enviar() (lo ve ultimo_envio())

TOL_MANO = 1e-3            # relativa, para la realimentación de la tabla a mano

# Parámetros de arranque por método y su nombre en LaTeX (para la línea de
# "Datos y arranque" del enunciado).
_PARAMS_TEXTO = {
    'MULLER': (('x0', '\\omega_0'), ('x1', '\\omega_1'), ('x2', '\\omega_2')),
    'BAIRSTOW': (('r0', 'r_0'), ('s0', 's_0')),
}


def _display(*objetos):
    from IPython.display import display
    return display(*objetos)


def _markdown(texto):
    from IPython.display import Markdown
    return Markdown(texto)


def _obtener_examen(nc=None, marco=None):
    """La tarea del alumno (la crea si no existe, leyendo alumno_id del cuaderno)."""
    global _EXAMEN
    if _EXAMEN is None:
        if marco is None:
            marco = inspect.currentframe().f_back
        glob = getattr(marco, 'f_globals', {}) or {}
        alumno = nc
        for clave in ('alumno_id', 'ALUMNO_ID', 'MI_CORREO', 'correo'):
            if alumno:
                break
            alumno = glob.get(clave)
        if alumno is None:
            raise RuntimeError('Primero ejecuta generar_tarea(alumno_id).')
        _EXAMEN = Tarea(alumno)
    return _EXAMEN


# =====================================================================
#  TAREA Y PREGUNTAS
# =====================================================================
def generar_tarea(alumno_id):
    """Crea la tarea del alumno y avisa de su tamaño (una sola línea)."""
    global _EXAMEN
    _EXAMEN = Tarea(alumno_id)
    _display(_markdown('Esta tarea tiene **%d** preguntas automáticas (%g puntos) y **%d** '
                       'actividades a mano que revisa tu profesor (%g%% de la calificación).'
                       % (len(_EXAMEN.preguntas), _EXAMEN.maximo,
                          len(METODOS_MANO), 100.0 * _EXAMEN.peso_mano)))
    return _EXAMEN


def generar_examen(alumno_id):
    return generar_tarea(alumno_id)


def _render_pregunta(i, p, peso=None, total=None):
    _display(_markdown('#### Pregunta %d: %s' % (i, p['titulo'])))
    if peso is not None and total:
        _display(_markdown('**Valor:** $\\frac{%g}{%g}$ puntos' % (peso, total)))
    if p.get('_mostrar_ejercicio') and p.get('_ej'):
        _display(_markdown('**Ejercicio:** %s' % p['_ej']['titulo']))
    _display(_markdown(p['texto']))
    if p['tipo'] == 'funcion':
        _display(_markdown(
            'Define la función con **exactamente** la firma `%s` en una celda aparte '
            'y ejecútala (no la definas dentro de esta celda).' % p.get('firma', '?')))


class _Vectores(object):
    """Envuelve N casillas como UN solo widget (`.value` devuelve la lista)."""

    def __init__(self, casillas, etiquetas):
        self.casillas = list(casillas)
        self.etiquetas = list(etiquetas)

    @property
    def value(self):
        return [c.value for c in self.casillas]


def _crear_widget_respuesta(i, p, marco):
    import ipywidgets as widgets
    from ipywidgets import Layout

    t = p['tipo']
    if t == 'opcion':
        for op in p['opciones']:
            _display(_markdown(op))
        letras = [chr(97 + j) + ')' for j in range(len(p['opciones']))]
        w = widgets.RadioButtons(
            options=[(letra, j) for j, letra in enumerate(letras)],
            value=None, disabled=False, layout=Layout(width='170px'))
        _display(w)
        marco.f_globals['resp_%d' % i] = w
        return w
    if t == 'simple':
        w = widgets.FloatText(value=0.0, description='Respuesta:',
                              layout=Layout(width='260px'))
        _display(w)
        marco.f_globals['resp_%d' % i] = w
        return w
    if t == 'vector':
        _display(_markdown('Escribe **un número en cada casilla**, en el orden '
                           'del enunciado:'))
        casillas = []
        etiquetas = p.get('etiquetas') or []
        for j, etiqueta in enumerate(etiquetas):
            caja = widgets.FloatText(value=0.0, description='%s =' % etiqueta,
                                     layout=Layout(width='230px'))
            _display(caja)
            casillas.append(caja)
        w = _Vectores(casillas, etiquetas)
        marco.f_globals['resp_%d' % i] = w
        return w
    marco.f_globals['resp_%d' % i] = None
    return None


def pregunta(numero):
    """Muestra la pregunta `numero` y su widget."""
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(marco=marco)
    i = int(numero)
    if not 1 <= i <= len(ex.preguntas):
        raise ValueError('Esta tarea tiene %d preguntas.' % len(ex.preguntas))
    p = ex.preguntas[i - 1]
    _render_pregunta(i, p, peso=ex.pesos[i - 1], total=ex.maximo)
    _crear_widget_respuesta(i, p, marco)
    return None


def _leer_valor(marco, i):
    for clave in ('resp_%d' % i, 'r%d' % i):
        w = marco.f_globals.get(clave)
        if w is None:
            continue
        try:
            return w.value
        except AttributeError:
            return w
    return None


def _respuestas_del_cuaderno(marco):
    ex = _EXAMEN
    res = {}
    for i in range(1, len(ex.preguntas) + 1):
        if ex.preguntas[i - 1]['tipo'] == 'funcion':
            continue
        res[i] = _leer_valor(marco, i)
    return res


# =====================================================================
#  CALIFICACIÓN
# =====================================================================
def _lista_txt(valores):
    return '[%s]' % ', '.join(_fmt(v, 6) for v in valores)


def _num_o_none(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _mostrar_resultados(filas):
    iconos = {'correcta': '\u2705', 'parcial': '\U0001f7e1',
              'incorrecta': '\u274c', 'sin respuesta': '\u26a0\ufe0f'}
    print('%-4s %-12s %-11s %s' % ('#', 'estado', 'puntos', 'respuesta'))
    print('-' * 62)
    for fila in filas:
        val = fila['val']
        if isinstance(val, (tuple, list)) and val and isinstance(val[0], tuple):
            val = 'programa (%d casos)' % len(val)
        elif isinstance(val, list):
            val = _lista_txt(val)
        print('%-4d %-12s %-11s %s' % (fila['i'], iconos[fila['estado']],
                                       '%g/%g' % (fila['puntos'], fila['peso']), val))
    print('-' * 62)


def _nota_ponderada(ex, porcentaje_auto):
    print('NOTA FINAL (ponderada): %.1f / 100  =  %.2f × %.1f %%  +  %.2f × manual'
          % (100.0 * ex.peso_auto * porcentaje_auto / 100.0, ex.peso_auto,
             porcentaje_auto, ex.peso_mano))
    print('   (falta el %.0f %% manual: las 2 rúbricas de la hoja de trabajo)'
          % (100.0 * ex.peso_mano))


def calificar(marco=None):
    ex = _EXAMEN
    if ex is None:
        raise RuntimeError('Primero ejecuta generar_tarea(alumno_id).')
    if marco is None:
        marco = inspect.currentframe().f_back

    respuestas = _respuestas_del_cuaderno(marco)
    filas = ex.calificar(respuestas, marco)

    puntos = 0.0
    maximo = 0.0
    for fila in filas:
        puntos += fila['puntos']
        maximo += fila['peso']
    _mostrar_resultados(filas)
    print('AUTOMÁTICO: %.1f / %g  =  %.1f %%' % (puntos, maximo, 100.0 * puntos / maximo))
    _nota_ponderada(ex, 100.0 * puntos / maximo)
    return puntos, maximo


def ultimo_envio(detalle=False):
    if _ULTIMO_ENVIO is None:
        print('Todavía no has llamado a enviar().')
        return None
    res = _ULTIMO_ENVIO
    print('Último envío: %s  ·  %.1f %% (%g/%g puntos)'
          % ('enviado' if res.get('enviado') else 'NO enviado',
             res.get('calificacion', 0.0), res.get('puntos', 0.0),
             res.get('maximo', 0.0)))
    if res.get('motivo'):
        print('   motivo: %s' % res['motivo'])
    if res.get('error'):
        print('   error : %s' % res['error'])
    return res if detalle else None


def enviar(correo=None, marco=None, debug=False):
    global _ULTIMO_ENVIO
    ex = _EXAMEN
    if ex is None:
        raise RuntimeError('Primero ejecuta generar_tarea(alumno_id).')
    if marco is None:
        marco = inspect.currentframe().f_back

    puntos, maximo = calificar(marco)
    correo = correo or marco.f_globals.get('alumno_id', '') or ex.alumno_id
    res = ex.enviar(_respuestas_del_cuaderno(marco), marco, debug=debug, correo=correo)
    _ULTIMO_ENVIO = res

    if debug:
        print('POST', ex.url)
        print(json.dumps(res['cuerpo'], indent=2, ensure_ascii=False))
        return res

    if res.get('motivo') == 'minimo':
        print('⛔ Aún no puedes enviar: necesitas al menos %g %% (%g puntos de %g). '
              'Corrige y vuelve a intentarlo.'
              % (res['minimo'], ex.min_aprobacion * res['maximo'], res['maximo']))
        print('   (este intento NO se gastó: no se guardó nada en la hoja)')
        return None

    if res['enviado']:
        detalle = ''
        aviso = res.get('aviso')
        if isinstance(aviso, dict) and isinstance(aviso.get('data'), dict):
            d = aviso['data']
            detalle = ' Intento %s, total %.1f %%.' % (d.get('intento', '?'),
                                                       d.get('total', 0.0))
        print('\u2705 Enviado.%s Respuesta del servidor: %s'
              % (detalle, res['respuesta'][:300]))
    else:
        print('\u26a0\ufe0f No se pudo enviar a la hoja de cálculo: %s'
              % res.get('error'))
    return None


def consultar_calificacion():
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(marco=marco)
    res = ex.consultar()

    if not res.get('ok'):
        print('\u26a0\ufe0f No pude consultar la hoja de cálculo: %s'
              % res.get('error'))
        print('   (la consulta no gasta intentos; revisa tu conexión y reintenta)')
        return None

    usados = int(res.get('intento') or 0)
    total = res.get('total')
    restantes = max(0, ex.max_intentos - usados)
    print('NC %s  ·  %s' % (res.get('NC', ex.nc), res.get('tarea', ex.id_tarea)))
    print('   Intentos usados : %d de %d' % (usados, ex.max_intentos))
    print('   Te quedan       : %d' % restantes)
    print('   Último total    : %s'
          % ('%.1f %%' % float(total) if total is not None else '(todavía sin nota)'))
    print('   Estado          : %s' % res.get('estado', '?'))
    if total is not None:
        _nota_ponderada(ex, float(total))
    if total is not None and float(total) >= 100.0 * ex.min_aprobacion:
        print('\u2705 Ya tienes guardado un envío con nota suficiente.')
    elif restantes == 0:
        print('\u26d4 Ya no te quedan intentos; si necesitas otra oportunidad,')
        print('   habla con tu profesor.')
    else:
        print('   Todavía tienes %d intento%s: revisa con calificar() y luego envía.'
              % (restantes, '' if restantes == 1 else 's'))
    return None


# =====================================================================
#  ACTIVIDADES A MANO (con realimentación automática)
# =====================================================================
def _num_txt(valor):
    try:
        return '%g' % float(valor)
    except (TypeError, ValueError):
        return str(valor)


def _datos_texto(metodo, ej):
    """Línea compacta con los datos y el arranque del ejercicio."""
    piezas = []
    for nombre, valor, unidad in (ej.get('datos') or []):
        sufijo = '' if not unidad or unidad == '-' else ' %s' % unidad
        piezas.append('%s = %s%s' % (nombre, _num_txt(valor), sufijo))

    for clave, etiqueta in _PARAMS_TEXTO.get(metodo, ()):
        valor = ej.get(clave)
        if valor is not None:
            piezas.append('$%s = %s$' % (etiqueta, _num_txt(valor)))

    if metodo == 'MULLER':
        piezas.append('$f(\\omega) = %s$' % ej.get('f_latex', ''))

    if ej.get('a'):
        piezas.append('coeficientes `a = %s`' % _lista_txt(ej['a']))

    if not piezas:
        return None
    return '**Datos y arranque:** ' + '  ·  '.join(piezas)


def _reporte_txt(metodo):
    """'[x3]' / '[Δr, Δs]' — lo que el alumno tiene que reportar."""
    return '[%s]' % ', '.join(etq for etq, _fn in MANO_REPORTE[metodo])


def _marco_mano(metodo, ej):
    _display(_markdown('### ✏️ Actividad a mano: %s' % NOMBRE_METODO[metodo]))
    _display(_markdown('**%s**' % ej['titulo']))
    _display(_markdown(ej['contexto'].strip()))
    linea_datos = _datos_texto(metodo, ej)
    if linea_datos:
        _display(_markdown(linea_datos))
    _display(_markdown('Reporta en la celda siguiente la lista `%s`, con al menos '
                       '4 decimales. **Se comprueban todos los valores** para que '
                       'verifiques tu cálculo.' % _reporte_txt(metodo)))
    return ej


def mano_enunciado(metodo, nc=None):
    """Imprime el enunciado de la actividad a mano y guarda el ejercicio."""
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(nc=nc, marco=marco)
    rng = obtener_rng(nc or ex.nc, ex.id_tarea, 'mano', metodo)
    ej = elegir_mano(metodo, rng)
    _MANO_EJ[metodo] = ej
    _marco_mano(metodo, ej)
    return ej


def _referencia_mano(metodo):
    ej = _MANO_EJ[metodo]
    return [(etq, float(fn(ej))) for etq, fn in MANO_REPORTE[metodo]]


def mano_comprueba(metodo, valores):
    """Realimentación de la actividad a mano: compara todos los valores."""
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        print('Primero ejecuta mano_enunciado(%r).' % metodo)
        return None

    try:
        vals = [float(v) for v in valores]
    except (TypeError, ValueError):
        print('\u26a0\ufe0f Reporta una lista de números, por ejemplo %s.'
              % _reporte_txt(metodo))
        return None

    _MANO[metodo] = vals
    ref = _referencia_mano(metodo)
    print('Tus valores reportados: %s'
          % ', '.join('%s = %.8g' % (etq, v) for (etq, _r), v in zip(ref, vals)))

    todo, faltan = True, len(ref) - len(vals)
    print('')
    print('   %-10s %-16s %-16s %s' % ('valor', 'tu resultado', 'referencia', 'estado'))
    print('   ' + '-' * 58)
    for (etq, r), v in zip(ref, vals):
        err = abs(v - r) / max(abs(r), 1e-12)
        bien = err <= TOL_MANO
        todo = todo and bien
        print('   %-10s %-16.8g %-16.8g %s (error %.1e)'
              % (etq, v, r, '\u2705' if bien else '\u274c', err))

    _MANO_RES[metodo] = bool(todo and len(vals) == len(ref))
    print('')
    if _MANO_RES[metodo]:
        print('\u2705 Todos los valores son correctos.')
    else:
        if len(vals) < len(ref):
            print('\u26a0\ufe0f Reportaste %d valores y hacen falta %d: %s.'
                  % (len(vals), len(ref), _reporte_txt(metodo)))
        print('   Sugerencias: arrastra TODOS los decimales de los pasos y no')
        print('   redondees a la mitad del cálculo.')
    return None


def mano_solucion(metodo):
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        print('Primero ejecuta mano_enunciado(%r).' % metodo)
        return None
    print('Valores de referencia:')
    for etq, r in _referencia_mano(metodo):
        print('   %-10s = %.8f' % (etq, r))
    return None


def mano_referencia(metodo):
    return mano_solucion(metodo)


def hoja_manual(metodo=None):
    ex = _EXAMEN
    nombre = ex.id_tarea if ex is not None else 'U2_T3B'
    metodos = (metodo,) if metodo else METODOS_MANO

    print('=' * 72)
    print('HOJA DE TRABAJO MANUAL · %s' % nombre)
    print('=' * 72)
    for met in metodos:
        ej = (_MANO_EJ or {}).get(met)
        if ej is None:
            continue
        alumno = _MANO.get(met, [])
        print('\n%s · %s' % (NOMBRE_METODO[met], ej['titulo']))
        if met == 'MULLER':
            print('  función    : $f(\\omega) = %s$' % ej.get('f_latex', ''))
            print('  %-11s: %s, %s, %s' % ('puntos', _num_txt(ej['x0']),
                                          _num_txt(ej['x1']), _num_txt(ej['x2'])))
        else:
            print('  polinomio  : %s' % _lista_txt(ej['a']))
            print('  %-11s: r0 = %s, s0 = %s' % ('arranque', _num_txt(ej['r0']),
                                                _num_txt(ej['s0'])))
        print('  %-11s: %s' % ('referencia',
                                ', '.join('%s = %.6g' % (etq, r)
                                          for etq, r in _referencia_mano(met))))
        print('  %-11s: %s' % ('alumno',
                                (', '.join('%.6g' % v for v in alumno)
                                 if alumno else '(sin reportar)')))
        print('  %-11s: %s' % ('resultado', 'acertada' if _MANO_RES.get(met)
                                else ('revisar' if met in _MANO_RES
                                      else '(sin comprobar)')))
    if ex is not None:
        print('\nCalifica cada rúbrica de 0 a 10 en la hoja %s_Manual.' % nombre)
        print('Nota final = %.2f*automático + %.2f*manual'
              % (ex.peso_auto, ex.peso_mano))


# =====================================================================
#  Utilidades sueltas
# =====================================================================
def raices_de(a):
    """Todas las raíces del polinomio (reales y complejas) con `numpy.roots`."""
    return np.roots([float(c) for c in a])


def muller_referencia(f, x0, x1, x2, tol=1e-6, max_iter=100):
    """El Müller DEL MOTOR: lo usan los laboratorios, para no depender de lo
    que el alumno haya escrito (o no) en su celda de práctica."""
    from profe.core.solvers import muller
    return muller(f, x0, x1, x2, tol=tol, max_iter=max_iter)


def bairstow_referencia(a, r0, s0, tol=1e-6, max_iter=100):
    """El Bairstow DEL MOTOR: igual que arriba, para los laboratorios."""
    from profe.core.solvers import bairstow
    return bairstow(a, r0, s0, tol=tol, max_iter=max_iter)


def semilla_de(alumno_id):
    cfg, _ = obtener_configuracion()
    id_tarea = buscar(cfg, 'tarea.id', 'U2_T3B')
    return generar_semilla(extraer_nc(alumno_id), id_tarea)


# =====================================================================
#  API DEL CUADERNO
# ---------------------------------------------------------------------
#  ÚNICOS nombres que el cuaderno recibe del motor: la celda 1 lo carga en un
#  namespace aparte y copia al cuaderno lo que hay aquí. Si el cuaderno usa
#  algo que no esté en esta lista, falla con `KeyError` al arrancar.
# =====================================================================
__all__ = [
    'bairstow_referencia', 'calificar', 'consultar_calificacion', 'enviar',
    'extraer_nc', 'generar_examen', 'generar_tarea', 'hoja_manual',
    'mano_comprueba', 'mano_enunciado', 'mano_referencia', 'mano_solucion',
    'muller_referencia', 'pregunta', 'raices_de', 'semilla_de', 'ultimo_envio',
]
