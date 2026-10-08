# -*- coding: utf-8 -*-
"""
tools/build.py — Empaquetador del motor para Google Colab.

Junta los módulos, los YAML de `config/` y los textos de `profe/ejercicios/`
y `profe/evaluador/` en un solo archivo y escribe dos cosas:

    grader_ofuscado.txt   el blob base64+zlib que descomprime el cuaderno
    grader_local.py       el MISMO bundle, legible, para depurar en local

    Colab (lo que ve el alumno) -> grader_ofuscado.txt
    PC local (depuración)       -> grader_local.py

Los dos salen de las mismas fuentes, así que el modo local y el modo Colab
ejecutan exactamente el mismo código; lo único que cambia es de dónde leen los
datos (embebidos en el bundle, o del disco al importar el paquete).

Uso:  python tools/build.py
"""
import base64
import glob
import os
import zlib

import yaml

RAIZ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Orden de dependencia: cada módulo puede usar lo definido antes.
MODULOS = [
    'profe/config.py',
    'profe/core/helpers.py',
    'profe/core/seed.py',
    'profe/core/markdown_loader.py',
    'profe/core/modelos.py',
    'profe/core/registry.py',
    'profe/core/solvers.py',
    'profe/core/evaluator.py',
    'profe/ui/cuaderno.py',
]

CABECERA = (
    '# -*- coding: utf-8 -*-\n'
    '# Bundle del autograder U2_T3B — generado por tools/build.py, no editar a mano.\n'
    '# Contiene el motor completo (config + ejercicios + cuaderno) en un namespace.\n'
)


def leer(ruta_relativa):
    with open(os.path.join(RAIZ_DIR, ruta_relativa), 'r', encoding='utf-8') as f:
        return f.read()


def _sin_imports_internos(contenido):
    """
    Quita los imports entre los módulos del motor: en el bundle todo vive en
    un único namespace, así que ya están definidos. Los imports de librerías
    (numpy, yaml, math...) se conservan.

    Cuidado con los que ocupan varias líneas:

        from .modelos import (
            _ej_horner_calibracion,
            ...
        )
    """
    salida = []
    saltando = False
    for linea in contenido.splitlines():
        texto = linea.strip()
        if saltando:
            # Seguimos dentro del paréntesis del import hasta cerrarlo.
            if ')' in texto:
                saltando = False
            continue
        if (texto.startswith('from profe') or texto.startswith('import profe')
                or texto.startswith('from .') or texto.startswith('import .')):
            if '(' in texto and ')' not in texto:
                saltando = True
            continue
        salida.append(linea)
    return '\n'.join(salida)


def _textos(carpeta, obligatorio=True):
    """{nombre_archivo: contenido} de todos los .md de una carpeta."""
    textos = {}
    patron = os.path.join(RAIZ_DIR, carpeta, '*.md')
    for ruta in sorted(glob.glob(patron)):
        with open(ruta, 'r', encoding='utf-8') as f:
            textos[os.path.basename(ruta)] = f.read()
    if obligatorio and not textos:
        raise SystemExit('No encontré ningún .md en %s' % carpeta)
    return textos


def construir_bundle():
    print('Empaquetando el autograder...')

    # 1) Datos: los YAML de config/, los enunciados y las fichas de preguntas.
    cfg = yaml.safe_load(leer('config/config.yaml'))
    preguntas = yaml.safe_load(leer('config/preguntas.yaml'))
    textos_md = _textos('profe/ejercicios')
    textos_eval = _textos('profe/evaluador')

    # 2) Código: los módulos, en orden de dependencia.
    partes = [CABECERA, '']
    partes.append('# ------------------- datos embebidos -------------------')
    partes.append('# Los leen profe/config.py y profe/core/markdown_loader.py.')
    partes.append('DATOS_CONFIG_YAML = %r' % (cfg,))
    partes.append('DATOS_PREGUNTAS_YAML = %r' % (preguntas,))
    partes.append('DATOS_MARKDOWN_DICT = %r' % (textos_md,))
    partes.append('DATOS_EVALUADOR_DICT = %r' % (textos_eval,))
    partes.append('')

    for modulo in MODULOS:
        print('   + %s' % modulo)
        partes.append('# ================= %s =================' % modulo)
        partes.append(_sin_imports_internos(leer(modulo)))
        partes.append('')

    codigo = '\n'.join(partes)

    # 3) Salidas: el bundle legible y el blob ofuscado.
    ruta_local = os.path.join(RAIZ_DIR, 'grader_local.py')
    with open(ruta_local, 'w', encoding='utf-8') as f:
        f.write(codigo)

    blob = base64.b64encode(zlib.compress(codigo.encode('utf-8'), 9)).decode('ascii')
    ruta_ofuscada = os.path.join(RAIZ_DIR, 'grader_ofuscado.txt')
    with open(ruta_ofuscada, 'w', encoding='utf-8') as f:
        f.write(blob)

    print('\nListo:')
    print('   grader_local.py     %6.1f KB  (legible, para depurar en local)'
          % (os.path.getsize(ruta_local) / 1024.0))
    print('   grader_ofuscado.txt %6.1f KB  (blob, lo usa el cuaderno en Colab)'
          % (os.path.getsize(ruta_ofuscada) / 1024.0))
    print('   módulos: %d   enunciados: %d   fichas: %d'
          % (len(MODULOS), len(textos_md), len(textos_eval)))


if __name__ == '__main__':
    construir_bundle()
