---
id: muller_vibraciones
titulo: "Vibraciones: frecuencia natural con el método de Müller"
incognita: "omega"
unidad: "rad/s"
mano: true
rangos:
  c: [8, 14, 0]
  x0: [3.2, 3.6, 1]
  x1: [4.4, 4.8, 1]
  x2: [3.8, 4.2, 1]
---

La frecuencia de resonancia de un chasis robótico satisface la función no
lineal

$$f(\omega) = {polinomio} = 0$$

donde $\omega$ es la frecuencia angular en rad/s.

Utiliza el **método de Müller** con los tres puntos iniciales
$\omega_0 = {x0}$, $\omega_1 = {x1}$ y $\omega_2 = {x2}$ para estimar la
**primera aproximación** $\omega_3$: ajusta la parábola que pasa por esos tres
puntos y toma su raíz más cercana a $\omega_2$.
