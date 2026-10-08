# -*- coding: utf-8 -*-
"""
profe/ui/widgets.py — Interfaz visual gráfica e interactiva para Google Colab.

Es una ALTERNATIVA a las celdas con `pregunta(n)`: despliega todas las
preguntas de una vez con un botón de envío. No forma parte del bundle
ofuscado (el cuaderno no la usa), así que sirve para probar variantes.

    from profe.ui.widgets import InterfazTarea
    InterfazTarea(MI_TAREA).mostrar()
"""
import sys

import ipywidgets as widgets
from IPython.display import HTML, Markdown, display


class InterfazTarea(object):
    """Despliega la tarea interactiva en el Notebook de Google Colab."""

    def __init__(self, tarea, marco_evaluacion=None):
        self.tarea = tarea
        self.marco = marco_evaluacion or sys._getframe(1)
        self.controles = {}
        self.out_feedback = widgets.Output()

    def mostrar(self):
        """Renderiza todas las preguntas y el botón de envío."""
        print("=" * 70)
        print(" 📝 %s" % self.tarea.nombre_tarea)
        print(" 👤 Alumno: %s | NC: %s" % (self.tarea.alumno_id, self.tarea.nc))
        print("=" * 70 + "\n")

        componentes = [self._crear_pregunta_widget(idx, p)
                       for idx, p in enumerate(self.tarea.preguntas, 1)]

        btn_enviar = widgets.Button(
            description="🚀 Calificar y Enviar Tarea",
            button_style="success",
            icon="paper-plane",
            layout=widgets.Layout(width="280px", height="45px", margin="20px 0px 10px 0px"),
        )
        btn_enviar.on_click(self._on_click_enviar)

        display(widgets.VBox(componentes))
        display(btn_enviar)
        display(self.out_feedback)

    def _crear_pregunta_widget(self, idx, p):
        """Construye la tarjeta visual para una pregunta específica."""
        tipo = p['tipo']
        lbl_titulo = widgets.HTML(value="<b>Pregunta %d: %s</b>" % (idx, p['titulo']))
        lbl_texto = widgets.Output()
        with lbl_texto:
            display(Markdown(p['texto']))

        if tipo == 'opcion':
            control = widgets.RadioButtons(options=p['opciones'], index=None,
                                           layout=widgets.Layout(width="100%"))
        elif tipo == 'simple':
            control = widgets.Text(placeholder="Escribe tu respuesta numérica aquí...",
                                   layout=widgets.Layout(width="300px"))
        elif tipo == 'vector':
            etiquetas = p.get('etiquetas') or []
            control = widgets.VBox([
                widgets.FloatText(value=0.0, description='%s =' % etq,
                                  layout=widgets.Layout(width="230px"))
                for etq in etiquetas])
        elif tipo == 'funcion':
            control = widgets.HTML(
                value="<i>💡 Esta pregunta evalúa la función <code>%s</code> que "
                      "programaste en tu código.</i>" % p['funcion'])
        else:
            control = widgets.Label(value="Tipo de pregunta no soportado.")

        self.controles[idx] = (tipo, control)
        return widgets.VBox(
            [lbl_titulo, lbl_texto, control],
            layout=widgets.Layout(border="1px solid #d0d0d0", padding="12px",
                                  margin="0px 0px 15px 0px", border_radius="8px",
                                  background_color="#fdfdfd"))

    def _recopilar_respuestas(self):
        """Extrae los valores ingresados por el alumno en la interfaz."""
        respuestas = {}
        for idx, (tipo, ctrl) in self.controles.items():
            if tipo == 'opcion':
                val = ctrl.value
                if val is not None:
                    if isinstance(val, (int, float)):
                        respuestas[idx] = float(val)
                    else:
                        respuestas[idx] = float(ord(str(val).strip().lower()[0]) - 97)
            elif tipo == 'simple':
                val = ctrl.value.strip()
                if val:
                    try:
                        respuestas[idx] = float(val)
                    except ValueError:
                        respuestas[idx] = val
            elif tipo == 'vector':
                respuestas[idx] = [c.value for c in ctrl.children]
            elif tipo == 'funcion':
                respuestas[idx] = "EVALUAR_CODIGO"
        return respuestas

    def _on_click_enviar(self, boton):
        """Manejador de evento al presionar el botón de Calificar."""
        self.out_feedback.clear_output()
        with self.out_feedback:
            respuestas = self._recopilar_respuestas()
            filas_res = self.tarea.calificar(respuestas, self.marco)

            puntos = sum(f['puntos'] for f in filas_res)
            maximo = sum(f['peso'] for f in filas_res)
            calif = (puntos / maximo * 100.0) if maximo > 0 else 0.0

            html = ["<table style='width:100%; border-collapse: collapse;'>",
                    "<thead><tr style='background:#f2f2f2; text-align:left;'>"
                    "<th style='padding:8px;border:1px solid #ddd;'>#</th>"
                    "<th style='padding:8px;border:1px solid #ddd;'>Estado</th>"
                    "<th style='padding:8px;border:1px solid #ddd;'>Puntos</th>"
                    "<th style='padding:8px;border:1px solid #ddd;'>Detalle</th>"
                    "</tr></thead><tbody>"]
            for f in filas_res:
                color = {"correcta": "#28a745", "parcial": "#ffc107"}.get(
                    f['estado'], "#dc3545")
                html.append(
                    "<tr><td style='padding:8px;border:1px solid #ddd;'><b>%d</b></td>"
                    "<td style='padding:8px;border:1px solid #ddd;'>"
                    "<span style='color:white;background:%s;padding:3px 8px;"
                    "border-radius:4px;font-weight:bold;'>%s</span></td>"
                    "<td style='padding:8px;border:1px solid #ddd;'>%.1f / %.1f</td>"
                    "<td style='padding:8px;border:1px solid #ddd;'>%s</td></tr>"
                    % (f['i'], color, f['estado'].upper(), f['puntos'], f['peso'],
                       f['val']))
            html.append("</tbody></table><h3>Calificación final: "
                        "<span style='color:#0056b3;'>%.1f / 100</span></h3>" % calif)
            display(HTML("".join(html)))

            print("\nEnviando calificación a la hoja de registro oficial...")
            res = self.tarea.enviar(respuestas, self.marco)
            if res.get('motivo') == 'minimo':
                print('⛔ Aún no puedes enviar: necesitas al menos %g %% (%g puntos de %g).'
                      % (res['minimo'], self.tarea.min_aprobacion * res['maximo'],
                         res['maximo']))
            elif res['enviado']:
                print('✅ Enviado. Respuesta del servidor: %s' % res['respuesta'][:300])
            else:
                print('⚠️ No se pudo enviar: %s' % res.get('error'))
