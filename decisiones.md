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

# 3. Paleta de colores

La paleta parte de una idea: lo más importante que un directivo no debe confundir en este tablero es qué cifras ya ocurrieron y cuáles son estimaciones de un modelo. Por eso la pareja de colores con más contraste se reserva para esa diferencia. El azul marca lo observado y el naranja marca lo estimado. Son colores casi opuestos en el círculo cromático, así que se separan bien a simple vista, y la combinación azul con naranja es de las pocas que siguen distinguiéndose con los tipos más comunes de daltonismo, a diferencia de rojo con verde.

| Color | Código | Significado | Uso |
|---|---|---|---|
| Azul | #0B5C8E | Dato observado | Líneas continuas, barras y puntos con cifras publicadas por INGUAT. También es el color del elemento seleccionado en una gráfica. |
| Naranja | #D55E00 | Dato estimado | Líneas punteadas de las predicciones y errores de los modelos. |
| Naranja claro | #D55E00 al 20 % de opacidad | Margen de incertidumbre | Banda alrededor de la predicción que muestra el rango probable. |
| Naranja oscuro | #A84300 | Texto sobre estimaciones | Etiquetas y textos cortos que hablan de una estimación, porque el naranja normal no alcanza el contraste mínimo para texto. |
| Gris medio | #8A939E | Contexto | Barras o líneas que no están seleccionadas, para que el elemento elegido resalte sin perder el resto. |
| Escala de azules | #E8F1F8, #BBD5EA, #7FB0D6, #3F86BD, #0B5C8E, #0B3C5D | Cantidad observada, de menos a más | Gráficas donde el color representa cuántos visitantes hubo, por ejemplo una cuadrícula de meses por año. |
| Gris oscuro | #1F2933 | Texto principal | Títulos, cifras y texto explicativo. También las líneas de referencia, como un promedio. |
| Gris pizarra | #5B6573 | Texto secundario | Subtítulos, notas, fuente de los datos y etiquetas de ejes. |
| Gris claro | #E3E6EA | Rejilla y bordes | Líneas guía horizontales y separación entre tarjetas. |
| Blanco | #FFFFFF | Superficie | Fondo de las tarjetas donde van las gráficas. |
| Gris casi blanco | #F7F8FA | Fondo general | Fondo de la página, para que las tarjetas se vean como bloques separados. |

El resto de la paleta es neutra a propósito. Si cada gráfica tuviera sus propios colores, el lector tendría que aprender un código nuevo en cada una. Con pocos colores y muchos grises, el color solo aparece donde dice algo. Los mercados de origen y los tres modelos no reciben un color propio: se distinguen por su posición en la gráfica y por su nombre escrito al lado. Así el azul y el naranja nunca cambian de significado, y no hace falta un arcoíris de once países que sería imposible de leer.

Para la cantidad de visitantes se usa una escala secuencial de un solo tono de azul, del más claro al más oscuro. La claridad sube de forma pareja, así que el ojo lee más oscuro como más visitantes sin tener que consultar la leyenda, y la escala se entiende igual si se imprime en blanco y negro. El tono más claro no es blanco puro, para que una celda con pocos visitantes no se confunda con el fondo.

No se usa rojo ni verde para decir que algo está bien o mal. Más visitantes no siempre es bueno para un destino que busca ser sostenible, y el tablero no debe sugerir un juicio que los datos no dan. Cuando haga falta señalar un mes con muchas llegadas, se hará con una línea de referencia en gris oscuro y un texto que diga qué se compara.

Revisamos el contraste de cada color contra el fondo blanco con el criterio de accesibilidad WCAG. El texto principal llega a 14.8 a 1 y el secundario a 5.9 a 1, los dos por encima del 4.5 a 1 que se pide para leer texto. El azul observado llega a 7.2 a 1, así que sirve también para texto. El naranja estimado llega a 3.9 a 1, suficiente para líneas y marcas gráficas, que piden 3 a 1, pero no para texto; por eso existe la variante oscura #A84300, que llega a 6.1 a 1. El gris de contexto queda en 3.1 a 1, apenas por encima del mínimo para elementos gráficos, que es lo que buscamos para algo que debe verse pero quedar en segundo plano.

También simulamos cómo ven la paleta las personas con deuteranopía, protanopía y tritanopía. En los tres casos el azul y el naranja siguen muy separados, y los dos se distinguen del gris de contexto. Aun así, el color nunca es la única pista. Lo estimado siempre va en línea punteada, con su banda de incertidumbre y con la palabra "estimado" en la leyenda y en el recuadro que aparece al pasar el cursor. Lo observado va en línea continua. Si alguien imprime el tablero en grises o no distingue los colores, el tipo de línea y la etiqueta siguen diciendo lo mismo.

# 4. Fuentes

Todo el tablero usa una sola familia tipográfica, Inter. Usar una sola familia evita variaciones que no significan nada y deja que la jerarquía la marquen el tamaño y el grosor. Inter fue diseñada para leerse en pantalla: tiene letras con altura de minúscula grande, aberturas amplias y formas que no se confunden entre sí, como la l, la I y el 1. Además tiene números tabulares, es decir, todas las cifras ocupan el mismo ancho, lo que hace que los números de las tarjetas, las tablas y los ejes queden alineados y se puedan comparar de un vistazo. Es gratuita, de código abierto con licencia SIL Open Font License, y se puede descargar de Google Fonts.

| Elemento | Fuente y grosor | Tamaño |
|---|---|---|
| Título del tablero | Inter semibold | 26 px |
| Título de pestaña o sección | Inter semibold | 20 px |
| Título de cada gráfica | Inter semibold | 16 px |
| Cifras de las tarjetas | Inter semibold con números tabulares | 28 px |
| Texto explicativo y controles | Inter regular | 15 px |
| Ejes, leyendas y recuadros al pasar el cursor | Inter regular con números tabulares | 13 px |
| Notas, fuente de los datos y aclaraciones | Inter regular, gris pizarra | 12 px |

Ningún texto queda por debajo de 12 px, porque más pequeño cuesta leerlo en una laptop o en un proyector de sala de reuniones. El texto explicativo lleva un interlineado de 1.5 para que los párrafos cortos no se vean apretados.

Conviene guardar los archivos de Inter dentro de la carpeta de recursos de la aplicación en lugar de cargarlos desde internet, para que el tablero se vea igual aunque se abra sin conexión. Si por cualquier motivo Inter no carga, el respaldo es la fuente del sistema operativo, en este orden: system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial y sans-serif. Todas son tipografías sin remates pensadas para pantalla, así que el tablero se mantiene legible aunque cambie un poco su aspecto.

# 5. Bosquejo de la interfaz y navegación

El tablero se organiza en pestañas, una por cada grupo de preguntas de gestión, más una pestaña con la información de los datos. La idea es que el directivo entre por la pregunta que tiene en mente y no por el tipo de gráfica. Arriba de todo hay una barra fija con el título, el periodo que cubren los datos y los filtros globales, que se mantienen al cambiar de pestaña para no tener que volver a elegirlos.

```
+----------------------------------------------------------------------------------+
| Observatorio de turismo sostenible · Guatemala                                   |
| Llegadas de visitantes no residentes y ocupación hotelera, 2022 a 2024 · INGUAT  |
|                                                                                  |
| Periodo [2022 ===== 2024]  Mercado de origen [Todos v]  Detalle [Año|Trim|Mes]   |
+----------------------------------------------------------------------------------+
| Llegadas y mercados | Temporadas y hospedaje | Predicciones y modelos | Sobre los datos |
+----------------------------------------------------------------------------------+
|  [Tarjeta: llegadas del periodo] [Tarjeta: mes con más llegadas] [Tarjeta: ...]  |
|                                                                                  |
|  +---------------------------------------------+  +---------------------------+  |
|  | V1 Llegadas totales en el tiempo            |  | V2 Llegadas por mercado   |  |
|  | (clic o selección de un periodo) ---------->|  | de origen en el periodo   |  |
|  |                                             |  | elegido en V1             |  |
|  +---------------------------------------------+  +---------------------------+  |
|  +----------------------------------------------------------------------------+  |
|  | V4 Cómo cambia el peso de cada mercado de origen con los años              |  |
|  +----------------------------------------------------------------------------+  |
|  Mostrar gráficas: [x] V1 [x] V2 [x] V4                                          |
|  Nota: fuente, fecha y qué es observado o estimado                               |
+----------------------------------------------------------------------------------+
```

Las pestañas y lo que contiene cada una:

```
Llegadas y mercados ........ V1 y V2 (enlazadas), V4
Temporadas y hospedaje ..... V3, V5, V6
Predicciones y modelos ..... V7 y V8 (enlazadas), tabla comparativa de modelos
Sobre los datos ............ fuentes, glosario, alcance y limitaciones
```

Los filtros globales son tres. El periodo es un rango de fechas que recorta todas las gráficas de exploración. El mercado de origen permite elegir todos los mercados, una región o un país. Las regiones son América del Norte, América Central, América del Sur, Europa y resto del mundo, más los cruceristas, que INGUAT publica como un grupo aparte; dentro de América del Norte y América Central se puede bajar a países. El detalle temporal cambia la unidad de tiempo entre año, trimestre y mes. Cuando un filtro no aplica a una gráfica, aparece desactivado con una nota corta que dice por qué, para que nadie piense que está fallando. Pasa en la pestaña de predicciones y modelos, y también con la ocupación hotelera, porque INGUAT la publica para todo el país y sin separar por país de origen.

El nivel de detalle sube y baja de tres maneras. La primera es el control de detalle temporal, que pasa de años a trimestres y a meses. La segunda es hacer clic dentro de una gráfica: al elegir un año se ven sus meses, y al elegir una región se ven sus países. La tercera es una ruta de navegación encima de la gráfica, del tipo "Todos los mercados > América Central > El Salvador", que permite volver al nivel anterior con un clic. El zoom y el recuadro con el detalle al pasar el cursor que trae cada gráfica completan la exploración.

Cada pestaña tiene casillas para elegir qué gráficas mostrar, de modo que el directivo pueda quedarse solo con las que le sirven. Todas las gráficas llevan un título que dice qué muestran y en qué unidades, un texto corto que explica para qué le sirven a un directivo y una nota con la fuente. Cuando una selección deja una gráfica sin datos, en su lugar aparece un mensaje que lo explica y sugiere qué cambiar.

Estas son las ocho visualizaciones previstas, dónde van y qué pregunta de gestión responden. El tipo exacto de gráfica se decide al construir cada una:

| Visualización | Tema | Pestaña | Pregunta de gestión |
|---|---|---|---|
| V1 | Llegadas totales a lo largo del tiempo, con detalle por año, trimestre o mes | Llegadas y mercados | 1. En qué momentos llegan más y menos visitantes |
| V2 | Llegadas por mercado de origen en el periodo elegido en V1 | Llegadas y mercados | 2. De qué países o regiones vienen los visitantes |
| V3 | Estacionalidad: cada mes del año comparado entre 2022, 2023 y 2024 | Temporadas y hospedaje | 1. Cómo ha cambiado el patrón de temporadas con los años |
| V4 | Cambio del peso de cada mercado de origen con los años | Llegadas y mercados | 2. Cómo ha variado el peso de cada origen |
| V5 | Ocupación hotelera de cada mes | Temporadas y hospedaje | 3. Qué tan llena está la capacidad de hospedaje |
| V6 | Relación entre las llegadas de cada mes y la ocupación hotelera de ese mes | Temporadas y hospedaje | 4. Qué meses combinan mucha afluencia y hoteles llenos |
| V7 | Llegadas observadas y estimadas por el modelo elegido, con su margen de error | Predicciones y modelos | 5. Cuántos visitantes se esperan y con qué margen |
| V8 | Qué tan bien acierta el modelo elegido | Predicciones y modelos | 6. Qué tan confiable es cada modelo |

V1 y V2 son las del avance y quedan enlazadas: al elegir un periodo en V1, V2 muestra de dónde vinieron los visitantes en ese periodo. Si no hay ningún periodo elegido, V2 muestra el periodo completo del filtro global. V7 y V8 también se enlazan, porque el modelo que se elige en V7 es el que V8 evalúa. Además, al menos una de V3, V4 y V5 se enlazará con otra gráfica; la idea inicial es que al elegir un mes en V5 ese mes se resalte en V6. La tabla comparativa de los tres modelos va junto a V8 como apoyo y no cuenta como visualización.

Para las preguntas 3 y 4 se agregó una segunda fuente de INGUAT: los boletines anuales de ocupación hotelera de 2022, 2023 y 2024, que dan por mes las habitaciones disponibles, las habitaciones ocupadas y el índice de ocupación. Hay que tener presente que la ocupación cuenta a todos los huéspedes, residentes en Guatemala y extranjeros, mientras que las llegadas cuentan solo a visitantes no residentes. Por eso V6 muestra en qué meses coinciden muchas llegadas y hoteles llenos, pero el tablero no dice que unas causen lo otro.

# 6. Planificación de tareas y responsables

El trabajo se hace en cadena: cada quien empieza cuando el anterior terminó y dejó sus cambios en el repositorio, porque cada paso usa lo que deja el paso previo. Los estilos dependen de la paleta, la segunda gráfica se enlaza con la primera, y las gráficas de modelos necesitan que los resultados ya estén cargados. Así evitamos que dos personas toquen lo mismo al mismo tiempo. Además de su parte del tablero, cada responsable agrega al final de este documento la sección que describe lo que hizo.

| Orden | Entrega | Tarea | Responsable | Qué recibe del paso anterior |
|---|---|---|---|---|
| 1 | Avance | Paleta de colores, fuentes, bosquejo de la interfaz y navegación, y esta planificación | Joel Jaquez | Preguntas de gestión, alcance, herramienta y el proyecto base con los datos cargados |
| 2 | Avance | Archivo de estilos con la paleta y las fuentes, estructura de pestañas y filtros, y la visualización 1 con la selección del usuario disponible para otra gráfica | Nery Molina | Paleta, fuentes y bosquejo definidos |
| 3 | Avance | Visualización 2 enlazada con la 1, mensaje para selecciones sin datos, prueba del tablero desde cero e informe del avance en PDF | Kevin Villagran | Visualización 1 funcionando y su selección disponible |
| 4 | Final | Resultados de los tres modelos de los laboratorios anteriores, cargados en el tablero, y la visualización 7 con el selector de modelo | Fernando Ruiz | Tablero del avance con las visualizaciones 1 y 2 enlazadas |
| 5 | Final | Visualizaciones 3, 4 y 5 para explorar los datos, sus enlaces y la forma de aumentar y disminuir el nivel de detalle | Joel Jaquez | Resultados de los modelos cargados y visualización 7 funcionando |
| 6 | Final | Visualización 6, visualización 8 enlazada con el modelo elegido, tabla comparativa de modelos y selección de las gráficas que se quieren ver | Nery Molina | Visualizaciones 3, 4 y 5 con sus enlaces y niveles de detalle |
| 7 | Final | Textos explicativos, etiquetas de observado y estimado, mensajes sin datos, prueba completa del tablero e informe final en PDF | Kevin Villagran | Las ocho visualizaciones, la comparación de modelos y la selección de gráficas funcionando |

# 7. Visualización 1

La primera visualización muestra cómo cambian las llegadas de visitantes no residentes a Guatemala entre 2022 y 2024. Responde a la pregunta de en qué momentos llegan más y menos visitantes y cómo cambia ese patrón con los años. Elegimos una gráfica de líneas porque permite seguir la evolución del tiempo y reconocer temporadas con mayor o menor afluencia. Cada punto representa la suma de las categorías de origen disponibles para el periodo elegido.

El usuario puede elegir el mes inicial y final y filtrar todos los mercados, una región o un origen específico. Las opciones aclaran si se trata de un país, un agregado o el segmento de cruceristas. El control de detalle permite pasar entre meses, trimestres y años. Las sumas respetan el periodo del filtro: si solo se incluyen dos meses de un trimestre, el punto contiene esos dos meses. Al pasar el cursor se muestra el periodo, las llegadas observadas y la cantidad de meses con información. Las herramientas de la gráfica permiten ampliar y restaurar la vista sin cambiar los datos.

Para seleccionar un periodo se hace clic en un punto o se arrastra un recuadro sobre varios puntos. La selección se muestra debajo de la gráfica y puede limpiarse con el botón Limpiar selección. Al cambiar el periodo, el mercado o el detalle temporal, se descarta la selección anterior y se vuelve al periodo completo del filtro. Si se eligen meses no consecutivos, se conserva esa lista exacta, sin incluir los meses intermedios.

La gráfica tiene el identificador `arrivals-timeline`. Su selección queda disponible en el componente `v1-selection`, con los campos `dates`, `market`, `granularity` e `is_selected`. El primero contiene las fechas mensuales, el segundo identifica el mercado, el tercero guarda el detalle temporal y el último indica si hay puntos seleccionados. La función `apply_selection` permite recuperar esas filas del conjunto de datos ya cargado. Así queda preparado el enlace con la visualización 2, que mostrará los mercados de origen y todavía no está incorporada. Sin selección se comparten todos los meses del filtro; si no hay datos, se comparte una lista vacía.

La línea continua y los puntos azules representan las llegadas observadas. Los puntos fuera de una selección se muestran en gris para dar contexto. Se utiliza la fuente Inter y los tamaños definidos en las secciones anteriores; los archivos de la fuente y los estilos se sirven desde la aplicación. La gráfica incluye un texto que explica su utilidad para planificar recursos turísticos, una nota de fuente y un mensaje cuando el filtro no tiene información. Los meses ausentes interrumpen la línea y no se convierten en ceros. Las cifras originales se conservan, incluidas las diferencias de una unidad documentadas para algunos meses de 2024.
