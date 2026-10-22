# 1. Preguntas de gestión y alcance del tablero

1. ¿En qué momentos del año llegan más y menos visitantes, y cómo ha cambiado eso con los años?

   Esta pregunta ayuda a anticipar temporadas altas y bajas, ajustar recursos y comparar si el patrón de visitas se mantiene o está cambiando.

2. ¿De qué países o regiones vienen los visitantes y cómo ha variado su peso a lo largo del tiempo?

   Permite identificar los mercados de origen más importantes y detectar cambios que orienten la promoción turística y la atención a distintos públicos.

3. ¿Qué tan llena está la capacidad de hospedaje en cada temporada?

   Sirve para saber cuándo la oferta de alojamiento está cerca de su límite o tiene capacidad disponible, facilitando decisiones sobre operación y promoción.

4. ¿Qué meses concentran tanta afluencia que podrían generar presión sobre el destino?

   Ayuda a reconocer periodos en los que conviene reforzar servicios, movilidad y manejo del destino para reducir posibles impactos por saturación.

5. ¿Cuántos visitantes se esperan en los próximos meses y con qué margen de error?

   Ofrece una referencia para preparar personal, presupuesto y servicios, dejando claro el nivel de incertidumbre de la estimación.

6. ¿Qué tan confiable es cada modelo de predicción y en qué casos conviene tomar la estimación con cautela?

   Permite comparar los modelos y elegir sus resultados con criterio, especialmente cuando el desempeño indique que una predicción debe interpretarse con prudencia.

El tablero incluye:

- Exploración de llegadas de visitantes, origen, ocupación de hospedaje y estacionalidad.
- Predicción de llegadas mensuales con tres modelos simples reutilizados de los laboratorios anteriores.
- Comparación del desempeño de esos modelos.
- Textos explicativos pensados para directivos sin formación estadística.

El tablero no incluye:

- Modelos nuevos ni reentrenamiento de modelos.
- Datos en tiempo real.
- Explicaciones de causas que los datos no permiten establecer.
- Datos individuales de personas.

# 2. Herramienta

El tablero se desarrollará en Python con Plotly Dash y dash-bootstrap-components para el diseño. Plotly Dash permite enlazar las gráficas de forma nativa mediante callbacks que responden a clics y selecciones, una capacidad necesaria para que una visualización actualice a otra.

Los gráficos de Plotly ya ofrecen zoom, selección, tooltips y control del nivel de detalle. Además, los modelos de los laboratorios anteriores están desarrollados en Python con scikit-learn, por lo que se pueden reutilizar sin convertirlos ni trasladarlos a otro entorno.

Esta combinación es de código abierto y permite controlar el diseño del tablero, incluidos los colores, las fuentes y la distribución de los elementos. Para mantener ese control y facilitar los gráficos enlazados, se descartó Streamlit, ya que vuelve a ejecutar todo el script con cada interacción y ofrece un enlace más limitado entre gráficas. También se descartó R Shiny porque obligaría a trasladar los modelos a otro lenguaje.
