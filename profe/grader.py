# -*- coding: utf-8 -*-
"""
profe/grader.py — Fachada del motor de la Tarea 3B.

Es un punto de entrada que re-exporta los nombres que el cuaderno del alumno
conoce. Por dentro llama a los módulos pequeños:

    profe/config.py          pesos, tolerancias y URL del webhook
    profe/core/seed.py       semilla reproducible a partir del NC
    profe/core/modelos.py    las familias de polinomios (Müller/Bairstow)
    profe/core/registry.py   qué variante puede recibir cada método
    profe/core/solvers.py    muller y bairstow de referencia
    profe/core/evaluator.py  generar, calificar y enviar
    profe/ui/cuaderno.py     la API que usa el cuaderno (widgets, mano, envío)
"""
from profe.config import buscar, cargar_yaml, obtener_configuracion
from profe.core import (
    EJERCICIOS,
    ES_DEFECTO,
    MANO_FABRICA,
    MANO_REPORTE,
    MAX_ITER,
    METODOS_MANO,
    NOMBRE_FUNCION,
    NOMBRE_METODO,
    bairstow,
    elegir,
    elegir_mano,
    extraer_nc,
    generar_semilla,
    muller,
    obtener_rng,
    resolver,
)
from profe.core.evaluator import Tarea
from profe.ui.cuaderno import (
    calificar,
    consultar_calificacion,
    enviar,
    generar_examen,
    generar_tarea,
    hoja_manual,
    mano_comprueba,
    mano_enunciado,
    mano_ecuacion,
    mano_referencia,
    mano_solucion,
    practica,
    pregunta,
    raices_de,
    semilla_de,
    ultimo_envio,
    ver_preguntas,
)

# Compatibilidad: la clase se llamaba `Examen` antes de renombrarla.
Examen = Tarea

# Compatibilidad: la función se llamaba `semilla` antes de renombrarla.
semilla = generar_semilla

__all__ = [
    'EJERCICIOS', 'ES_DEFECTO', 'Examen', 'MANO_FABRICA', 'MANO_REPORTE',
    'MAX_ITER', 'METODOS_MANO', 'NOMBRE_FUNCION', 'NOMBRE_METODO', 'Tarea',
    'bairstow', 'buscar', 'cargar_yaml', 'calificar', 'consultar_calificacion',
    'elegir', 'elegir_mano', 'enviar', 'extraer_nc', 'generar_examen',
    'generar_semilla', 'generar_tarea', 'hoja_manual', 'mano_comprueba',
    'mano_enunciado', 'mano_ecuacion', 'mano_referencia', 'mano_solucion',
    'muller',
    'obtener_configuracion', 'obtener_rng', 'practica', 'pregunta',
    'raices_de', 'resolver',
    'semilla', 'semilla_de', 'ultimo_envio', 'ver_preguntas',
]
