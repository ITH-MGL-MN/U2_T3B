# -*- coding: utf-8 -*-
"""
profe/core/markdown_loader.py — Textos Markdown del motor.

Dos familias, con el mismo formato (`--- YAML ---` + cuerpo Markdown):

  profe/ejercicios/<nombre>.md   enunciados con datos aleatorios (`rangos`)
  profe/evaluador/<nombre>.md    textos de las preguntas del examen

Los textos viajan EMBEBIDOS en el bundle (`DATOS_MARKDOWN_DICT` y
`DATOS_EVALUADOR_DICT`, los pone `tools/build.py`) para que el motor
ofuscado no necesite el disco; al importar el paquete en local se leen de
esas carpetas.
"""
import os
import re

import yaml

from .helpers import _r, _fmt

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:            # dentro del bundle (exec) no existe __file__
    _AQUI = os.getcwd()
DIR_EJERCICIOS = os.path.normpath(os.path.join(_AQUI, '..', 'ejercicios'))
DIR_EVALUADOR = os.path.normpath(os.path.join(_AQUI, '..', 'evaluador'))

_CACHE = {}

# Marcadores del enunciado: un nombre sencillo entre llaves, {x0}, {lam}, {m}.
# NO tocamos las llaves de LaTeX (\frac{x^2-3}{2}, e^{-ct/m}) porque no son
# identificadores sueltos: así el .md sigue siendo LaTeX legible.
#
# La guarda `(?<![\}\^\{\\_\w])` evita el único caso en que un marcador y el
# LaTeX chocan: un argumento de `\frac` escrito como `{v}`. En
# `\frac{g m}{v}` la llave va precedida de `}` y en `\frac{24}{Re}` también,
# así que ninguna de las dos se sustituye aunque `v` o `Re` sean variables
# sorteadas. Si el `{` va precedido de `^`, `{`, `_` o de una letra (como en
# `\frac{a}{v^2}`) tampoco es un marcador.
_PLACEHOLDER = re.compile(r'(?<![\}\^\{\\_\w])\{([A-Za-z_][A-Za-z_0-9]*)\}')


def sustituir(texto, **valores):
    """
    Reemplaza los marcadores `{nombre}` por sus valores YA formateados.

    Los marcadores que no estén en `valores` se dejan tal cual, así que
    también sirve para completar valores que la fábrica calcula después
    de sortear (por ejemplo `r` y `x0` en el ejercicio de la raíz doble).

    Un `{nombre}` que forme parte de LaTeX (argumento de `\\frac` o similar)
    tampoco se sustituye: ver `_PLACEHOLDER`.
    """
    return _PLACEHOLDER.sub(
        lambda m: str(valores[m.group(1)]) if m.group(1) in valores else m.group(0),
        texto)


def _texto(nombre_archivo, carpeta, clave_embebida):
    """
    Markdown del archivo: primero el embebido del bundle (lo pone
    tools/build.py), si no, del disco.

    El nombre del dict embebido se busca en los globals en tiempo de
    ejecución: dentro del bundle viven en el namespace del cuaderno y al
    importar el paquete no existen (así que se lee del disco).
    """
    embebido = globals().get(clave_embebida)
    if isinstance(embebido, dict) and nombre_archivo in embebido:
        return embebido[nombre_archivo]

    clave = (carpeta, nombre_archivo)
    if clave not in _CACHE:
        with open(os.path.join(carpeta, nombre_archivo), 'r',
                  encoding='utf-8') as f:
            _CACHE[clave] = f.read()
    return _CACHE[clave]


def _partir_frontmatter(contenido, nombre_archivo):
    """Separa `--- YAML --- cuerpo` y devuelve (meta, cuerpo)."""
    partes = re.split(r'^---\s*$', contenido, flags=re.MULTILINE)
    if len(partes) < 3:
        raise ValueError('%s no tiene frontmatter YAML (--- ... ---)' % nombre_archivo)
    return yaml.safe_load(partes[1]) or {}, partes[2]


def cargar_ejercicio_md(nombre_archivo, rng):
    """
    Devuelve `(meta, cuerpo_formateado, valores)` del ejercicio indicado.

    `meta`     : el frontmatter YAML (titulo, incognita, unidad, rangos, ...)
    `cuerpo`   : el Markdown con los valores sorteados ya sustituidos
    `valores`  : dict variable -> valor numerico sorteado
    """
    contenido = _texto(nombre_archivo, DIR_EJERCICIOS, 'DATOS_MARKDOWN_DICT')
    meta, cuerpo_md = _partir_frontmatter(contenido, nombre_archivo)

    # Aleatorizar variables según los rangos definidos en el YAML
    datos = {}
    valores_fmt = {}
    for var, (lo, hi, dec) in meta.get('rangos', {}).items():
        val = _r(rng, lo, hi, dec)
        datos[var] = val
        valores_fmt[var] = _fmt(val, dec)

    # Inyectar los valores reales en la plantilla del texto Markdown
    contexto_formateado = sustituir(cuerpo_md, **valores_fmt)

    return meta, contexto_formateado, datos


def cargar_pregunta_md(nombre_archivo, **valores):
    """
    Texto de una pregunta del examen: `(meta, cuerpo)` de `profe/evaluador/`.

    El frontmatter lleva lo que la pregunta necesita (nombre de la función,
    firma exacta, llamada de ejemplo, opciones del concepto...) y el cuerpo es
    el Markdown que lee el alumno, con marcadores `{...}` que se sustituyen
    aquí.
    """
    contenido = _texto(nombre_archivo, DIR_EVALUADOR, 'DATOS_EVALUADOR_DICT')
    meta, cuerpo = _partir_frontmatter(contenido, nombre_archivo)
    return meta, sustituir(cuerpo, **valores).strip()
