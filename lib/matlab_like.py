"""matlab_like — precarga NumPy/Matplotlib/SciPy con sintaxis estilo MATLAB.

Se ejecuta con exec(..., globals()) en el notebook para que el alumno
escriba directamente, por ejemplo:

    x = linspace(0, 10, 100)
    plot(x, sin(x))
"""
from numpy import *
from numpy.linalg import *
import numpy as np
from matplotlib.pyplot import *
import matplotlib.pyplot as plt

try:
    from scipy.integrate import *
except ImportError:
    pass

# Configuración visual estilo MATLAB
np.set_printoptions(precision=4, suppress=True, linewidth=120)
plt.rcParams['figure.figsize'] = (8, 6)

# Alias cortos estilo MATLAB
lin = linspace
