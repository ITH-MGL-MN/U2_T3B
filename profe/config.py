# -*- coding: utf-8 -*-
"""
profe/config.py — Lectura de la configuración de la tarea.

`config/config.yaml` guarda los pesos, las tolerancias y la URL del webhook;
`config/preguntas.yaml` guarda los bancos teóricos (opción múltiple).

En el bundle ofuscado los dos viajan EMBEBIDOS (`DATOS_CONFIG_YAML` y
`DATOS_PREGUNTAS_YAML`, los pone `tools/build.py`), para que el motor del
alumno no dependa del disco; al importar el paquete en local se leen de
`config/`.
"""
import os

import yaml

try:
    DIR_PROFE = os.path.dirname(os.path.abspath(__file__))
except NameError:            # dentro del bundle (exec) no existe __file__
    DIR_PROFE = os.getcwd()
RAIZ_DIR = os.path.dirname(DIR_PROFE)

_RUTAS = {
    'config/config.yaml': 'DATOS_CONFIG_YAML',
    'config/preguntas.yaml': 'DATOS_PREGUNTAS_YAML',
}


def _embebido(nombre_global):
    """Dato embebido por tools/build.py, o None si corremos desde el disco."""
    if not nombre_global:
        return None
    return globals().get(nombre_global)


def cargar_yaml(ruta_relativa):
    """Lee un YAML de `config/` (o el embebido equivalente en el bundle)."""
    dato = _embebido(_RUTAS.get(ruta_relativa))
    if dato is not None:
        return yaml.safe_load(dato) if isinstance(dato, str) else dato
    with open(os.path.join(RAIZ_DIR, ruta_relativa), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def obtener_configuracion():
    """(config.yaml, preguntas.yaml) ya cargados."""
    cfg = cargar_yaml('config/config.yaml')
    preguntas = cargar_yaml('config/preguntas.yaml')
    return cfg, preguntas


def buscar(dicc, ruta, defecto=None):
    """
    Lee una clave anidada con puntos, sin reventar si falta.

        buscar(cfg, 'evaluacion.min_aprobacion', 0.9)

    Recorre la ruta_alternativa por si el valor está en la raíz (así un
    config.yaml viejo o incompleto no rompe el motor).
    """
    nodo = dicc
    for clave in ruta.split('.'):
        if not isinstance(nodo, dict) or clave not in nodo:
            nodo = None
            break
        nodo = nodo[clave]
    if nodo is not None:
        return nodo
    # Respaldo: la última clave en la raíz del diccionario
    ultima = ruta.split('.')[-1]
    if isinstance(dicc, dict) and ultima in dicc:
        return dicc[ultima]
    return defecto
