# -*- coding: utf-8 -*-
"""
profe/ui/cuaderno.py — API que usa el cuaderno del alumno (Tarea 3B).

El cuaderno NO habla con los módulos internos: llama a estas funciones, que
son la capa de presentación. El motor de `profe.core` solo devuelve datos.

QUÉ SE PUEDE LLAMAR Y QUÉ DEVUELVE
----------------------------------
`__all__` (al final del archivo) es el contrato: son los ÚNICOS nombres que la
celda 1 copia al cuaderno. Todo lo que empieza con `_` es interno del motor
(el que dibuja, como `_marco_mano`, o el estado, como `_MANO`) y se puede
cambiar sin romper el cuaderno.

Ojo con los `return`: cuando una función devuelve `None` es porque actúa por
efecto (dibuja o guarda estado por dentro); cuando devuelve un dato, es para
que el cuaderno lo use.

    función                    devuelve           ¿te sirve?
    generar_tarea(id, nombre)  la Tarea           sí: queda en MI_TAREA
    pregunta(n)                None               no: el widget queda en resp_n
    ver_preguntas(banco)       None               no: imprime los enunciados
                                                  (material del profesor)
    mano_enunciado(metodo)     el ejercicio       sí: EJ_MU['f'], EJ_BA['a']
    mano_comprueba(metodo, v)  None               no: el veredicto queda dentro
    mano_ecuacion(metodo)      None               no: revisa tu f contra el
                                                  enunciado
    mano_solucion(metodo)      None               sí: tu tabla CON la referencia
    practica(metodo)           None               no: prueba TU función y la
                                                  compara con la referencia
                                                  (material del profesor)
    hoja_manual()              None               no: dibuja la hoja
    calificar()                (puntos, maximo)   sí: puntos, maximo = calificar()
    enviar(correo)             None               no: queda en _ULTIMO_ENVIO
    ultimo_envio(detalle)      el dict o None     sí, si pides detalle=True
    consultar_calificacion()   None               no: solo imprime
    muller_referencia(...)     (raiz, n_iter)     sí: los laboratorios
    bairstow_referencia(...)   (raices, n_iter)   sí: los laboratorios
    raices_de(a)               las raíces         sí: los laboratorios
    extraer_nc(correo)         el no. de control  sí: está en profe/core/seed.py
    semilla_de(alumno_id)      la semilla         sí: hace reproducible la tarea

CÓMO ESTÁ ORGANIZADO POR DENTRO
-------------------------------
Todo lo que empieza con `_` es interno, y se puede cambiar sin tocar el
cuaderno. Por grupos:

    estado    _EXAMEN (tu tarea), _MANO (lo que reportaste), _MANO_EJ (tu
              ejercicio), _MANO_RES (el veredicto), _ULTIMO_ENVIO
    entrada   _obtener_examen, _leer_valor, _respuestas_del_cuaderno
    dibujo    _display, _markdown, _render_pregunta, _crear_widget_respuesta,
              _marco_mano, _mostrar_resultados, _nota_ponderada, practica,
              mano_ecuacion
    formato   _num_txt, _largo_txt, _exp_tex, _lista_txt, _etq_tex, _error_rel,
              _complejo_tex, _cerca, _identidad_tex, _tabla_md, _tabla_mano,
              _datos_texto, _referencia_mano

El error relativo de la tabla a mano (`_error_rel`) divide entre el MAYOR de
los dos números, no entre la referencia: así un valor reportado de 0 da error
1.0 (el tope) en lugar del absurdo 3.9e11, y el resultado sigue siendo
comparable con `TOL_MANO`.

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
TOL_ECUACION = 1e-9        # relativa, para revisar la f que escribe el alumno

# Parámetros de arranque por método y su nombre en LaTeX (para la línea de
# "Datos y arranque" del enunciado).
_PARAMS_TEXTO = {
    'MULLER': (('x0', '\\omega_0'), ('x1', '\\omega_1'), ('x2', '\\omega_2')),
    'BAIRSTOW': (('r0', 'r_0'), ('s0', 's_0')),
}


def _display(*objetos):
    """Muestra objetos en el cuaderno, como el `display` de IPython.

    El import va aquí dentro a propósito: así el módulo se puede cargar fuera
    de un cuaderno (las pruebas de `profe/`) sin necesitar IPython.
    """
    from IPython.display import display
    return display(*objetos)


def _markdown(texto):
    """Envuelve el texto en `Markdown` para que `_display` lo renderice."""
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
def generar_tarea(alumno_id, nombre=None):
    """Crea la tarea del alumno y avisa de su tamaño (una sola línea).

    `alumno_id` es el correo institucional (de ahí sale el número de control).
    `nombre` es opcional y solo se usa en la hoja de trabajo: la calificación
    se identifica siempre por el NC.

    Devuelve la `Tarea`. El cuaderno la guarda en `MI_TAREA`, aunque casi no
    necesita tocarla: las demás funciones la recuerdan por dentro.
    """
    global _EXAMEN
    _EXAMEN = Tarea(alumno_id, nombre=nombre)
    _display(_markdown('Esta tarea tiene **%d** preguntas automáticas (%g puntos): '
                       'esas son las que cuentan. Las **%d** actividades a mano se '
                       'hacen igual, pero se entregan como evidencia (captura de la '
                       'hoja + enlace de tu cuaderno en Colab).'
                       % (len(_EXAMEN.preguntas), _EXAMEN.maximo,
                          len(METODOS_MANO))))
    return _EXAMEN


def generar_examen(alumno_id):
    """Nombre viejo de `generar_tarea`. Hace y devuelve lo mismo."""
    return generar_tarea(alumno_id)


def _render_pregunta(i, p, peso=None, total=None):
    """Dibuja el encabezado y el enunciado de la pregunta `i` (sin el widget)."""
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
        if p.get('ejemplo'):
            _display(_markdown('Con los datos de tu enunciado se llama así: `%s`.'
                               % p['ejemplo']))


class _Vectores(object):
    """Envuelve N casillas como UN solo widget (`.value` devuelve la lista)."""

    def __init__(self, casillas, etiquetas):
        self.casillas = list(casillas)
        self.etiquetas = list(etiquetas)

    @property
    def value(self):
        return [c.value for c in self.casillas]


def _crear_widget_respuesta(i, p, marco):
    """Crea el widget de la pregunta `i` y lo deja en el cuaderno como `resp_i`.

    El tipo lo decide el enunciado: 'opcion' -> botones de opción, 'simple' ->
    una casilla, 'vector' -> varias casillas envueltas en `_Vectores`.
    """
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
    """Muestra la pregunta `numero` y su widget.

    El widget queda guardado en el cuaderno como `resp_<numero>`, que es de
    donde `calificar()` lo lee después.

    Devuelve None: actúa dibujando.
    """
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(marco=marco)
    i = int(numero)
    if not 1 <= i <= len(ex.preguntas):
        raise ValueError('Esta tarea tiene %d preguntas.' % len(ex.preguntas))
    p = ex.preguntas[i - 1]
    _render_pregunta(i, p, peso=ex.pesos[i - 1], total=ex.maximo)
    _crear_widget_respuesta(i, p, marco)
    return None


def ver_preguntas(banco=None):
    """Imprime los enunciados como los ve el alumno, pero sin crear widgets.

    Es material del profesor y sirve para revisar el **LaTeX**: una barra de
    más (`\\`), un `$` sin cerrar o un acento roto se ven aquí antes que en
    clase.

    Sin argumentos saca las preguntas de esta tarea (sin marcar nada: esa celda
    puede quedarse en el cuaderno del alumno, así que no destripa respuestas);
    con el nombre de un banco teórico (`'MULLER_INTRO'`, `'BAIRSTOW_INTRO'`,
    `'POLI_CONCL'`) saca TODAS las de ese banco, que son las que se reparten
    entre los alumnos, con la opción correcta marcada. Ese modo SÍ enseña la
    respuesta: es para que el profesor compruebe de una pasada que `correcta`
    apunta a la opción buena.

    Devuelve None: actúa dibujando.
    """
    if banco:
        _cfg, bancos = obtener_configuracion()
        if banco not in bancos:
            _display(_markdown('No conozco el banco `%s`; hay: %s.'
                               % (banco, ', '.join('`%s`' % b
                                                   for b in sorted(bancos)))))
            return None
        for k, p in enumerate(bancos[banco], start=1):
            correcta = int(p.get('correcta', 0))
            _display(_markdown('#### %s · %d/%d · %s'
                               % (banco, k, len(bancos[banco]), p['titulo'])))
            _display(_markdown(p['pregunta']))
            for j, op in enumerate(p.get('opciones') or []):
                _display(_markdown('%s%s' % (op, '  ✅' if j == correcta else '')))
        return None

    ex = _EXAMEN
    if ex is None:
        _display(_markdown('Primero ejecuta `generar_tarea(alumno_id)`.'))
        return None
    for i, p in enumerate(ex.preguntas, start=1):
        _render_pregunta(i, p, peso=ex.pesos[i - 1], total=ex.maximo)
        for op in p.get('opciones') or []:
            _display(_markdown(op))
    return None


def _leer_valor(marco, i):
    """Lo que el alumno puso en la pregunta `i`, o None si no hay widget."""
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
    """Todas las respuestas del cuaderno, en un diccionario pregunta -> valor.

    Salta las preguntas de programación: esas no tienen widget, se califican
    probando la función que definió el alumno.
    """
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
    """Una lista de números como texto: `[1, 2, 3]`."""
    return '[%s]' % ', '.join(_fmt(v, 6) for v in valores)


def _num_o_none(valor):
    """El valor como número, o None si no se puede convertir.

    Hoy nadie la llama: quedó de cuando las respuestas numéricas se leían a
    mano en vez de por widget.
    """
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _mostrar_resultados(filas):
    """Muestra la tabla de `calificar()`: estado, puntos y respuesta por pregunta."""
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
    """Imprime la nota final: solo la automática si no hay parte manual."""
    if ex.peso_mano <= 0:
        print('NOTA FINAL: %.1f / 100  (todo automático)' % porcentaje_auto)
        return
    print('NOTA FINAL (ponderada): %.1f / 100  =  %.2f × %.1f %%  +  %.2f × manual'
          % (100.0 * ex.peso_auto * porcentaje_auto / 100.0, ex.peso_auto,
             porcentaje_auto, ex.peso_mano))
    print('   (falta el %.0f %% manual: las 2 rúbricas de la hoja de trabajo)'
          % (100.0 * ex.peso_mano))


def calificar(marco=None):
    """Corrige lo escrito y muestra la tabla de resultados.

    Imprime la nota que llevas y **no envía nada**: se puede llamar las veces
    que quieras sin gastar intentos.

    Devuelve `(puntos, maximo)` en crudo, que es lo que el cuaderno guarda en
    `puntos, maximo = calificar()`.
    """
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
    """Muestra qué pasó con el último `enviar()` de esta sesión.

    Devuelve el diccionario del envío solo si pides `detalle=True`; si no,
    devuelve None (lo normal es leer lo que imprime).
    """
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
    """Califica y manda el resultado al Apps Script del profesor.

    Gasta uno de los intentos, salvo que no llegues al mínimo: en ese caso no
    se guarda nada y el intento no cuenta. Con `debug=True` imprime el JSON
    que se mandaría y NO envía.

    Devuelve None: para saber cómo salió, mira `ultimo_envio()`.
    """
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
    """Muestra lo que la hoja de cálculo ya tiene guardado de este alumno.

    No gasta intentos. Devuelve None: solo imprime.
    """
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
    """Un número corto como texto, para meterlo dentro de una frase."""
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


def _marco_mano(metodo, ej):
    """Dibuja el enunciado completo de la actividad a mano.

    Título, contexto del ejercicio, línea de datos y arranque, y la línea que
    dice qué lista hay que reportar. Es lo que sale al ejecutar
    `mano_enunciado(...)`.
    """
    _display(_markdown('### ✏️ Actividad a mano: %s' % NOMBRE_METODO[metodo]))
    _display(_markdown('**%s**' % ej['titulo']))
    _display(_markdown(ej['contexto'].strip()))
    linea_datos = _datos_texto(metodo, ej)
    if linea_datos:
        _display(_markdown(linea_datos))
    _display(_markdown('Reporta en la celda siguiente la lista $%s$, con al menos '
                       '4 decimales. **Se comprueban todos los valores** para que '
                       'verifiques tu cálculo.' % _reporte_tex(metodo)))
    return ej


def mano_enunciado(metodo, nc=None):
    """Imprime el enunciado de la actividad a mano y guarda el ejercicio.

    `metodo` es 'MULLER' o 'BAIRSTOW'. El ejercicio sale de la semilla del
    alumno, así que para él es siempre el mismo.

    Devuelve el diccionario del ejercicio (`EJ_MU` / `EJ_BA`), y sí se usa:
    las celdas de práctica leen `EJ_MU['f']` y `EJ_BA['a']`.
    """
    marco = inspect.currentframe().f_back
    ex = _obtener_examen(nc=nc, marco=marco)
    rng = obtener_rng(nc or ex.nc, ex.id_tarea, 'mano', metodo)
    ej = elegir_mano(metodo, rng)
    _MANO_EJ[metodo] = ej
    _marco_mano(metodo, ej)
    return ej


def _referencia_mano(metodo):
    """Los valores de referencia del ejercicio, como pares (etiqueta, valor).

    Es lo que se compara con lo que reportó el alumno.
    """
    ej = _MANO_EJ[metodo]
    return [(etq, float(fn(ej))) for etq, fn in MANO_REPORTE[metodo]]


# --- presentación de las actividades a mano --------------------------
#  Todo lo que muestre valores o tablas va con `display` y en LaTeX, nunca
#  con `print`: así el alumno ve las cuentas como en el enunciado.

_TEXTO_ETQ = {'x3': '\\omega_3', 'Δr': r'\Delta r', 'Δs': r'\Delta s'}


def _etq_tex(etq: str) -> str:
    """La etiqueta del valor, lista para meter entre `$`: `x3` -> omega_3."""
    return _TEXTO_ETQ.get(etq, etq)


def _reporte_tex(metodo):
    """La lista que hay que reportar, en LaTeX: `[omega_3]` o `[Delta r, ...]`."""
    return '[%s]' % ', '.join(_etq_tex(etq)
                              for etq, _fn in MANO_REPORTE[metodo])


def _largo_txt(valor):
    """Un número con 8 cifras significativas (sin notación científica)."""
    try:
        return '%.8g' % float(valor)
    except (TypeError, ValueError):
        return str(valor)


def _exp_tex(valor):
    """LaTeX para un número pequeño: `1.2e-05` -> 1.2 \times 10^{-5}."""
    mantisa, _, exponente = ('%.1e' % float(valor)).partition('e')
    return r'%s\times 10^{%d}' % (mantisa, int(exponente))


def _complejo_tex(z, dec=6):
    """Un número real o complejo en LaTeX, sin los `$`.

    Hace falta porque las raíces de Müller y Bairstow son complejas, y un
    `%g` a secas no sabe escribirlas.
    """
    z = complex(z)
    parte = '%.*g' % (dec, z.real)
    if abs(z.imag) <= 1e-12 * max(1.0, abs(z.real)):
        return parte
    return '%s %+.*g\\,i' % (parte, dec, z.imag)


def _cerca(a, b, tol):
    """¿Son `a` y `b` el mismo número, con tolerancia relativa `tol`?

    Se usa para comparar las raíces que devuelve la función del alumno con las
    de referencia: un método iterativo puede parar en 1.0000000001 - 1.9999999999i
    y eso es la misma raíz.
    """
    a, b = complex(a), complex(b)
    return abs(a - b) <= float(tol) * max(1.0, abs(a), abs(b))


def _error_rel(valor, ref):
    """Qué tan lejos quedó un valor reportado de su referencia.

    Es el error relativo de siempre, `|valor - ref| / |ref|`, con dos
    cuidados:

    * Si el alumno reporta 0 (o algo diminuto), dividir entre |ref| no dice
      nada útil: con `ref = 3.9422728` saldría un error de 3.9e11, un número
      que no le comunica nada y que además no se compara con una tolerancia
      como `TOL_MANO`. Por eso el divisor es el mayor de los dos (o 1 si los
      dos son diminutos): así reportar 0 da error 1.0 —el tope razonable, no
      0 %, no 3.9e11— y el resultado siempre es comparable con la tolerancia.
    * Si el valor está bien, sigue dando un número pequeñito, que es lo que se
      quiere ver (`1.2e-05`).

    Devuelve un flotante no negativo.
    """
    valor, ref = float(valor), float(ref)
    escala = max(abs(valor), abs(ref), 1e-12)
    return abs(valor - ref) / escala


def _tabla_md(encabezados, filas):
    """Una tabla de Markdown (las matemáticas van entre `$`)."""
    lineas = ['| ' + ' | '.join(encabezados) + ' |',
              '|' + '|'.join([':---'] * len(encabezados)) + '|']
    lineas += ['| ' + ' | '.join(fila) + ' |' for fila in filas]
    return '\n'.join(lineas)


def _tabla_mano(metodo, alumno, ref, con_referencia=False):
    """
    Tabla: valor, lo que reportaste, el error relativo y el estado.

    La columna de la **referencia** solo sale con `con_referencia=True`, que es
    lo que pide `mano_solucion()` (material del profesor). En el cuaderno del
    alumno nunca se imprime: la actividad a mano es suya, y enseñarle la
    respuesta antes de que la mande sería regalarle el ejercicio. El error
    relativo le sirve de realimentación sin decirle el número.
    """
    encabezados = ['**valor**', '**tu resultado**']
    if con_referencia:
        encabezados.append('**referencia**')
    encabezados += ['**error relativo**', '**estado**']

    filas = []
    for i, (etq, r) in enumerate(ref):
        valor = alumno[i] if i < len(alumno) else None
        celdas = ['$%s$' % _etq_tex(etq)]
        if valor is None:
            celdas.append('_(sin reportar)_')
            if con_referencia:
                celdas.append('$%s$' % _largo_txt(r))
            celdas += ['—', '⚠️']
        else:
            err = _error_rel(valor, r)
            celdas.append('$%s$' % _largo_txt(valor))
            if con_referencia:
                celdas.append('$%s$' % _largo_txt(r))
            celdas += ['$%s$' % _exp_tex(err),
                       '✅' if err <= TOL_MANO else '❌']
        filas.append(celdas)
    return _tabla_md(encabezados, filas)


def mano_comprueba(metodo, valores):
    """Comprueba lo que reportaste y te dice si está bien (sin decirte cuánto vale).

    Muestra la tabla con el error relativo de cada valor y guarda el veredicto
    por dentro (`_MANO_RES`), que es lo que después lee `hoja_manual()`. La
    referencia NO se enseña aquí: para verla está `mano_solucion()`, pero eso
    es material del profesor y deja la actividad a mano sin sentido.

    Devuelve None.
    """
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        _display(_markdown('Primero ejecuta `mano_enunciado(%r)`.' % metodo))
        return None

    try:
        vals = [float(v) for v in valores]
    except (TypeError, ValueError):
        _display(_markdown('\u26a0\ufe0f Reporta una lista de números, por '
                           'ejemplo $%s$.' % _reporte_tex(metodo)))
        return None

    _MANO[metodo] = vals
    ref = _referencia_mano(metodo)

    _display(_markdown('**Tus valores reportados** · %s' % ej['titulo']))
    _display(_markdown(_tabla_mano(metodo, vals, ref)))

    todo = True
    for (etq, r), v in zip(ref, vals):
        todo = todo and _error_rel(v, r) <= TOL_MANO
    _MANO_RES[metodo] = bool(todo and len(vals) == len(ref))

    if _MANO_RES[metodo]:
        _display(_markdown('✅ **Todos los valores son correctos.**'))
    else:
        if len(vals) < len(ref):
            _display(_markdown('\u26a0\ufe0f Reportaste **%d** valores y hacen '
                               'falta **%d**: $%s$.'
                               % (len(vals), len(ref), _reporte_tex(metodo))))
        _display(_markdown('_Sugerencias: arrastra TODOS los decimales de los '
                           'pasos y no redondees a la mitad del cálculo (un '
                           'error de $1$ significa que el valor reportado no '
                           'se parece en nada al esperado)._'))
    return None


def _fn_del_cuaderno(marco, nombre):
    """La función `nombre` que definió el alumno en el cuaderno, o None."""
    return (getattr(marco, 'f_globals', {}) or {}).get(nombre)


def mano_ecuacion(metodo):
    """Revisa la función que escribiste contra la del enunciado.

    La compara contigo en **valores que no son tus puntos de arranque**, así que
    no sirve una $f$ que acierte solo en los tres que ves: o la transcribiste
    bien —paréntesis, signos y **tu** constante incluidos— o no.

    Es el paso previo a usar tu $f$ como entrada de tu método. A propósito no
    imprime los valores de $f$: esos son parte de la actividad a mano.

    Devuelve None: actúa dibujando.
    """
    marco = inspect.currentframe().f_back
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        _display(_markdown('Primero ejecuta `mano_enunciado(%r)`.' % metodo))
        return None

    referencia = ej.get('f')
    if not callable(referencia):
        _display(_markdown('La actividad de **%s** no pide escribir una función: '
                           'su entrada es la lista de coeficientes.'
                           % NOMBRE_METODO[metodo]))
        return None

    fn = _fn_del_cuaderno(marco, 'f')
    if not callable(fn):
        _display(_markdown('⚠️ Todavía no escribes tu $f$: deja `f = lambda x: ...` '
                           'en esta celda y vuelve a ejecutarla.'))
        return None

    puntos = (ej['x0'], ej['x2'], 0.5 * (ej['x0'] + ej['x1']), 0.0, -1.5)
    peor, fallo = 0.0, None
    for x in puntos:
        try:
            tuyo, del_enunciado = float(fn(x)), float(referencia(x))
        except Exception as exc:                  # noqa: BLE001
            fallo = (x, exc)
            break
        if np.isfinite(tuyo) and np.isfinite(del_enunciado):
            peor = max(peor, abs(tuyo - del_enunciado)
                       / max(1.0, abs(del_enunciado)))

    _display(_markdown('**Revisión de tu $f$** · %s' % ej['titulo']))
    if fallo is not None:
        _display(_markdown('❌ Tu $f$ falló en $x = %g$: `%r`'
                           % (fallo[0], fallo[1])))
    elif peor == 0:
        _display(_markdown('✅ **Tu $f$ es la del enunciado** (coincide '
                           'exactamente, en %d valores).' % len(puntos)))
    elif peor <= TOL_ECUACION:
        _display(_markdown('✅ **Tu $f$ es la del enunciado** (la diferencia '
                           'relativa máxima es $%s$, en %d valores).'
                           % (_exp_tex(peor), len(puntos))))
    else:
        _display(_markdown('❌ **Tu $f$ no coincide** con la del enunciado (la '
                           'diferencia relativa máxima es $%s$). Revisa el signo '
                           'de la constante, los coeficientes y los paréntesis.'
                           % _exp_tex(peor)))
    return None


def mano_solucion(metodo):
    """Muestra los valores de referencia, con la tabla completa.

    Imprime la misma tabla que `mano_comprueba` pero CON la columna de la
    referencia. Es material del profesor (o para el alumno que ya entregó).
    Devuelve None.
    """
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        print('Primero ejecuta mano_enunciado(%r).' % metodo)
        return None
    print('Valores de referencia:')
    for etq, r in _referencia_mano(metodo):
        print('   %-10s = %.8f' % (etq, r))
    _display(_markdown('**Valores de referencia** · %s (profesor)'
                       % ej['titulo']))
    _display(_markdown(_tabla_mano(metodo, _MANO.get(metodo, []),
                                   _referencia_mano(metodo),
                                   con_referencia=True)))
    return None


def mano_referencia(metodo):
    """Nombre viejo de `mano_solucion`. Hace y devuelve lo mismo (None)."""
    return mano_solucion(metodo)


# --- prácticas: probar la función que escribió el alumno -----------------
#  Las celdas de práctica del cuaderno solo DEFINEN la función. Llamarla,
#  compararla con la referencia y presentar el resultado en LaTeX es idéntico
#  en las dos prácticas (Müller y Bairstow), así que vive aquí y el cuaderno
#  no repite el mismo bloque de presentación dos veces.
def _raiz_y_nit(res):
    """La raíz que devolvió el alumno y, si la dio, el número de iteraciones.

    Acepta `(raiz, n_iter)`, que es lo que pide la firma, y también la raíz a
    secas: devolver solo el resultado es un error razonable y no vale la pena
    castigarlo en una celda de práctica.
    """
    if isinstance(res, (list, tuple)) and len(res) == 2:
        return res[0], res[1]
    return res, None


def _raices_y_nit(res):
    """Las raíces que devolvió el alumno y, si las dio, las iteraciones.

    Igual que `_raiz_y_nit`, pero para una LISTA: aquí hay que distinguir
    `([raices], n_iter)` de una lista de dos raíces, así que solo se toma como
    pareja cuando el primer elemento es una lista (o un arreglo).
    """
    if (isinstance(res, tuple) and len(res) == 2
            and isinstance(res[0], (list, tuple, np.ndarray))):
        return list(res[0]), res[1]
    if isinstance(res, (list, tuple, np.ndarray)):
        return list(res), None
    return [res], None


def practica(metodo):
    """Prueba TU función con el ejercicio de tu enunciado.

    Se llama después de definir la función (`muller` o `bairstow`). Compara lo
    que devuelve con la referencia del motor y lo enseña en LaTeX, con el
    veredicto. Acepta los dos métodos.

    Ojo: esto NO es la calificación. Los casos que cuentan son los ocultos de
    la tarea, así que aquí no hay puntos ni intentos.

    Devuelve None: actúa dibujando.
    """
    marco = inspect.currentframe().f_back
    ej = (_MANO_EJ or {}).get(metodo)
    if ej is None:
        _display(_markdown('Primero ejecuta `mano_enunciado(%r)`.' % metodo))
        return None

    nombre = NOMBRE_FUNCION[metodo]
    fn = _fn_del_cuaderno(marco, nombre)
    if not callable(fn):
        _display(_markdown('⚠️ No encuentro tu función `%s(...)`: define la '
                           'tuya en esta celda y vuelve a ejecutarla.' % nombre))
        return None

    try:
        if metodo == 'MULLER':
            res = fn(ej['f'], ej['x0'], ej['x1'], ej['x2'])
        else:
            res = fn(ej['a'], ej['r0'], ej['s0'])
    except NotImplementedError as exc:
        _display(_markdown('⚠️ Todavía no terminas la función: %s' % exc))
        return None
    except Exception as exc:                       # noqa: BLE001
        _display(_markdown('❌ Tu función falló: `%r`' % (exc,)))
        return None

    tol = getattr(_EXAMEN, 'tol_funcion', 1e-4) or 1e-4
    _display(_markdown('**Prueba con tu ejercicio** · %s' % ej['titulo']))

    if metodo == 'MULLER':
        raiz, nit = _raiz_y_nit(res)
        ref, nit_ref = muller_referencia(ej['f'], ej['x0'], ej['x1'],
                                         ej['x2'], tol=1e-9)
        ok = _cerca(raiz, ref, tol)
        filas = [['$x$', '$%s$' % _complejo_tex(raiz),
                  '$%s$' % _complejo_tex(ref), '✅' if ok else '❌']]
    else:
        raices, nit = _raices_y_nit(res)
        _, nit_ref = bairstow_referencia(ej['a'], ej['r0'], ej['s0'], tol=1e-9)
        clave = lambda z: (complex(z).real, complex(z).imag)
        tuyas = sorted([complex(v) for v in raices], key=clave)
        ref = sorted([complex(v) for v in raices_de(ej['a'])], key=clave)
        filas, ok = [], True
        for j in range(max(len(tuyas), len(ref))):
            tu = tuyas[j] if j < len(tuyas) else None
            es = ref[j] if j < len(ref) else None
            bien = (tu is not None and es is not None and _cerca(tu, es, tol))
            ok = ok and bien
            filas.append([
                '$x_{%d}$' % (j + 1),
                '$%s$' % _complejo_tex(tu) if tu is not None else '_(falta)_',
                '$%s$' % _complejo_tex(es) if es is not None else '_(de más)_',
                '✅' if bien else '❌'])

    if nit is not None:
        filas.append(['$n$ iteraciones', '$%d$' % nit,
                      '$%d$' % nit_ref if nit_ref is not None else '—', '—'])
    _display(_markdown(_tabla_md(
        ['**valor**', '**tu resultado**', '**referencia**', '**estado**'],
        filas)))
    if nit is not None:
        _display(_markdown('_El número de iteraciones depende de dónde decidas '
                           'parar; lo que se compara es la raíz._'))
    if ok:
        _display(_markdown('✅ **Tu función resuelve el ejercicio del enunciado.**'))
    else:
        _display(_markdown('❌ **No coincide.** Revisa el orden de los pasos y, '
                           'sobre todo, que no redondees a la mitad del '
                           'cálculo._'))
    return None


def _identidad_tex(ex):
    """Nombre y número de control: es lo que identifica la hoja entregada."""
    if ex is None:
        return '_(sin identificar: ejecuta la celda de identificación)_'
    piezas = []
    if ex.nombre:
        piezas.append('**Alumno:** %s' % ex.nombre)
    piezas.append('**NC:** %s' % ex.nc)
    if not ex.nombre:
        piezas.append('_(el nombre solo lo da Google cuando corres en Colab)_')
    return '  ·  '.join(piezas)


def hoja_manual(metodo=None, mostrar_referencia=False):
    """Hoja de evidencia de las 2 actividades a mano (captura + enlace).

    Con `metodo` muestra solo esa actividad; sin argumentos, todas.

    La columna con la **referencia NO se imprime** salvo que se pida con
    `mostrar_referencia=True`: esta hoja la entrega el alumno, así que imprimir
    la respuesta sería regalársela. En su lugar va el error relativo, que
    además le sirve al profesor para ver si el cálculo está bien.
    Devuelve None: la hoja es lo que dibuja.
    """
    ex = _EXAMEN
    nombre = ex.id_tarea if ex is not None else 'U2_T3B'
    metodos = (metodo,) if metodo else METODOS_MANO

    _display(_markdown('# 📋 Hoja de trabajo · %s' % nombre))
    _display(_markdown(_identidad_tex(ex)))

    for met in metodos:
        ej = (_MANO_EJ or {}).get(met)
        _display(_markdown('## %s · %s' % (NOMBRE_METODO[met], ej['titulo'])
                           if ej else '## %s' % NOMBRE_METODO[met]))
        if ej is None:
            _display(_markdown('_Todavía no ejecutas `mano_enunciado(%r)`, así '
                               'que no hay nada que calificar aquí._' % met))
            continue

        alumno = _MANO.get(met, [])
        linea = _datos_texto(met, ej)
        if linea:
            _display(_markdown(linea))
        _display(_markdown('**Se reporta:** $%s$' % _reporte_tex(met)))
        _display(_markdown(_tabla_mano(met, alumno, _referencia_mano(met),
                                       mostrar_referencia)))

        if met not in _MANO_RES:
            _display(_markdown('_Sin comprobar: falta ejecutar la celda de la '
                               'actividad a mano._'))
        elif _MANO_RES[met]:
            _display(_markdown('✅ **Acertada.**'))
        else:
            _display(_markdown('❌ **Revisar**: el error relativo tiene que '
                           'quedar por debajo de $%s$. Ojo: si reportas un '
                           'valor que no es (o dejas el $0$ de ejemplo), el '
                           'error sale $1$ —el máximo— porque el divisor es el '
                           'mayor de los dos números.' % _exp_tex(TOL_MANO)))
    if ex is not None:
        _display(_markdown('---'))
        _display(_markdown('Toma una **captura de esta hoja** y mándala junto con '
                           '**fotos de las operaciones hechas a mano** y el '
                           '**enlace de tu cuaderno en Colab**. La nota sale sola '
                           'de las %d preguntas automáticas; la hoja es la '
                           'evidencia de que hiciste las actividades a mano.'
                           % len(ex.preguntas)))


# =====================================================================
#  Utilidades sueltas
# =====================================================================
def raices_de(a):
    """Todas las raíces del polinomio (reales y complejas) con `numpy.roots`.

    `a` son los coeficientes de mayor a menor grado. Devuelve el arreglo de
    raíces, que es lo que usan los laboratorios para comparar.
    """
    return np.roots([float(c) for c in a])


def muller_referencia(f, x0, x1, x2, tol=1e-6, max_iter=100):
    """El Müller DEL MOTOR: lo usan los laboratorios, para no depender de lo
    que el alumno haya escrito (o no) en su celda de práctica.

    Devuelve `(raiz, n_iter)`: la raíz convergida y las iteraciones que tardó.
    """
    from profe.core.solvers import muller
    return muller(f, x0, x1, x2, tol=tol, max_iter=max_iter)


def bairstow_referencia(a, r0, s0, tol=1e-6, max_iter=100):
    """El Bairstow DEL MOTOR: igual que arriba, para los laboratorios.

    Devuelve `(raices, n_iter)`: TODAS las raíces y las iteraciones totales.
    """
    from profe.core.solvers import bairstow
    return bairstow(a, r0, s0, tol=tol, max_iter=max_iter)


def semilla_de(alumno_id):
    """La semilla con la que se sortean los ejercicios de este alumno.

    Devuelve un entero: dos corridas con el mismo correo dan la misma tarea.
    """
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
    'mano_comprueba', 'mano_enunciado', 'mano_ecuacion', 'mano_referencia',
    'mano_solucion',
    'muller_referencia', 'practica', 'pregunta', 'raices_de', 'semilla_de',
    'ultimo_envio', 'ver_preguntas',
]
