# -*- coding: utf-8 -*-
"""
tools/visualizar.py — herramienta de visualización: tablas y gráficas.

Esto NO es parte del motor de calificación. Son utilidades para PRESENTAR los
resultados de un experimento numérico, y están a la vista a propósito: las
puedes leer, copiar y usar en tus propios cuadernos cuando quieras.

    latex_cientifico(valor)               cifra en notación científica de LaTeX
    tabla_experimento(columnas, filas)    tabla de Markdown a partir de los datos
    bits_flotante(numero, precision)      los bits IEEE 754: signo, exponente y mantisa
    graficar_polinomio(a, x0, raices)     la curva de P(x) con sus marcas
    graficar_errores(x, series)           varias curvas de error contra la misma x

El cuaderno del curso la carga solo, en la celda de configuración
(`from visualizar import ...`), así que basta con llamarlas. No dependen del
motor: si copias este archivo a otro cuaderno, las funciones siguen
funcionando igual (necesitan numpy, y matplotlib solo para las gráficas).

Todas siguen la misma regla, y es a propósito:

    mostrar=True  (por omisión)   saca la tabla o la figura y no devuelve nada
    mostrar=False                 no saca nada y devuelve el texto o la figura

Así una celda que termina en `tabla_experimento(...)` muestra SOLO la tabla. Si
la función devolviera el texto, el cuaderno lo imprimiría ADEMÁS como resultado
de la celda, en texto plano y con sus `|` y sus `\\n` a la vista.
"""
import struct

import numpy as np

__all__ = ['bits_flotante', 'graficar_errores', 'graficar_polinomio',
           'latex_cientifico', 'tabla_experimento']


def _display(*objetos):
    """`display` de IPython, importado solo cuando se usa."""
    from IPython.display import display
    return display(*objetos)


def _markdown(texto):
    from IPython.display import Markdown
    return Markdown(texto)


def _plt():
    """`matplotlib.pyplot`, importado solo cuando se va a graficar."""
    import matplotlib.pyplot as plt
    return plt


# =====================================================================
#  Cifras
# =====================================================================
def latex_cientifico(valor, dec=3):
    """
    Cifra en notación científica de LaTeX, para las tablas de los laboratorios:

        3.55e-09  ->  '3.55\\times 10^{-9}'

    En LaTeX, escribir `$3.55e-09$` sale con la «e» en cursiva y parece una
    variable; así sale como el número que es. `dec` es el número de decimales de
    la mantisa: con 16 se ven las 17 cifras de un `float`. El cero se devuelve
    como `'0'` (un error de cero es un resultado, no una cifra diminuta).
    """
    if valor == 0 or valor == 0.0:
        return "0"
    try:
        mantisa, exponente = (("%." + str(dec) + "e") % float(valor)).split("e")
        return r"%s\times 10^{%d}" % (mantisa, int(exponente))
    except (TypeError, ValueError):
        return str(valor)


# =====================================================================
#  Bits (formato IEEE 754)
# =====================================================================
#  Ver los bits es lo único que hace tangible de dónde salen "unas 16 cifras"
#  y "rango de 10^308": los bits del exponente dan el RANGO, y los de la
#  mantisa la PRECISIÓN. Cambiar de float64 a float32 quita bits de los dos.
_IEEE = {
    # precisión: (nombre, molde al empaquetar, molde para leer el entero,
    #             bits totales, bits de exponente, bits de mantisa)
    'float64': ('doble, 64 bits', '>d', '>Q', 64, 11, 52),
    'float32': ('simple, 32 bits', '>f', '>I', 32, 8, 23),
}

def bits_flotante(numero, precision='float64', mostrar=True):
    """
    Muestra la estructura IEEE 754 de un número: signo, exponente y mantisa.

    Sirve para VER de dónde salen las 16 cifras y el rango. Escribe 0.1 y
    cambia la precisión a `float32` para ver la diferencia entre simple y
    doble: con 23 bits de mantisa el número guardado ya no es 0.1.

    La tabla la dibuja `tabla_experimento`, así que se ve igual que las de los
    laboratorios, y los bits van entre acentos graves para que salgan con ancho
    fijo y se note dónde empieza cada sección.

    Los números se escriben con `%r` en el título, la forma más corta que al
    releerla da el mismo valor: para 0.1 sale `0.1`, que es lo que escribiste.
    En 'Valor guardado' va el número de máquina con las cifras que hacen falta
    para identificarlo, y en el pie su valor exacto. Así se distinguen las tres
    cosas: lo que escribiste, lo que se guarda y lo que eso vale de verdad.

    Parámetros
    ----------
    numero    : el número que se quiere inspeccionar
    precision : 'float64' (por omisión) o 'float32'
    mostrar   : True (por omisión) la imprime y no devuelve nada; con False
                devuelve el texto de la tabla (para pegarlo en otro sitio o
                comprobarlo desde una prueba)

    Devuelve
    --------
    None si la imprimió, o el texto de la tabla si pediste `mostrar=False`.
    """
    if precision not in _IEEE:
        raise ValueError("Precisión no soportada: usa 'float64' o 'float32'.")
    nombre, empaqueta, desempaqueta, total, bits_exp, bits_mant = _IEEE[precision]

    try:
        datos = struct.pack(empaqueta, float(numero))
    except (OverflowError, struct.error):
        texto = ('**%r no cabe en %s**: el mayor es %.3e, y el menor normal '
                 '%.3e. Ese es el otro lado del **rango**.'
                 % (float(numero), precision, float(np.finfo(precision).max),
                    float(np.finfo(precision).tiny)))
        if mostrar:
            _display(_markdown(texto))
            return None
        return texto

    guardado = struct.unpack(empaqueta, datos)[0]
    bits = bin(struct.unpack(desempaqueta, datos)[0])[2:].zfill(total)
    signo = bits[0]
    exp_bits = bits[1:1 + bits_exp]
    mant_bits = bits[1 + bits_exp:]

    sesgo = 2 ** (bits_exp - 1) - 1
    crudo = int(exp_bits, 2)
    if crudo == 0:
        # Cero o subnormal: el 1 de delante de la mantisa no existe.
        exponente, implicito = 1 - sesgo, 0.0
    else:
        exponente, implicito = crudo - sesgo, 1.0
    filas = [
        ['Signo ($S$)', '`%s`' % signo,
         'positivo' if signo == '0' else 'negativo'],
        ['Exponente ($E$)', '`%s`' % exp_bits,
         '%d − %d = %d' % (crudo, sesgo, exponente)],
        ['Mantisa ($M$)', '`%s`' % mant_bits,
         'los %d bits que se suman a %d' % (bits_mant, implicito)],
        ['En memoria', '`%s`' % ' '.join((signo, exp_bits, mant_bits)),
         '%d bits, en este orden' % total],
        ['Valor guardado', '`%.17g`' % guardado,
         '±(%d.M) × 2^%d' % (implicito, exponente)],
    ]
    # Para el pie: `Decimal` da el valor exacto del binario, sin redondearlo a
    # decimal, y `Fraction` sirve para saber si lo escrito y lo guardado son o
    # no el mismo número.
    from decimal import Decimal
    from fractions import Fraction

    avisos = []
    if Fraction(repr(float(numero))) != Fraction(guardado):
        avisos.append('**%r** no se guarda exacto: el número que queda en '
                      'memoria, con todas sus cifras, es `%s`'
                      % (float(numero), Decimal(guardado)))
    if guardado != float(numero):
        error = abs(guardado - float(numero)) / abs(float(numero))
        avisos.append('y no es el que escribiste: difiere en `%r`, el %.1f %% '
                      'del épsilon de %s'
                      % (guardado - float(numero),
                         100.0 * error / float(np.finfo(precision).eps),
                         precision))

    return tabla_experimento(
        [('Sección', 'l'), ('Bits', 'l'), ('Qué es', 'l')], filas,
        titulo='**%r** en **%s** (%s)' % (float(numero), precision, nombre),
        pie='  \n'.join(avisos) or None, mostrar=mostrar)


# =====================================================================
#  Tablas
# =====================================================================
#  Los laboratorios imprimen tablas de experimentos (una fila por caso, una
#  columna por magnitud). Armarlas a mano es donde se cuelan los errores que
#  NO se ven, así que se arman aquí.
_FORMATOS_TABLA = {
    'texto': lambda v: str(v),
    'entero': lambda v: '$%d$' % v,
}
_ALINEACIONES = {'l': ':---', 'c': ':---:', 'r': '---:'}


def _formateador_columna(formato):
    """
    Convierte la descripción de una columna en una función `celda -> texto`.

    Se acepta, en este orden:
      * una función tuya            lambda v: '$%s$' % latex_cientifico(v, 2)
      * un molde de impresión       '$%.17g$'   (por llevar '%')
      * 'texto' / 'entero'          str(v) / '$%d$'
      * 'ciencia' / 'ciencia16'     notación científica de LaTeX, con ese
                                    número de decimales en la mantisa
      * 'num2' / 'num6'             '$%.2f$' / '$%.6f$'
    """
    if formato is None:
        formato = 'texto'
    if callable(formato):
        return formato
    if isinstance(formato, str):
        if formato in _FORMATOS_TABLA:
            return _FORMATOS_TABLA[formato]
        if formato.startswith('ciencia'):
            sufijo = formato[len('ciencia'):]
            dec = int(sufijo) if sufijo.isdigit() else 3
            return lambda v: '$%s$' % latex_cientifico(v, dec)
        if formato.startswith('num') and formato[3:].isdigit():
            return lambda v: '$%.*f$' % (int(formato[3:]), v)
        if '%' in formato:
            return lambda v: formato % (v,)
    raise ValueError(
        "No sé qué formato es %r. Usa 'texto', 'entero', 'ciencia<N>', "
        "'num<N>', un molde con '%%' o una función." % (formato,))


def tabla_experimento(columnas, filas, titulo=None, pie=None, mostrar=True):
    """
    Imprime una tabla de laboratorio.

    Escribe los '|' y la fila de alineación por ti, que es donde se cometen los
    errores que no avisan: si esa fila no tiene el mismo número de columnas que
    el encabezado, Jupyter dibuja la tabla torcida **y no dice nada**. Aquí se
    arma sola, y si una fila trae más o menos celdas de las que toca se levanta
    un error que dice CUÁL fila es.

    Parámetros
    ----------
    columnas : una entrada por columna: (etiqueta, alineación) o
               (etiqueta, alineación, formato).
                 alineación : 'l' izquierda, 'c' centro, 'r' derecha
                 formato    : ver `_formateador_columna`; por omisión 'texto'
               Las etiquetas pueden traer LaTeX (p. ej. '$\\kappa$').
    filas    : lista de filas, cada una con los valores CRUDOS de la medición
               (números o texto); el formato de su columna los convierte. Una
               celda que valga None se dibuja como '—' (no aplica), para la
               fila de referencia que no tiene error que medir.
    titulo   : markdown que va ENCIMA de la tabla (opcional).
    pie      : markdown que va DEBAJO de la tabla (opcional).
    mostrar  : True (por omisión) imprime la tabla y no devuelve nada; con False
               no imprime y devuelve el texto de Markdown (para pegarla en otro
               sitio, o para comprobarla desde una prueba).

    Devuelve
    --------
    None si la imprimió, o el texto de Markdown si pediste `mostrar=False`.

    Ejemplo
    -------
        tabla_experimento(
            [('Grado', 'c', 'entero'), ('$\\kappa$', 'c', 'num2'),
             ('Error rel.', 'c', 'ciencia2')],
            [[n, condicion_evaluacion(a, x), error_relativo(v, ex)] for ...],
            titulo='### Error medido contra el valor exacto')
    """
    if not columnas:
        raise ValueError('Una tabla necesita al menos una columna.')

    etiquetas, alineaciones, formatos = [], [], []
    for columna in columnas:
        columna = tuple(columna)
        etiqueta, alineacion = columna[0], columna[1]
        formato = columna[2] if len(columna) > 2 else 'texto'
        if alineacion not in _ALINEACIONES:
            raise ValueError("Alineación %r desconocida: usa 'l', 'c' o 'r'."
                             % (alineacion,))
        etiquetas.append(str(etiqueta))
        alineaciones.append(_ALINEACIONES[alineacion])
        formatos.append(_formateador_columna(formato))

    try:
        filas = [list(fila) for fila in filas]
    except TypeError:
        # Se pasó un valor suelto en lugar de una fila (por ejemplo [1, 2, 3]
        # en vez de [[1, 2, 3]]): el error de Python hablaría de iteradores y no
        # del problema real, que es un nivel de corchetes que falta.
        raise ValueError(
            'Cada fila tiene que ser una lista de celdas y llegó algo que no se '
            'puede recorrer. ¿Faltó un nivel de corchetes alrededor de las filas?')
    for i, fila in enumerate(filas):
        if len(fila) != len(columnas):
            raise ValueError(
                'La fila %d trae %d celdas y la tabla tiene %d columnas.'
                % (i, len(fila), len(columnas)))

    lineas = ['| ' + ' | '.join(etiquetas) + ' |',
              '|' + '|'.join(alineaciones) + '|']
    for fila in filas:
        celdas = ['—' if valor is None else formato(valor)
                  for formato, valor in zip(formatos, fila)]
        lineas.append('| ' + ' | '.join(celdas) + ' |')

    texto = '\n\n'.join(p for p in (titulo, '\n'.join(lineas), pie) if p)
    if mostrar:
        _display(_markdown(texto))
        return None
    return texto


# =====================================================================
#  Gráficas
# =====================================================================
def _horner(a, x):
    """
    P(x) con la forma anidada, para una x escalar o un arreglo de puntos.

    Es la misma recurrencia de la tarea, sin el cociente: aquí solo hace falta
    el valor. Con un arreglo funciona igual, porque las operaciones se aplican
    a todos los puntos a la vez.
    """
    y = 0.0
    for c in a:
        y = y * x + c
    return y


def _raices_reales(raices, x_min=None, x_max=None):
    """Las raíces con parte imaginaria despreciable, dentro del rango pedido."""
    salida = []
    for z in raices or ():
        z = complex(z)
        if abs(z.imag) > 1e-9 * max(1.0, abs(z)):
            continue
        if x_min is not None and not (x_min <= z.real <= x_max):
            continue
        salida.append(z.real)
    return salida


def graficar_polinomio(a, x0=None, raices=None, rango=None, titulo=None,
                       mostrar=True):
    """
    Dibuja P(x) y, si se los das, marca el punto de evaluación y las raíces.

    Parámetros
    ----------
    a      : coeficientes de MAYOR a menor grado (los mismos que los de Horner)
    x0     : punto donde se evaluó el polinomio (se marca con un círculo)
    raices : iterable de raíces; se marcan sobre el eje las que son reales
    rango  : (x_min, x_max); si no se da, se deduce de x0 y de las raíces
    titulo : título de la gráfica
    mostrar: True (por omisión) la dibuja y no devuelve nada; con False no la
             dibuja y devuelve la figura (para combinarla con otras gráficas)

    Devuelve
    --------
    None si la dibujó, o la figura de matplotlib si pediste `mostrar=False`.
    """
    if not a:
        raise ValueError('El polinomio necesita al menos un coeficiente.')

    plt = _plt()
    fig, ax = plt.subplots()

    centros = [complex(z).real for z in (raices or ())]
    if x0 is not None:
        centros.append(float(x0))
    if rango is not None:
        x_min, x_max = float(rango[0]), float(rango[1])
    elif centros:
        abajo, arriba = min(centros), max(centros)
        margen = max(1.0, 0.5 * (arriba - abajo))
        x_min, x_max = abajo - margen, arriba + margen
    else:
        x_min, x_max = -3.0, 3.0

    xs = np.linspace(x_min, x_max, 400)
    ys = _horner(a, xs)
    ax.plot(xs, ys, lw=1.8, label='$P(x)$')

    # La ventana vertical sale de los valores que toma la curva en el rango
    # elegido, con un poco de aire. El 0 se incluye siempre: sin él no se ve
    # dónde cambia de signo. (Recortar por percentiles no sirve: para un
    # polinomio muestreado de forma uniforme los percentiles siguen a los
    # extremos, así que lo único que haría es comerse la punta de la curva.)
    # Si la ventana automática no te sirve —raíces muy separadas, por
    # ejemplo—, pásale `rango=(a, b)`.
    finitos = np.asarray(ys)[np.isfinite(np.asarray(ys))]
    if finitos.size:
        abajo, arriba = float(finitos.min()), float(finitos.max())
        if arriba == abajo:          # P constante: es una franja, no una curva
            abajo, arriba = abajo - 1.0, arriba + 1.0
        relleno = 0.1 * (arriba - abajo)
        ax.set_ylim(min(abajo - relleno, 0.0), max(arriba + relleno, 0.0))

    ax.axhline(0.0, color='0.7', lw=0.8)

    if x0 is not None:
        ax.axvline(float(x0), color='C3', ls='--', lw=0.8, alpha=0.4)
        ax.plot([float(x0)], [_horner(a, float(x0))], 'o', color='C3', ms=7,
                label='$x_0$')

    reales = _raices_reales(raices, x_min, x_max)
    if reales:
        ax.plot(reales, [_horner(a, r) for r in reales], 'x', color='C2', ms=9,
                mew=2, label='raíces')

    ax.set_title(titulo or 'Polinomio de grado %d' % (len(a) - 1))
    ax.set_xlabel('$x$')
    ax.set_ylabel('$P(x)$')
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    if mostrar:
        plt.show()
        return None
    return fig


def graficar_errores(x, series, etiqueta_x='$n$', etiqueta_y='error relativo',
                     titulo=None, escala_log=True, mostrar=True):
    """
    Dibuja varias curvas de error contra la misma variable (grados, iteraciones).

    Parámetros
    ----------
    x      : valores del eje horizontal, uno por medición
    series : diccionario nombre -> lista de errores, o lista de pares
             (nombre, lista). Todas las listas miden lo mismo que x.
    mostrar: True (por omisión) la dibuja y no devuelve nada; con False no la
             dibuja y devuelve la figura

    Ojo con la escala logarítmica: un error de CERO no se puede dibujar (no hay
    logaritmo de cero), así que esos puntos se quedan fuera de la curva. Si te
    interesan, dibuja con `escala_log=False` o míralos en la tabla.

    Devuelve
    --------
    None si la dibujó, o la figura de matplotlib si pediste `mostrar=False`.
    """
    plt = _plt()
    if isinstance(series, dict):
        series = list(series.items())

    fig, ax = plt.subplots()
    for nombre, valores in series:
        if len(valores) != len(x):
            raise ValueError(
                'La serie %r trae %d valores y el eje horizontal tiene %d.'
                % (nombre, len(valores), len(x)))
        ax.plot(x, valores, marker='o', ms=4, label=str(nombre))

    if escala_log:
        ax.set_yscale('log')
    ax.set_xlabel(etiqueta_x)
    ax.set_ylabel(etiqueta_y)
    if titulo:
        ax.set_title(titulo)
    ax.grid(alpha=0.3, which='both')
    ax.legend()
    fig.tight_layout()
    if mostrar:
        plt.show()
        return None
    return fig
