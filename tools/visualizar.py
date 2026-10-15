# -*- coding: utf-8 -*-
"""
tools/visualizar.py — herramienta de visualización: tablas y gráficas.

Esto NO es parte del motor de calificación. Son utilidades para PRESENTAR los
resultados de un experimento numérico, y están a la vista a propósito: las
puedes leer, copiar y usar en tus propios cuadernos cuando quieras.

    latex_cientifico(valor)               cifra en notación científica de LaTeX
    tabla_experimento(columnas, filas)    tabla de Markdown a partir de los datos
    complejo_tex(z)                       un número complejo en LaTeX (sin los $)
    vector_tex(valores)                   una lista de números como vector de LaTeX
    bits_flotante(numero, precision)      los bits IEEE 754: signo, exponente y mantisa
    graficar_polinomio(a, x0, raices)     la curva de P(x) con sus marcas
    graficar_errores(x, series)           varias curvas de error contra la misma x
    camino_muller(f, x0, x1, x2)          los puntos por los que pasa Müller
    explorar_muller(f, x0, x1, x2)        el deslizador para recorrer las iteraciones
    graficar_paso_muller(f, x0, x1, x2, coef, x3)  la función, la parábola y x3
    graficar_plano_complejo(raices, camino)        raíces y recorrido en el plano complejo
    graficar_polinomio_complejo(a, raices, camino) la superficie |P(z)|: cada raíz es un valle
    animar_muller(f, x0, x1, x2, a)     la misma superficie, paso a paso y animada

Dos de ellas tienen versión INTERACTIVA: la figura se puede girar, acercar y
leer con el ratón (el valor de un punto sale al pasarle el cursor por encima).
Son `graficar_polinomio_complejo(..., interactivo=True)` y `animar_muller`, y
necesitan plotly.

El cuaderno del curso la carga solo, en la celda de configuración
(`from visualizar import ...`), así que basta con llamarlas. No dependen del
motor: si copias este archivo a otro cuaderno, las funciones siguen
funcionando igual (necesitan numpy, y matplotlib o plotly para las gráficas).

Todas siguen la misma regla, y es a propósito:

    mostrar=True  (por omisión)   saca la tabla o la figura y no devuelve nada
    mostrar=False                 no saca nada y devuelve el texto o la figura

Así una celda que termina en `tabla_experimento(...)` muestra SOLO la tabla. Si
la función devolviera el texto, el cuaderno lo imprimiría ADEMÁS como resultado
de la celda, en texto plano y con sus `|` y sus `\\n` a la vista.
"""
import cmath
import struct

import numpy as np

__all__ = ['animar_muller', 'bits_flotante', 'camino_muller', 'complejo_tex',
           'explorar_muller', 'graficar_errores', 'graficar_paso_muller',
           'graficar_plano_complejo', 'graficar_polinomio',
           'graficar_polinomio_complejo', 'latex_cientifico',
           'tabla_experimento', 'vector_tex']


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


def _plotly():
    """`plotly.graph_objects`, importado solo cuando se va a graficar."""
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise ImportError(
            'Las gráficas interactivas (girar la vista, leer los valores con '
            'el ratón) necesitan plotly. Se instala con:  pip install plotly'
        ) from exc
    return go


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


def _lista(valor):
    """
    Un iterable seguro para recorrer, venga como lista, tupla o arreglo.

    No se puede usar `valor or ()`: con un arreglo de numpy, `bool(arreglo)`
    revienta con «The truth value of an array ... is ambiguous». Y las raíces
    suelen venir de `numpy.roots`, que devuelve un arreglo.
    """
    return () if valor is None else valor


def _re_im(interesantes, re=None, im=None):
    """
    El rectángulo del plano complejo que hay que mirar.

    Si le pasas `re` y `im` los respeta; si no, los deduce con holgura de los
    números que le des en `interesantes` (raíces y recorrido). Comparten esto
    la versión de matplotlib y la de plotly para que las dos ventanas
    coincidan.
    """
    if re is not None and im is not None:
        return re, im
    if interesantes:
        xs = [z.real for z in interesantes]
        ys = [z.imag for z in interesantes]
        mx = max(1.0, 0.7 * (max(xs) - min(xs)))
        my = max(1.0, 0.7 * (max(ys) - min(ys)))
        return (min(xs) - mx, max(xs) + mx), (min(ys) - my, max(ys) + my)
    return (-4.0, 4.0), (-4.0, 4.0)


def _malla_compleja(a, re, im, n):
    """
    La malla del paisaje `log10(1 + |P(z)|)` sobre el rectángulo `re` x `im`.

    El logaritmo es a propósito: sin él las paredes de los costados tapan los
    valles. En las raíces vale cero igual. Devuelve (eje_x, eje_y, X, Y, Z),
    donde X, Y son la retícula (la necesita la figura de matplotlib y la de
    plotly no, porque plotly acepta los ejes sueltos). La usan las dos
    versiones, la de matplotlib y la de plotly.
    """
    ejex = np.linspace(float(re[0]), float(re[1]), int(n))
    ejey = np.linspace(float(im[0]), float(im[1]), int(n))
    X, Y = np.meshgrid(ejex, ejey)
    Z = np.log10(1.0 + np.abs(_horner(a, X + 1j * Y)))
    return ejex, ejey, X, Y, Z


def _raices_reales(raices, x_min=None, x_max=None):
    """Las raíces con parte imaginaria despreciable, dentro del rango pedido."""
    salida = []
    for z in _lista(raices):
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
    if a is None or len(a) == 0:
        raise ValueError('El polinomio necesita al menos un coeficiente.')

    plt = _plt()
    fig, ax = plt.subplots()

    centros = [complex(z).real for z in _lista(raices)]
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


# =====================================================================
#  Müller: el paso, el recorrido y el plano complejo
# =====================================================================
def _pasos_muller(f, x0, x1, x2, iteraciones):
    """
    Los fotogramas de Müller, uno por iteración.

    Cada fotograma es un diccionario con los tres puntos de ESA iteración, los
    coeficientes de la parábola que pasa por ellos y el x3 donde corta:

        x0, x1, x2   los tres puntos (complejos)
        a, b, c      coeficientes de a(x-x2)^2 + b(x-x2) + c
        x3           la aproximación siguiente
        real         True si los cuatro números caben en el eje real

    Se detiene antes de tiempo si llega a la raíz (así no repite fotogramas).
    """
    pasos = []
    p0, p1, p2 = complex(x0), complex(x1), complex(x2)
    for _ in range(int(iteraciones)):
        f0, f1, f2 = complex(f(p0)), complex(f(p1)), complex(f(p2))
        h0, h1 = p1 - p0, p2 - p1
        if h0 == 0 or h1 == 0:
            break
        a = ((f2 - f1) / h1 - (f1 - f0) / h0) / (h1 + h0)
        b = a * h1 + (f2 - f1) / h1
        disc = cmath.sqrt(b * b - 4.0 * a * f2)
        den = b + disc if abs(b + disc) > abs(b - disc) else b - disc
        if den == 0:                     # parábola degenerada: no hay paso
            break
        x3 = p2 - 2.0 * f2 / den
        pasos.append({
            'x0': p0, 'x1': p1, 'x2': p2, 'a': a, 'b': b, 'c': f2, 'x3': x3,
            'real': all(abs(z.imag) <= 1e-12 * max(1.0, abs(z.real))
                        for z in (p0, p1, p2, x3)),
        })
        if abs(x3 - p2) <= 1e-13 * max(1.0, abs(x3)):
            break                        # ya está en la raíz
        p0, p1, p2 = p1, p2, x3
    return pasos


def _pasos_utiles(f, x0, x1, x2, iteraciones):
    """
    Los fotogramas de Müller, sin los últimos que ya no mueven el punto.

    Müller converge tan rápido que, en cuanto llega a la raíz, repite el mismo
    número: esos fotogramas de más no enseñan nada y hacen que el deslizador y
    la animación parezcan atascados al final. Los quita.
    """
    pasos = _pasos_muller(f, x0, x1, x2, iteraciones)
    if not pasos:
        raise ValueError('No se pudo dar ni un paso con esos tres puntos.')
    while len(pasos) > 1 and (abs(pasos[-1]['x3'] - pasos[-1]['x2'])
                              <= 1e-9 * max(1.0, abs(pasos[-1]['x3']))):
        pasos.pop()
    return pasos


def camino_muller(f, x0, x1, x2, iteraciones=8):
    """
    Los puntos por los que pasa Müller: [x0, x1, x2, x3, x4, ...].

    Aunque arranques con tres números reales, los siguientes se salen del eje
    en cuanto la parábola deja de cruzarlo, así que devuelve una lista de
    números COMPLEJOS. Es el dato que necesitan `graficar_plano_complejo` y
    `graficar_polinomio_complejo` para dibujar el recorrido.

    Devuelve la lista de puntos; si el método converge antes, la lista es más
    corta de lo pedido (no repite el último punto).
    """
    return ([complex(x0), complex(x1), complex(x2)]
            + [p['x3'] for p in _pasos_muller(f, x0, x1, x2, iteraciones)])


def explorar_muller(f, x0, x1, x2, iteraciones=6, rango=None, titulo=None,
                    mostrar=True):
    """
    Un deslizador para recorrer las iteraciones, fotograma a fotograma.

    Muestra lo que ninguna figura fija enseña: que en cada paso la parábola se
    reajusta, que $x_3$ es donde corta, y que DESPUÉS los tres puntos se
    desplazan (el $x_0$ se olvida y el $x_3$ recién calculado pasa a ser el
    nuevo $x_2$). Ese relevo es el `x0, x1, x2 = x1, x2, x3` que hay que
    programar.

    Mientras los iterados son reales se dibuja el plano real (la parábola, los
    tres puntos y el corte). En cuanto uno se sale del eje, el panel cambia al
    plano complejo y muestra el recorrido: una parábola con coeficientes
    complejos ya no se puede dibujar sobre el eje real.

    Parámetros
    ----------
    f, x0, x1, x2 : la función y los tres puntos iniciales
    iteraciones   : cuántos fotogramas calcular como máximo
    rango         : (x_min, x_max) horizontal; si no se da, se deduce
    titulo        : título de cada fotograma
    mostrar       : True (por omisión) saca el control y no devuelve nada; con
                    False devuelve el control, para incrustarlo en otra celda

    Devuelve
    --------
    None si lo mostró, o el control de ipywidgets si pediste `mostrar=False`.
    """
    import ipywidgets as widgets

    pasos = _pasos_utiles(f, x0, x1, x2, iteraciones)

    if rango is None:
        reales = [z.real for p in pasos
                  for z in (p['x0'], p['x1'], p['x2'], p['x3'])
                  if abs(z.imag) <= 1e-9 * max(1.0, abs(z))]
        if reales:
            abajo, arriba = min(reales), max(reales)
            margen = max(0.5, 0.5 * (arriba - abajo))
            rango = (abajo - margen, arriba + margen)

    salida = widgets.Output()
    deslizador = widgets.IntSlider(value=1, min=1, max=len(pasos), step=1,
                                   description='iteración',
                                   continuous_update=False)

    def dibuja(k):
        paso = pasos[int(k) - 1]
        with salida:
            salida.clear_output(wait=True)
            _display(_markdown(
                '**Iteración %d de %d** — la parábola se ajusta por '
                '$x_0 = %s$, $x_1 = %s$, $x_2 = %s$ y corta en '
                '$x_3 = %s$.'
                % (k, len(pasos), complejo_tex(paso['x0']),
                   complejo_tex(paso['x1']), complejo_tex(paso['x2']),
                   complejo_tex(paso['x3']))))
            if paso['real']:
                graficar_paso_muller(f, paso['x0'].real, paso['x1'].real,
                                     paso['x2'].real,
                                     (paso['a'].real, paso['b'].real,
                                      paso['c'].real),
                                     x3=paso['x3'].real, rango=rango,
                                     titulo=titulo)
                if int(k) < len(pasos):
                    _display(_markdown('En el fotograma siguiente el relevo '
                                       'es $x_0 \\leftarrow x_1$, '
                                       '$x_1 \\leftarrow x_2$ y '
                                       '$x_2 \\leftarrow x_3$.'))
            else:
                graficar_plano_complejo(
                    camino=[p['x3'] for p in pasos[:int(k)]],
                    titulo='El recorrido, ya en el plano complejo')
                _display(_markdown('A partir de aquí los puntos se salen del '
                                   'eje real: la parábola ya no lo corta, y '
                                   'el recorrido sigue en el plano '
                                   'complejo.'))

    def al_cambiar(cambio):
        if cambio['name'] == 'value':
            dibuja(cambio['new'])

    deslizador.observe(al_cambiar, names='value')
    control = widgets.VBox([deslizador, salida])
    dibuja(1)
    if mostrar:
        _display(control)
        return None
    return control


def complejo_tex(z, dec=6):
    """
    Un número real o complejo en LaTeX, sin los `$`.

    Es el formateador que usan los laboratorios para escribir los pasos a mano:
    los números de Müller y Bairstow son complejos (y con parte imaginaria casi
    nula, como el $-1 - 3\times10^{-9}i$ de una raíz doble) y un `%g` a secas
    no sabe escribirlos.

        2.222222 - 1.082982i   ->   2.222222 -1.082982\,i
    """
    z = complex(z)
    if abs(z.imag) <= 1e-12 * max(1.0, abs(z.real)):
        return '%.*g' % (dec, z.real)
    return '%.*g %+.*g\\,i' % (dec, z.real, dec, z.imag)


def vector_tex(valores, dec=6):
    """
    Una lista de números como vector de LaTeX, sin los `$`.

        [1.5, -2]   ->   \\left[1.5,\ -2\\right]

    Bairstow lo usa para enseñar los $b_k$ y los $c_k$ de las dos divisiones.
    """
    return (r'\left[%s\right]'
            % r',\ '.join(complejo_tex(v, dec) for v in valores))


def _complejo_txt(z, dec=6):
    """
    Un número real o complejo en texto plano.

    Es el hermano pobre de `_complejo_tex` para las gráficas de plotly: en sus
    etiquetas no entra el LaTeX (solo `&lt;b&gt;`, `&lt;sub&gt;`, `&lt;br&gt;`, ...), así que
    los números van tal cual, que es justo lo que se quiere leer con el ratón.
    """
    z = complex(z)
    if abs(z.imag) <= 1e-12 * max(1.0, abs(z.real)):
        return '%.*g' % (dec, z.real)
    return '%.*g %s %.*gi' % (dec, z.real, '+' if z.imag >= 0 else '-',
                              dec, abs(z.imag))


def graficar_paso_muller(f, x0, x1, x2, coef, x3=None, rango=None,
                         titulo=None, mostrar=True):
    """
    Dibuja un paso de Müller: la función, la parábola que ajusta y x3.

    Parámetros
    ----------
    f          : la función, evaluada sobre el eje real
    x0, x1, x2 : los tres puntos iniciales
    coef       : (a, b, c) de la parábola a(x-x2)^2 + b(x-x2) + c
    x3         : la aproximación siguiente. Si es real se marca sobre el eje;
                 si es compleja se avisa en una nota, porque verla requiere
                 salirse del plano real (`graficar_plano_complejo`)
    mostrar    : True (por omisión) la dibuja y no devuelve nada; con False no
                 la dibuja y devuelve la figura

    Devuelve
    --------
    None si la dibujó, o la figura de matplotlib si pediste `mostrar=False`.
    """
    plt = _plt()
    fig, ax = plt.subplots()

    a, b, c = (float(v) for v in coef)
    x0, x1, x2 = float(x0), float(x1), float(x2)
    if rango is not None:
        x_min, x_max = float(rango[0]), float(rango[1])
    else:
        abajo, arriba = min(x0, x1, x2), max(x0, x1, x2)
        margen = max(0.5, 0.6 * (arriba - abajo))
        x_min, x_max = abajo - margen, arriba + margen

    xs = np.linspace(x_min, x_max, 400)
    ax.plot(xs, [float(f(v)) for v in xs], lw=1.8, label='$f(x)$')
    ax.plot(xs, a * (xs - x2) ** 2 + b * (xs - x2) + c, lw=1.8, ls='--',
            label='parábola de Müller')
    ax.axhline(0.0, color='0.7', lw=0.8)

    ax.plot([x0, x1, x2], [f(x0), f(x1), f(x2)], 'o', color='C3', ms=7,
            label='los tres puntos')
    for etiqueta, valor in (('$x_0$', x0), ('$x_1$', x1), ('$x_2$', x2)):
        ax.annotate(etiqueta, (valor, f(valor)), textcoords='offset points',
                    xytext=(7, 6), color='C3')

    if x3 is not None:
        z = complex(x3)
        if abs(z.imag) <= 1e-12 * max(1.0, abs(z.real)):
            ax.axvline(z.real, color='C2', ls=':', lw=1.0, alpha=0.7)
            ax.plot([z.real], [0.0], 'v', color='C2', ms=10,
                    label='$x_3 = %s$' % complejo_tex(z))
        else:
            ax.annotate('$x_3 = %s$: se sale del plano real'
                        % complejo_tex(z), xy=(0.03, 0.93),
                        xycoords='axes fraction', color='C2')

    ax.set_title(titulo or 'Un paso de Müller')
    ax.set_xlabel('$x$')
    ax.set_ylabel('$f(x)$')
    ax.grid(alpha=0.3)
    ax.legend(loc='best')
    fig.tight_layout()
    if mostrar:
        plt.show()
        return None
    return fig


def graficar_plano_complejo(raices=(), camino=(), titulo=None, mostrar=True):
    """
    El plano complejo: las raíces y el recorrido de Müller.

    Es la vista que muestra lo que un método puramente real no puede hacer: en
    cuanto la parábola deja de cruzar el eje real, los puntos se salen de la
    recta y el recorrido baja hacia una raíz compleja.

    Parámetros
    ----------
    raices : iterable de raíces; se marcan con una ×
    camino : los puntos de Müller, como los devuelve `camino_muller`
    mostrar: True (por omisión) la dibuja y no devuelve nada; con False no la
             dibuja y devuelve la figura

    Devuelve
    --------
    None si la dibujó, o la figura de matplotlib si pediste `mostrar=False`.
    """
    plt = _plt()
    fig, ax = plt.subplots()

    ax.axhline(0.0, color='0.6', lw=1.0)
    ax.axvline(0.0, color='0.6', lw=1.0)

    puntos = [complex(z) for z in _lista(camino)]
    if puntos:
        xs = [z.real for z in puntos]
        ys = [z.imag for z in puntos]
        ax.plot(xs, ys, '-o', color='C0', ms=5, lw=1.2, label='iteraciones')
        for i, z in enumerate(puntos[:3]):
            ax.annotate('$x_%d$' % i, (z.real, z.imag),
                        textcoords='offset points', xytext=(8, 5), color='C0')
        if len(puntos) > 3:
            ax.plot([xs[-1]], [ys[-1]], '*', color='C0', ms=14)
            ax.annotate('converge', (xs[-1], ys[-1]),
                        textcoords='offset points', xytext=(11, -13),
                        color='C0')

    reales = [complex(z) for z in _lista(raices)]
    if reales:
        ax.plot([z.real for z in reales], [z.imag for z in reales], 'x',
                color='C2', ms=11, mew=2.4, label='raíces')

    ax.margins(0.14)                 # aire para que no se corten las etiquetas

    ax.set_title(titulo or 'El plano complejo')
    ax.set_xlabel('$\\mathrm{Re}(z)$')
    ax.set_ylabel('$\\mathrm{Im}(z)$')
    ax.grid(alpha=0.3)
    if reales or puntos:
        ax.legend(loc='best')
    fig.tight_layout()
    if mostrar:
        plt.show()
        return None
    return fig


def graficar_polinomio_complejo(a, raices=(), camino=(), re=None, im=None,
                                n=70, titulo=None, letra='P',
                                interactivo=False, mostrar=True):
    """
    La superficie |P(z)| sobre el plano complejo: cada raíz es un valle.

    Para un polinomio de coeficientes reales, dibujar |P(z)| sobre z = x + iy
    muestra POR QUÉ Müller alcanza raíces complejas: la superficie baja hasta
    cero en cada raíz, y las complejas aparecen como dos valles simétricos
    fuera del eje real. Un método que solo mira el eje (o la recta que une dos
    puntos del eje) nunca los pisa; la parábola de Müller, al no tener que
    cruzarlo, sí.

    Parámetros
    ----------
    a      : coeficientes de MAYOR a menor grado
    raices : para marcarlas en el suelo del plano
    camino : los puntos de Müller (`camino_muller`); se dibuja su proyección
    re, im : (mínimo, máximo) del plano complejo. Por omisión se deduce de las
             raíces y del recorrido
    n      : puntos de la malla por lado (n x n). Más puntos, más lento
    letra  : con qué letra se llama al polinomio en los ejes ('P' por omisión).
             En el laboratorio de Müller la función del enunciado es `f`, así
             que ahí se pide `letra='f'` y el eje dice lo mismo que el título
    interactivo : True para que la figura sea de plotly, que se puede GIRAR,
             ACERCAR y leer con el ratón (el valor de un punto sale al pasarle
             el cursor por encima, y en la leyenda se puede apagar el paisaje
             para ver el recorrido a solas); False (por omisión) para la de
             matplotlib, que es una imagen fija pero más ligera
    mostrar: True (por omisión) la dibuja y no devuelve nada; con False no la
             dibuja y devuelve la figura

    La altura es `log10(1 + |P(z)|)` y no |P| a secas: sin el logaritmo las
    paredes de los costados tapan los valles. En las raíces vale cero igual.

    Devuelve
    --------
    None si la dibujó, o la figura (de matplotlib, o de plotly si pediste
    `interactivo=True`) si pediste `mostrar=False`.
    """
    if a is None or len(a) == 0:
        raise ValueError('El polinomio necesita al menos un coeficiente.')

    raices = [complex(z) for z in _lista(raices)]
    camino = [complex(z) for z in _lista(camino)]
    re, im = _re_im(raices + camino, re, im)
    ejex, ejey, X, Y, Z = _malla_compleja(a, re, im, n)

    def altura(z):
        """A qué altura se dibuja el punto z: sobre el paisaje mismo."""
        return float(np.log10(1.0 + abs(complex(_horner(a, complex(z))))))

    if interactivo:
        fig = _paisaje_plotly(ejex, ejey, Z, raices, camino, altura, titulo,
                              letra)
        if mostrar:
            fig.show()
            return None
        return fig

    plt = _plt()
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(projection='3d')
    ax.plot_surface(X, Y, Z, cmap='viridis', linewidth=0, antialiased=True,
                    alpha=0.9)
    ax.contour(X, Y, Z, levels=14, zdir='z', offset=0.0, cmap='viridis')

    if raices:
        ax.scatter([z.real for z in raices], [z.imag for z in raices],
                   [0.0] * len(raices), marker='x', s=90, color='C2',
                   label='raíces', depthshade=False)
    if camino:
        ax.plot([z.real for z in camino], [z.imag for z in camino],
                [0.0] * len(camino), '-o', color='C3', ms=4,
                label='recorrido de Müller')

    ax.set_xlabel('$\\mathrm{Re}(z)$')
    ax.set_ylabel('$\\mathrm{Im}(z)$')
    ax.set_zlabel('$\\log_{10}(1 + |%s(z)|)$' % letra)
    ax.set_title(titulo or 'El paisaje de un polinomio en el plano complejo')
    ax.view_init(elev=38, azim=-58)
    if raices or camino:
        ax.legend(loc='upper left')
    fig.tight_layout()
    if mostrar:
        plt.show()
        return None
    return fig


# =====================================================================
#  Las mismas gráficas, pero interactivas (plotly)
# =====================================================================
#  Una figura de plotly no es una imagen: se gira con el ratón, se acerca con
#  la rueda y dice el valor de cada punto con solo pasarle el cursor por
#  encima. Se usa donde el giro aporta algo (el paisaje |P(z)|, que se mira
#  desde varios lados) y donde el método da varios pasos que hay que ver
#  DESPUÉS del que se está mirando (la animación de Müller).


def _etiqueta_altura(letra='P'):
    """
    El nombre del eje de las alturas: `log10(1 + |X(z)|)`.

    Lleva la letra del polinomio a propósito, porque en el cuaderno se usan
    dos: en el laboratorio de Bairstow el polinomio es $P$, y en el de Müller (y
    en su animación) la función del enunciado se llama $f$. Por debajo son el
    mismo polinomio, pero para el alumno son dos nombres distintos: el eje no
    puede llamarse de una forma mientras el título lo hace de otra.
    """
    return 'log<sub>10</sub>(1 + |%s(z)|)' % letra


def _escenario_plotly(fig, titulo, etiqueta_altura):
    """
    El escenario 3D que comparten las figuras de plotly: ejes, cámara y aire.

    Las proporciones van a mano (`aspectratio`) en vez de `cube`: el eje de las
    alturas recorre un rango mucho más corto que el plano complejo, y con la
    caja cúbica los valles saldrían estirados de más. La cámara arranca en el
    mismo punto de vista que la figura de matplotlib.
    """
    fig.update_layout(
        title=dict(text=titulo, x=0.5),
        scene=dict(
            xaxis_title='Re(z)',
            yaxis_title='Im(z)',
            zaxis_title=etiqueta_altura,
            aspectmode='manual',
            aspectratio=dict(x=1.4, y=1.4, z=0.6),
            camera=dict(eye=dict(x=1.55, y=-1.75, z=0.95)),
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.0, x=0.0),
        margin=dict(l=0, r=0, t=70, b=0),
    )
    return fig


def _traza_paisaje(ejex, ejey, Z, letra='P'):
    """La superficie `log10(1 + |P(z)|)`, con sus curvas de nivel en el suelo."""
    go = _plotly()
    altura = _etiqueta_altura(letra)
    return go.Surface(
        x=ejex, y=ejey, z=Z, colorscale='Viridis', showscale=False,
        opacity=0.96, name='paisaje |%s(z)|' % letra,
        # Las superficies NO entran en la leyenda por su cuenta (en plotly ese
        # `showlegend` viene apagado): se pone a mano para que se pueda pulsar
        # su nombre y apagarla, y quedarse mirando solo el recorrido.
        showlegend=True,
        contours={'z': {'show': True, 'usecolormap': True,
                        'project': {'z': True}}},
        hovertemplate=('Re(z) = %{x:.3f}<br>Im(z) = %{y:.3f}<br>'
                       + altura + ' = %{z:.3f}<extra></extra>'),
    )


def _traza_raices(raices):
    """Las raíces, marcadas en el fondo del valle (altura 0)."""
    go = _plotly()
    return go.Scatter3d(
        x=[z.real for z in raices], y=[z.imag for z in raices],
        z=[0.0] * len(raices),
        mode='markers+text', text=[_complejo_txt(z) for z in raices],
        textposition='bottom center',
        textfont=dict(color='seagreen', size=12),
        marker=dict(symbol='x', size=7, color='seagreen',
                    line=dict(width=1, color='white')),
        name='raíces',
        customdata=[[_complejo_txt(z)] for z in raices],
        hovertemplate=('raíz<br>z = %{customdata[0]}<br>'
                       '|P(z)| = 0<extra></extra>'),
    )


def _traza_recorrido(puntos, altura):
    """El recorrido de Müller, SUBIENDO por el paisaje: baja al valle."""
    go = _plotly()
    return go.Scatter3d(
        x=[z.real for z in puntos], y=[z.imag for z in puntos],
        z=[altura(z) for z in puntos],
        mode='lines+markers',
        line=dict(color='crimson', width=4),
        marker=dict(size=3, color='crimson'),
        name='recorrido',
        customdata=[[_complejo_txt(z)] for z in puntos],
        hovertemplate=('recorrido<br>z = %{customdata[0]}<br>'
                       'log<sub>10</sub>(1 + |f(z)|) = %{z:.4g}'
                       '<extra></extra>'),
    )


def _traza_puntos(puntos, etiquetas, altura, color, tamano, nombre):
    """Los puntos de un fotograma (los tres de la parábola, o el x3)."""
    go = _plotly()
    return go.Scatter3d(
        x=[z.real for z in puntos], y=[z.imag for z in puntos],
        z=[altura(z) for z in puntos],
        mode='markers+text', text=list(etiquetas),
        textposition='top center',
        textfont=dict(color=color, size=13),
        marker=dict(size=tamano, color=color,
                    line=dict(width=1, color='white')),
        name=nombre,
        customdata=[[_complejo_txt(z)] for z in puntos],
        hovertemplate=('<b>%{text}</b><br>z = %{customdata[0]}<br>'
                       'log<sub>10</sub>(1 + |f(z)|) = %{z:.4g}'
                       '<extra></extra>'),
    )


def _paisaje_plotly(ejex, ejey, Z, raices, camino, altura, titulo=None,
                    letra='P'):
    """
    La figura 3D de plotly: el paisaje, las raíces y el recorrido.

    La usan las dos funciones interactivas. La de la animación la deja sin
    recorrido (le pasa `camino=()`) porque allí el recorrido lo van dibujando
    los fotogramas, y le añade las trazas y los controles después.
    """
    go = _plotly()
    fig = go.Figure()
    if Z is not None:
        fig.add_trace(_traza_paisaje(ejex, ejey, Z, letra))
    if raices:
        fig.add_trace(_traza_raices(raices))
    if camino:
        fig.add_trace(_traza_recorrido(list(camino), altura))
    return _escenario_plotly(
        fig, titulo or 'El paisaje de un polinomio en el plano complejo',
        _etiqueta_altura(letra))


def animar_muller(f, x0, x1, x2, a=None, raices=(), iteraciones=8, n=60,
                  re=None, im=None, pausa=1200, titulo=None, mostrar=True):
    """
    La animación de Müller: gira la vista, lee los valores y dale a reproducir.

    Es la versión interactiva de `explorar_muller`. Muestra lo mismo —que en
    cada paso la parábola se reajusta, que `x3` es donde corta y que DESPUÉS
    los tres puntos se desplazan—, pero la figura trae sus propios controles
    (reproducir, pausa y la barra de iteraciones) y se puede girar y acercar
    con el ratón; pasando el cursor por encima de un punto sale su valor
    exacto.

    Los puntos van SOBRE el paisaje `log10(1 + |f(z)|)` (si le das los
    coeficientes en `a`), así que se ve lo que el método hace: caminar hacia
    el valle. En cada fotograma la parábola se reajusta por los tres puntos de
    ese momento y `x3` es donde corta.

    Una pega que conviene saber antes de enseñarla: en un cuaderno la figura se
    dibuja al ejecutar la celda y sus controles funcionan sin volver a
    ejecutarla, pero NO se puede imprimir.

    Parámetros
    ----------
    f, x0, x1, x2 : la función y los tres puntos iniciales
    a             : coeficientes del polinomio, de MAYOR a menor grado, para
                    dibujar el paisaje. Sin ellos la animación sale sin
                    superficie, sobre el plano z = 0 (el complejo), y sigue
                    sirviendo: lo que se mira es el recorrido
    raices        : las raíces, para marcarlas
    iteraciones   : cuántos fotogramas calcular como máximo
    n             : puntos de la malla del paisaje por lado
    re, im        : (mínimo, máximo) del plano complejo; se deducen solos
    pausa         : milisegundos que dura cada fotograma al reproducir
    titulo        : título de la figura
    mostrar       : True (por omisión) la saca y no devuelve nada; con False
                    devuelve la figura de plotly

    Devuelve
    --------
    None si la mostró, o la figura de plotly si pediste `mostrar=False`.
    """
    go = _plotly()
    pasos = _pasos_utiles(f, x0, x1, x2, iteraciones)
    raices = [complex(z) for z in _lista(raices)]

    def altura(z):
        """A qué altura se dibuja el punto z: log10(1 + |f(z)|)."""
        return float(np.log10(1.0 + abs(complex(f(complex(z))))))

    if a is not None and len(a) > 0:
        # El paisaje se dibuja con los coeficientes `a` y la altura de los
        # puntos se mide con `f`: si no son el mismo polinomio, los puntos
        # salen flotando fuera de la superficie y no se entiende nada. Se
        # comprueba en un par de puntos antes de dibujar (es más barato que
        # darse cuenta mirando la figura).
        for _z in (0.7, 1.9):
            _p = _horner(a, _z)
            if abs(_p - complex(f(_z))) > 1e-6 * max(1.0, abs(_p)):
                raise ValueError(
                    'El paisaje (a = %r) no es el polinomio de `f`: los puntos '
                    'saldrían fuera de la superficie. Pásale en `a` los '
                    'coeficientes de la f del enunciado, o deja `a` vacío para '
                    'que no se dibuje el paisaje.' % (a,))
        re, im = _re_im(raices + [p['x3'] for p in pasos], re, im)
        ejex, ejey, _X, _Y, Z = _malla_compleja(a, re, im, n)
    else:
        ejex = ejey = Z = None

    # Las trazas fijas (el paisaje y las raíces), y a partir de ahí las tres
    # que cambian de fotograma en fotograma. Los índices de esas tres se
    # calculan solos: si la figura lleva paisaje y raíces son 2, 3 y 4, y si
    # no lleva nada son 0, 1 y 2.
    fig = _paisaje_plotly(ejex, ejey, Z, raices, camino=(), altura=altura,
                          titulo=titulo, letra='f')
    base = len(fig.data)

    camino = [complex(x0), complex(x1), complex(x2)]
    datos = []
    for paso in pasos:
        camino.append(complex(paso['x3']))
        datos.append([
            _traza_recorrido(list(camino), altura),
            _traza_puntos((paso['x0'], paso['x1'], paso['x2']),
                          ('x<sub>0</sub>', 'x<sub>1</sub>', 'x<sub>2</sub>'),
                          altura, 'royalblue', 6, 'los tres puntos'),
            _traza_puntos((paso['x3'],), ('x<sub>3</sub>',), altura,
                          'crimson', 8, 'x<sub>3</sub>'),
        ])

    fig.add_traces(datos[0])          # el fotograma que se ve al ejecutar
    fig.frames = [go.Frame(name=str(k), data=trazas,
                           traces=[base, base + 1, base + 2])
                  for k, trazas in enumerate(datos, start=1)]

    cuadro = dict(frame=dict(duration=int(pausa), redraw=True),
                  fromcurrent=True, transition=dict(duration=0))
    pasos_barra = [dict(method='animate', label=str(k),
                        args=[[str(k)], dict(mode='immediate',
                                             frame=dict(duration=0,
                                                        redraw=True),
                                             transition=dict(duration=0))])
                   for k in range(1, len(datos) + 1)]
    fig.update_layout(
        updatemenus=[dict(
            type='buttons', showactive=False, direction='left',
            x=0.0, y=1.05, xanchor='left', yanchor='bottom',
            buttons=[
                dict(label='▶  reproducir', method='animate',
                     args=[None, cuadro]),
                dict(label='⏸  pausa', method='animate',
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode='immediate',
                                        transition=dict(duration=0))]),
            ])],
        sliders=[dict(active=0, currentvalue=dict(prefix='iteración '),
                      x=0.0, len=1.0, pad=dict(t=1),
                      steps=pasos_barra)],
        margin=dict(l=0, r=0, t=100, b=0),
    )
    if mostrar:
        fig.show()
        return None
    return fig
