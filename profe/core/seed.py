# -*- coding: utf-8 -*-
"""
profe/core/seed.py — Generación determinista de semillas y limpieza del Número de Control.
"""
import hashlib
import re
import numpy as np

def extraer_nc(identificador: str) -> str | None:
    """
    Extrae únicamente la secuencia de dígitos del Número de Control (NC) a partir
    del correo institucional o identificador.

    Formatos aceptados:
      - 'm16330887@hermosillo.tecnm.mx' -> '16330887'
      - '16330887@hermosillo.tecnm.mx'  -> '16330887'
      - 'm{16330887}@tecnm.mx'          -> '16330887'
    """
    if identificador is None:
        return None

    s = str(identificador).strip()

    # 1. Buscar coincidencia entre llaves {NC} si se usa formato explícito
    match_llaves = re.search(r'\{([^}]+)\}', s)
    if match_llaves:
        return match_llaves.group(1).strip()

    # 2. Extraer dígitos de la parte local del correo (antes del @)
    local = s.split('@')[0]
    match_digitos = re.search(r'\d{4,}', local)
    if match_digitos:
        return match_digitos.group(0)

    return None

def generar_semilla(*partes) -> int:
    """
    Genera un entero de 32 bits determinista y reproducible en cualquier plataforma o sesión.

    Uso típico:
        semilla_int = generar_semilla(nc, "U2_T2_Metodos_abiertos")
    """
    texto_unido = '|'.join(str(p) for p in partes)
    digest_hex = hashlib.sha256(texto_unido.encode('utf-8')).hexdigest()
    # Tomar el entero del hash hexadecimal y acotarlo al rango de 32 bits de NumPy
    return int(digest_hex, 16) % (2**32)

def obtener_rng(*partes) -> np.random.Generator:
    """
    Devuelve un generador de números aleatorios NumPy (default_rng) sembrado
    de forma reproducible a partir de las partes enviadas.
    """
    semilla_int = generar_semilla(*partes)
    return np.random.default_rng(semilla_int)
