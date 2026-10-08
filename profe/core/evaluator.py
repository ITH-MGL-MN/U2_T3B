# -*- coding: utf-8 -*-
"""
profe/core/evaluator.py — Motor de generación, calificación y envío de la tarea.

Los slots (cuántas preguntas, de qué tipo y con qué peso) y las tolerancias
viven en `config/config.yaml`; los bancos teóricos en `config/preguntas.yaml`
y los TEXTOS de las preguntas en `profe/evaluador/<ficha>.md`, con el mismo
formato que los enunciados de `profe/ejercicios/`. La ficha de cada slot se
declara en el propio slot (`ficha: horner_valor`); si no se declara, se usa el
nombre del método.
Todo lo que depende del alumno se sortea con una semilla derivada de su número
de control, así que su tarea es reproducible.
"""
import json
import math
import urllib.request

import numpy as np

from profe.config import buscar, obtener_configuracion
from profe.core import (
    MANO_REPORTE,
    NOMBRE_FUNCION,
    NOMBRE_METODO,
    elegir,
    elegir_mano,
)
from profe.core.helpers import _fmt, _igual, _igual_num
from profe.core.markdown_loader import cargar_pregunta_md, sustituir
from profe.core.seed import extraer_nc, obtener_rng
from profe.core.solvers import bairstow, muller

# Valores por omisión si el config.yaml no los trae
TOLERANCIA_SIMPLE = 1e-6        # respuestas numéricas ('simple'), relativa
TOLERANCIA_FUNCION = 1e-4       # raíz de las preguntas de programación
MIN_APROBACION = 0.9
MAX_INTENTOS_DEFECTO = 2        # envíos permitidos; lo impone el Apps Script
MAX_ITER_DEFECTO = 60
CRITERIOS_PARO = [0.01, 0.1, 0.001]
TOL_ITERACION = 0.5             # tolerancia de "¿en qué iteración...?"
CASOS_OCULTOS = 3
MAX_ITER_ALUMNO = 1000


class Tarea(object):
    def __init__(self, alumno_id, cfg=None, bancos=None):
        self.alumno_id = alumno_id
        self.nc = extraer_nc(alumno_id)
        if not self.nc:
            raise ValueError('No pude leer el Número de Control de %r' % (alumno_id,))

        cfg_disco, bancos_disco = obtener_configuracion()
        self.cfg = cfg_disco if cfg is None else cfg
        self.bancos_teoricos = bancos_disco if bancos is None else bancos

        self.id_tarea = buscar(self.cfg, 'tarea.id', 'U2_T3B')
        self.nombre_tarea = buscar(self.cfg, 'tarea.nombre', self.id_tarea)
        self.tol_simple = float(buscar(self.cfg, 'evaluacion.tolerancia_simple',
                                       buscar(self.cfg, 'evaluacion.tolerancia_porcentual',
                                              TOLERANCIA_SIMPLE)))
        self.tol_funcion = float(buscar(self.cfg, 'evaluacion.tolerancia_funcion',
                                        TOLERANCIA_FUNCION))
        self.min_aprobacion = float(buscar(self.cfg, 'evaluacion.min_aprobacion',
                                           MIN_APROBACION))
        self.max_intentos = int(buscar(self.cfg, 'evaluacion.max_intentos',
                                       MAX_INTENTOS_DEFECTO))
        self.max_iter = int(buscar(self.cfg, 'evaluacion.max_iter', MAX_ITER_DEFECTO))
        self.criterios_paro = [float(v) for v in
                               buscar(self.cfg, 'evaluacion.criterios_paro', CRITERIOS_PARO)]
        self.url = buscar(self.cfg, 'evaluacion.apps_script_url', '')
        self.token = buscar(self.cfg, 'evaluacion.webhook_token', '')
        self.accion = buscar(self.cfg, 'evaluacion.accion', 'guardar')
        self.peso_auto = float(buscar(self.cfg, 'ponderacion.automatico', 0.70))
        self.peso_mano = float(buscar(self.cfg, 'ponderacion.manual', 0.30))

        self.slots = buscar(self.cfg, 'slots', []) or []
        self.rng = obtener_rng(self.nc, self.id_tarea)

        self.preguntas = []
        self.soluciones = []
        self.pesos = [float(sl.get('peso', 0)) for sl in self.slots]
        self.funciones = []

        self._generar()

    def _generar(self):
        """Genera las preguntas asignadas a los slots según la semilla del alumno."""
        for slot in self.slots:
            tipo = slot.get('tipo', 'teorica')
            metodo = slot.get('metodo')
            # Cada slot con texto declara su ficha de profe/evaluador/; si no
            # la declara, la ficha es el nombre del método.
            ficha = slot.get('ficha') or metodo

            if tipo == 'teorica':
                p, s = self._generar_teorica(slot.get('banco'))
            elif tipo == 'ejercicio_num':
                p, s = self._generar_ejercicio_num(metodo, ficha)
            elif tipo == 'vector':
                p, s = self._generar_vector(metodo, ficha)
            elif tipo == 'funcion':
                p, s = self._generar_funcion_oculta(metodo, ficha)
                self.funciones.append(p['funcion'])
            else:
                raise ValueError('Tipo de slot desconocido: %r' % (tipo,))

            self.preguntas.append(p)
            self.soluciones.append(s)

        self.maximo = sum(self.pesos)

    def _generar_teorica(self, banco_nom):
        """Pregunta de opción múltiple: elige del banco y baraja las opciones."""
        banco = (self.bancos_teoricos or {}).get(banco_nom) or []
        if not banco:
            raise ValueError('Banco teórico vacío o no encontrado: %r' % (banco_nom,))
        p_raw = banco[int(self.rng.integers(0, len(banco)))]

        # El orden de las opciones cambia, y con él la LETRA correcta: la
        # solución es la posición que quedó ocupando la opción buena.
        opciones = _reordenar(p_raw['opciones'], int(p_raw.get('correcta', 0)), self.rng)
        p = {
            'titulo': p_raw['titulo'],
            'tipo': 'opcion',
            'texto': p_raw['pregunta'],
            'opciones': [texto for texto, _ in opciones],
        }
        return p, float([i for i, (_, buena) in enumerate(opciones) if buena][0])

    def _generar_ejercicio_num(self, metodo, ficha):
        """
        Pregunta numérica sobre EL MISMO ejercicio de la actividad a mano.

        QUÉ se pregunta lo declara la ficha con `respuesta: p_val` (el nombre
        de la clave en el diccionario del ejercicio), así que la misma
        maquinaria sirve para "reporta P(x0)" y para "reporta P'(x0)" sin
        tocar código.

        Misma semilla y mismo catálogo que `mano_enunciado`, así que el
        alumno ya tiene delante ese enunciado (y su tabla en blanco).
        """
        meta, texto = _ficha(ficha)
        clave = meta.get('respuesta')
        if not clave:
            raise ValueError('La ficha profe/evaluador/%s.md no declara '
                             '`respuesta`' % ficha)

        rng_mano = obtener_rng(self.nc, self.id_tarea, 'mano', metodo)
        ej = elegir_mano(metodo, rng_mano)
        if ej.get(clave) is None:
            raise ValueError('El ejercicio de %s no calcula %r'
                             % (metodo, clave))

        p = {
            'titulo': '%s: %s' % (meta.get('etiqueta') or 'Valor',
                                  NOMBRE_METODO.get(metodo, metodo)),
            'tipo': 'simple',
            'texto': texto,
            '_ej': ej,
            '_mostrar_ejercicio': True,
        }
        return p, float(ej[clave])

    def _generar_vector(self, metodo, ficha):
        """
        Pregunta de VARIOS valores a la vez (los coeficientes del polinomio
        reducido). La respuesta de referencia y sus etiquetas salen de
        `MANO_REPORTE`, que es la misma fuente que usa el cuaderno para la
        actividad a mano: así la pregunta automática y la tabla a mano nunca
        piden cosas distintas.
        """
        meta, texto = _ficha(ficha)
        referencia = MANO_REPORTE.get(metodo)
        if not referencia:
            raise ValueError('El método %r no declara MANO_REPORTE' % (metodo,))

        rng_mano = obtener_rng(self.nc, self.id_tarea, 'mano', metodo)
        ej = elegir_mano(metodo, rng_mano)
        sol = [float(fn(ej)) for _etq, fn in referencia]

        etiquetas = [str(e) for e in (meta.get('etiquetas') or [])]
        if not etiquetas:
            etiquetas = [etq for etq, _fn in referencia]
        if len(etiquetas) != len(sol):
            raise ValueError('La ficha %s.md declara %d etiquetas pero %s '
                             'reporta %d valores'
                             % (ficha, len(etiquetas), metodo,
                                len(sol)))

        p = {
            'titulo': '%s: %s' % (meta.get('etiqueta') or 'Coeficientes',
                                  NOMBRE_METODO.get(metodo, metodo)),
            'tipo': 'vector',
            'texto': texto,
            'etiquetas': etiquetas,
            '_ej': ej,
            '_mostrar_ejercicio': True,
        }
        return p, sol

    def _generar_funcion_oculta(self, metodo, ficha):
        """Pregunta de programación: la función se prueba con casos ocultos."""
        meta, texto = _ficha(ficha)
        # El nombre de la función es el que declara el cuaderno: si la ficha y
        # el registro no coinciden, la pregunta se calificaría sola en el vacío.
        esperado = NOMBRE_FUNCION.get(metodo)
        if esperado is not None and meta.get('funcion') != esperado:
            raise ValueError('profe/evaluador/%s.md declara la funcion %r pero '
                             'NOMBRE_FUNCION dice %r'
                             % (ficha, meta.get('funcion'), esperado))
        casos = _casos_func(metodo, self.rng)
        p = {
            'titulo': 'Programa: %s' % NOMBRE_METODO.get(metodo, metodo),
            'tipo': 'funcion',
            'funcion': meta['funcion'],
            'salida': meta.get('salida', 'escalar'),
            'texto': texto,
            'casos': casos,
            'firma': meta['firma'],
            'ejemplo': meta.get('ejemplo'),
        }
        return p, None

    # -------------------------------------------------------------------------
    # CALIFICACIÓN
    # -------------------------------------------------------------------------
    @staticmethod
    def _num(valor):
        """Convierte a float lo que haya (número, widget, tupla, 'a)')."""
        if valor is None:
            return None
        try:
            if isinstance(valor, (tuple, list, np.ndarray)):
                return float(np.ravel(np.asarray(valor, dtype=float))[0])
            return float(valor)
        except (TypeError, ValueError):
            return None

    def _correcta(self, p, valor, sol):
        """Compara una respuesta numérica o de opción múltiple."""
        num = self._num(valor)
        if num is None or sol is None:
            return False
        tol = p.get('tol')
        if tol is None:
            return abs(num - sol) <= self.tol_simple * max(1.0, abs(sol))
        return abs(num - sol) <= tol

    def calificar(self, respuestas, marco=None):
        """Devuelve una fila de detalle por pregunta (puntos, estado, solución)."""
        filas_res = []

        for i, (p, sol) in enumerate(zip(self.preguntas, self.soluciones), 1):
            peso = self.pesos[i - 1]

            if p['tipo'] == 'funcion':
                filas_res.append(self._calificar_funcion(i, p, peso, marco))
                continue
            if p['tipo'] == 'vector':
                filas_res.append(self._calificar_vector(i, p, peso,
                                                        respuestas.get(i), sol))
                continue

            val_alumno = respuestas.get(i)
            if val_alumno is None:
                filas_res.append({
                    'i': i, 'estado': 'sin respuesta', 'puntos': 0.0,
                    'peso': peso, 'sol': sol, 'val': None
                })
                continue

            ok = self._correcta(p, val_alumno, sol)
            filas_res.append({
                'i': i, 'estado': 'correcta' if ok else 'incorrecta',
                'puntos': peso if ok else 0.0, 'peso': peso,
                'sol': sol, 'val': val_alumno
            })

        return filas_res

    def _calificar_vector(self, i, p, peso, valor, sol):
        """
        Califica una respuesta de VARIOS valores (los coeficientes del
        polinomio reducido): cada componente correcta aporta su fracción del
        peso, así que se puede sacar crédito parcial.
        """
        etiquetas = p.get('etiquetas') or []
        valores = _lista_numeros(valor)
        if valores is None or not sol:
            return {'i': i, 'estado': 'sin respuesta', 'puntos': 0.0,
                    'peso': peso, 'sol': sol, 'val': valor,
                    'etiquetas': etiquetas, 'aciertos': 0}

        aciertos = 0
        for j, esperado in enumerate(sol):
            obtenido = valores[j] if j < len(valores) else None
            if obtenido is not None and _igual_num(obtenido, esperado,
                                                   self.tol_simple):
                aciertos += 1

        n = len(sol)
        puntos = peso * aciertos / float(n)
        estado = ('correcta' if aciertos == n
                  else ('parcial' if aciertos else 'incorrecta'))
        return {'i': i, 'estado': estado, 'puntos': puntos, 'peso': peso,
                'sol': sol, 'val': valor, 'etiquetas': etiquetas,
                'aciertos': aciertos}

    def _calificar_funcion(self, i, p, peso, marco):
        """
        Prueba la función del alumno con los casos ocultos. Cada caso aporta
        la misma fracción del peso.

        Con `salida: escalar` (métodos iterativos) se revisa que la raíz
        coincida y que el número de iteraciones sea razonable; con cualquier
        otra salida se comparan TODOS los valores que devuelve la función
        (tuplas, listas y complejos incluidos).
        """
        fn_alumno = None
        if marco is not None:
            fn_alumno = marco.f_globals.get(p['funcion'])

        aciertos, total = 0, 0
        detalle = []

        for entrada, esperado in (p.get('casos') or []):
            total += 1
            res = None
            ok = False

            if callable(fn_alumno):
                try:
                    res = fn_alumno(*entrada)
                except Exception:                      # noqa: BLE001
                    res = None

            if res is not None:
                if p.get('salida') == 'raices':
                    # Bairstow: una LISTA de raíces (reales y complejas) en
                    # cualquier orden. Se casa cada raíz con su pareja.
                    ok = _igual_raices(res, esperado, self.tol_funcion)
                elif p.get('salida', 'escalar') == 'escalar':
                    # (raiz, n_iteraciones): la raíz y un conteo razonable.
                    raiz, nit = None, None
                    try:
                        if isinstance(res, (tuple, list, np.ndarray)) and len(res) >= 2:
                            raiz, nit = self._num(res[0]), self._num(res[1])
                        else:
                            raiz, nit = self._num(res), 999
                    except Exception:                  # noqa: BLE001
                        raiz, nit = None, None
                    if raiz is not None and nit is not None:
                        bien_raiz = (abs(raiz - esperado)
                                     <= self.tol_funcion * max(1.0, abs(esperado)))
                        ok = bool(bien_raiz and 1 <= nit <= MAX_ITER_ALUMNO)
                else:
                    # Varios valores a la vez: se comparan TODOS, componente a
                    # componente y con tolerancia relativa (soporta complejos).
                    ok = _igual(res, esperado, self.tol_funcion)

            aciertos += 1 if ok else 0
            detalle.append((p['funcion'], esperado, res, ok))

        if total == 0:
            return {'i': i, 'estado': 'sin respuesta', 'puntos': 0.0, 'peso': peso,
                    'sol': None, 'val': None}

        puntos = peso * aciertos / float(total)
        estado = 'correcta' if aciertos == total else ('parcial' if aciertos else 'incorrecta')
        return {'i': i, 'estado': estado, 'puntos': puntos, 'peso': peso,
                'sol': p, 'val': detalle}

    # -------------------------------------------------------------------------
    # ENVÍO A GOOGLE APPS SCRIPT
    # -------------------------------------------------------------------------
    def enviar(self, respuestas, marco=None, debug=False, correo=None):
        """
        Califica y envía el resultado automático al Apps Script.

        Devuelve un diccionario con el resultado (no imprime nada: de la
        realimentación al alumno se encarga `profe.ui.cuaderno`).
        """
        filas = self.calificar(respuestas, marco)
        puntos = sum(f['puntos'] for f in filas)
        maximo = sum(f['peso'] for f in filas)
        calif = 100.0 * (puntos / maximo) if maximo > 0 else 0.0

        resultado = {
            'enviado': False,
            'calificacion': calif,
            'puntos': puntos,
            'maximo': maximo,
            'minimo': self.min_aprobacion * 100.0,
            'filas': filas,
        }

        if calif < self.min_aprobacion * 100.0:
            resultado['motivo'] = 'minimo'
            return resultado

        # El Apps Script (doPost.gs -> procesarTarea) no se fía del resumen:
        # exige `respuestas` (el PUNTAJE de cada pregunta), `pesos` y
        # `maxPuntos`, y con eso reconstruye las columnas R1..Rn y el total
        # escalado a 100. Sin `respuestas` responde
        #   {"status":"error","message":"Las respuestas deben ser un arreglo..."}
        # y NO guarda nada en la hoja.
        cuerpo = {
            'token': self.token,
            'accion': self.accion,
            'tarea': self.id_tarea,
            'NC': self.nc,
            'correo': correo or self.alumno_id,
            'calificacion': round(calif, 1),
            'automatico': round(puntos, 2),
            'maximo': maximo,
            'respuestas': [round(f['puntos'], 4) for f in filas],
            'pesos': list(self.pesos),
            'maxPuntos': max(self.pesos) if self.pesos else 2,
        }
        resultado['cuerpo'] = cuerpo

        if debug:
            return resultado

        datos = json.dumps(cuerpo).encode('utf-8')
        pet = urllib.request.Request(
            self.url, data=datos,
            headers={'Content-Type': 'text/plain;charset=utf-8'})
        try:
            with urllib.request.urlopen(pet, timeout=30) as resp:
                texto = resp.read().decode('utf-8', 'replace')
            resultado['respuesta'] = texto
            # El Apps Script contesta 200 aunque RECHAZE el envío, así que hay
            # que mirar el cuerpo: si trae status=error, no se guardó nada.
            try:
                aviso = json.loads(texto)
            except ValueError:
                aviso = None
            resultado['aviso'] = aviso
            if isinstance(aviso, dict) and str(aviso.get('status', '')).lower() == 'error':
                resultado['enviado'] = False
                resultado['motivo'] = 'servidor'
                resultado['error'] = aviso.get('message', texto)
            else:
                resultado['enviado'] = True
        except Exception as exc:                            # noqa: BLE001
            resultado['motivo'] = 'red'
            resultado['error'] = str(exc)
        return resultado

    def consultar(self, timeout=30):
        """
        Pregunta al Apps Script qué hay guardado para este NC.

        Usa la acción `intento`, que es de SOLO LECTURA: no escribe nada en la
        hoja de cálculo, así que se puede llamar las veces que haga falta.
        Sirve para saber cuántos intentos se han gastado antes de enviar.

        Devuelve un diccionario con 'ok' y, si todo salió bien, los datos que
        reporta la hoja: semilla, intento, estado, total y enviado.
        """
        if not self.url:
            return {'ok': False, 'error': 'el webhook no está configurado'}
        cuerpo = {'token': self.token, 'accion': 'intento',
                  'tarea': self.id_tarea, 'NC': self.nc}
        pet = urllib.request.Request(
            self.url, data=json.dumps(cuerpo).encode('utf-8'),
            headers={'Content-Type': 'text/plain;charset=utf-8'})
        try:
            with urllib.request.urlopen(pet, timeout=timeout) as resp:
                texto = resp.read().decode('utf-8', 'replace')
        except Exception as exc:                            # noqa: BLE001
            return {'ok': False, 'error': str(exc)}

        try:
            aviso = json.loads(texto)
        except ValueError:
            return {'ok': False, 'error': texto, 'respuesta': texto}
        if str(aviso.get('status', '')).lower() == 'error':
            return {'ok': False, 'error': aviso.get('message', texto),
                    'respuesta': texto}

        res = {'ok': True, 'respuesta': texto}
        res.update(aviso.get('data') or {})
        return res


# =====================================================================
#  BANCOS AUXILIARES: opciones, conceptos y textos de las preguntas
# =====================================================================
def _reordenar(opciones, idx_correcta, rng):
    """
    Reetiqueta las opciones a) b) c) d) y mueve la correcta a una posición al
    azar. Las opciones del banco vienen como 'a) texto' y la correcta la
    indica el campo `correcta` del YAML.

    Devuelve una lista de pares (texto_con_letra, es_la_correcta).
    """
    cuerpos = []
    for op in opciones:
        op = str(op).strip()
        cuerpos.append(op[2:].strip() if len(op) > 2 and op[1] == ')' else op)

    if not (0 <= idx_correcta < len(cuerpos)):
        idx_correcta = 0

    correcta = cuerpos.pop(idx_correcta)
    posicion = int(rng.integers(0, len(cuerpos) + 1))
    cuerpos.insert(posicion, correcta)

    return [('%s) %s' % (chr(97 + j), texto), j == posicion)
            for j, texto in enumerate(cuerpos)]


# =====================================================================
#  FICHAS (profe/evaluador/<ficha>.md)
#
#  El nombre de la ficha ES el nombre del archivo: el slot la declara con
#  `ficha: horner_valor` y el motor lee `profe/evaluador/horner_valor.md`
#  (si el slot no la declara, se usa el nombre del método).
#
#  El frontmatter lleva lo que la pregunta necesita:
#     tipo funcion -> `funcion`, `firma`, `salida` y una llamada de `ejemplo`
#                     (`salida: tupla` compara todos los valores devueltos;
#                      `salida: escalar` es el caso (raiz, n_iteraciones))
#     tipo simple  -> `respuesta` (la clave del valor que se pregunta),
#                     `etiqueta` y `unidad`
#     tipo vector  -> `n` y `etiquetas` (una por casilla)
#  y el cuerpo es el Markdown que lee el alumno.
# =====================================================================
_FICHAS = {}


def _ficha(ficha):
    """`(meta, texto)` de una ficha de `profe/evaluador/`."""
    if ficha not in _FICHAS:
        archivo = '%s.md' % ficha
        try:
            meta, texto = cargar_pregunta_md(archivo)
        except (IOError, OSError):
            raise ValueError('No existe profe/evaluador/%s (lo pide un slot).'
                             % archivo)
        _FICHAS[ficha] = (meta, texto)
    return _FICHAS[ficha]


def _lista_numeros(valor):
    """
    Normaliza la respuesta de un widget de vectores a una lista de floats.

    Acepta la lista de casillas, una cadena '1 -2 3' o '1, -2, 3' y un número
    suelto. Devuelve None si algo no se puede leer como número.
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        partes = valor.replace(',', ' ').replace(';', ' ').split()
    else:
        try:
            partes = list(valor)
        except TypeError:
            partes = [valor]
    salida = []
    for parte in partes:
        try:
            salida.append(float(parte))
        except (TypeError, ValueError):
            return None
    return salida


# =====================================================================
#  CASOS OCULTOS DE LAS PREGUNTAS DE PROGRAMACIÓN
#
#  Son problemas DISTINTOS a los del alumno (nunca los ve): si su función
#  conoce el método, los resuelve; si devuelve un número fijo, falla.
#  El valor esperado NO es una fórmula escrita a mano: lo calcula el solver
#  de referencia (`solvers.muller` / `solvers.bairstow`), así que la
#  comparación siempre es consistente con lo que califica el resto.
# =====================================================================
def _func_poli_oculta(a):
    """f(x) = a_n x^n + ... + a_0 (para los casos ocultos de Müller)."""
    n = len(a) - 1

    def f(x):
        return sum(c * x ** (n - i) for i, c in enumerate(a))
    return f


def _casos_func(metodo, rng):
    """Casos ocultos: lista de (entrada, esperado) con valores sembrados."""
    casos = []
    if metodo == 'MULLER':
        for _ in range(CASOS_OCULTOS):
            b = int(rng.integers(-15, -11))
            c = int(rng.integers(8, 15))
            f = _func_poli_oculta([1, 0, b, -c])
            x0 = round(float(rng.uniform(3.0, 3.6)), 1)
            x1 = round(float(rng.uniform(4.4, 4.8)), 1)
            x2 = round(float(rng.uniform(3.8, 4.2)), 1)
            raiz, _ = muller(f, x0, x1, x2, tol=1e-9, max_iter=200)
            casos.append(((f, x0, x1, x2), raiz))
        return casos
    if metodo == 'BAIRSTOW':
        for _ in range(CASOS_OCULTOS):
            p = int(rng.integers(1, 4))
            q = int(rng.integers(2, 5))
            t = int(rng.integers(1, 4))
            if p == q == t:
                t += 1
            a = [1, p + q + t, p * q + p * t + q * t, p * q * t]
            r0 = -(p + q) + 0.5
            s0 = -(p * q) + 0.5
            raices, _ = bairstow(a, r0, s0, tol=1e-9, max_iter=200)
            casos.append(((a, r0, s0), raices))
        return casos
    raise ValueError('Método desconocido en los casos ocultos: %r' % (metodo,))


def _igual_raices(res, ref, tol):
    """
    ¿Devuelve el alumno las mismas raíces que la referencia, en cualquier orden?

    `res` puede ser la lista de raíces o la tupla `(lista, n_iteraciones)` de
    Bairstow. Se casa cada raíz (real o compleja) con una pareja de la
    referencia por tolerancia relativa.
    """
    if (isinstance(res, (tuple, list)) and len(res) == 2
            and isinstance(res[0], (tuple, list, np.ndarray))):
        res = res[0]
    try:
        alumno = [complex(v) for v in res]
        referencia = [complex(v) for v in ref]
    except (TypeError, ValueError):
        return False
    if len(alumno) != len(referencia):
        return False
    pendientes = list(referencia)
    for v in alumno:
        pareja = None
        for i, w in enumerate(pendientes):
            if abs(v - w) <= tol * max(1.0, abs(w)):
                pareja = i
                break
        if pareja is None:
            return False
        pendientes.pop(pareja)
    return True
