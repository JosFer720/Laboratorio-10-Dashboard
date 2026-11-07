# Informe en Power BI

## Versión de Power BI Desktop

La última versión de Desktop documentada para el archivo recibido es `2.159.1231.0 (64 bits)` en Windows. Los cambios de predicciones, controles y navegación se incorporaron después mediante los archivos PBIR, conservando el modelo importado. Esta última edición todavía no se abrió ni guardó en Desktop; la revisión de ejecución debe completarse allí.

## Resultados comprobados en Desktop

La actualización terminó correctamente el 5 de noviembre de 2026. Se cargaron las ocho tablas y se conservaron las siete relaciones del modelo. Las consultas de `comprobaciones.dax` dieron estos resultados:

- total histórico: `46,711,912.89`, mostrado como `46,711,913`;
- máximo histórico: diciembre de 2019, con `449,114.07`, mostrado como `449,114`;
- observado de diciembre de 2025: `365573.0218067979`, mostrado como `365,573.02`, sin variar al seleccionar uno o todos los modelos.

El informe tiene seis páginas: Inicio, Llegadas y mercados, Temporadas y hospedaje, Predicciones y modelos, Sobre los datos y una página de detalle de región a países que no aparece entre los botones. Las cinco primeras se recorren con los botones del encabezado. El diseño previsto está en [bosquejo.png](../docs/lab12/bosquejo.png).

La definición actual contiene las ocho visualizaciones. Se recuperó la matriz V3, que había sido reemplazada por la dispersión V6. El `.pbix` y los archivos de `observatorio_turismo.Report/` contienen el mismo informe; el modelo importado mantiene exactamente el mismo SHA-256 que la versión recibida. La revisión y sus límites están en [revision_informe.md](../docs/lab12/revision_informe.md).

La página **Temporadas y hospedaje** presenta dos vistas complementarias y mantiene el estilo visual del informe:

- **Ocupación hotelera por mes**: gráfico de columnas con `Calendario[month_name]` y la medida `Ocupación hotelera` en formato porcentual.
- **Llegadas vs. ocupación hotelera (2022–2024)**: gráfico de dispersión con la ocupación en el eje X, `Llegadas` en el eje Y y `Calendario[year_month]` como detalle. La cobertura queda limitada a los años disponibles en Hospedaje y la relación se interpreta únicamente de forma descriptiva, sin afirmar causalidad.

La tasa agregada se calcula a partir de habitaciones, no sumando porcentajes publicados:

```DAX
Ocupación hotelera =
DIVIDE(
    SUM(Hospedaje[rooms_occupied]),
    SUM(Hospedaje[rooms_available])
)
```

La página **Llegadas y mercados** también tiene gráficos pequeños, uno por región, con el peso de cada región en las llegadas de cada año. Usan la medida `Peso de la región` de la tabla `Calendario`:

```DAX
Peso de la región = DIVIDE([Llegadas], CALCULATE([Llegadas], REMOVEFILTERS(Origenes)))
```

Con clic derecho sobre una región y Obtener detalles se llega a la página de detalle con sus mercados.

La página **Llegadas y mercados** incluye una línea temporal con la jerarquía año > trimestre > mes y barras por mercado de origen. La selección de un período en la primera visualización filtra la segunda. Ambas usan la medida:

```DAX
Llegadas = SUM(Llegadas[arrivals])
```

## Predicciones y modelos

V7 compara el observado nacional en azul continuo con el estimado del modelo elegido en naranja discontinuo. El selector empieza en LSTM catch22 y solo afecta V7. Si se limpia o se selecciona más de un modelo, no se suman estimaciones de modelos diferentes y aparece la indicación de elegir uno.

V8 muestra `estimado − observado` por mes en tres paneles, uno por modelo, con barras naranjas y la misma escala. Una barra negativa indica subestimación. La selección de un mes de V7 filtra V8. La tabla mantiene MAE, RMSE y MAPE de los tres modelos sobre los mismos 63 meses de abril de 2021 a junio de 2026. El filtro temporal no recalcula esas métricas históricas. La etiqueta de evaluación histórica, no pronóstico, aparece en la página.

Las medidas específicas del informe están en `observatorio_turismo.Report/definition/reportExtensions.json`; las referencias de los visuales usan el esquema `extension`. `Observado histórico` suma `Observados[observed]`, con una fila por mes; nunca se usa la suma del observado repetido en Predicciones. Las fórmulas, las equivalencias con Dash y el tratamiento de filtros se describen en [predicciones_y_navegacion.md](../docs/lab12/predicciones_y_navegacion.md).

## Filtros y navegación

Los cinco botones del encabezado enlazan las páginas principales y resaltan en azul la página activa. El detalle de región se abre con clic derecho desde los mercados o los paneles de regiones y tiene un botón Volver. En Desktop, los botones se activan con Ctrl + clic.

Los segmentadores de años y meses se sincronizan entre las tres páginas de análisis. Mercado se sincroniza entre Llegadas y mercados y Temporadas y hospedaje; solo afecta llegadas, porque hospedaje y predicciones son nacionales. Cada página muestra una tarjeta con los filtros activos. Las páginas de análisis agregan mensajes para selecciones sin datos.

Restablecer vista aplica un marcador que limpia años, meses, mercados y selecciones entre gráficos, recupera el detalle anual de V1 y deja LSTM como modelo inicial. Mantiene la página actual; desde el detalle vuelve a Llegadas y mercados. La página Sobre los datos reúne las fuentes, el glosario y las limitaciones.

## Abrir el informe

Abre primero `observatorio_turismo.pbix` en Windows. Conserva los datos importados y la definición actual del informe. Si necesitas actualizar las fuentes, cambia `pCarpetaDatos` como se indica abajo y pulsa Actualizar.

Para comprobar esta edición, recorre las seis páginas, ejecuta `comprobaciones_finales.dax` en la vista de consultas DAX y prueba los enlaces V1 → V2, V3 → V5 y V7 → V8, el detalle de región con regreso, los filtros sincronizados y Restablecer vista. Incluye una selección de 2025 en hospedaje para comprobar el mensaje sin datos. Guarda en Desktop y registra cualquier diferencia. Las pruebas comparativas completas siguen [protocolo_pruebas.md](../docs/lab12/protocolo_pruebas.md).

La alternativa editable es `observatorio_turismo.pbip`, con el modelo en `observatorio_turismo.SemanticModel/model.bim` y el informe completo en `observatorio_turismo.Report/`. Para preparar una copia con la ruta de datos de otro equipo:

En Windows, desde la raíz del repositorio:

```powershell
python scripts/preparar_powerbi.py
```

El comando verifica las cuatro fuentes y crea una copia en `powerbi/local/`, ignorada por Git, con la ruta de datos de ese equipo. Solo necesita Python y Git. Se detiene si la carpeta ya existe para conservar cualquier edición. Para otra copia usa `--output powerbi/local-otra`; las carpetas alternativas deben quedar fuera del repositorio o excluirse de Git.

1. Instala [Power BI Desktop](https://learn.microsoft.com/es-es/power-bi/fundamentals/desktop-get-the-desktop) en Windows desde Microsoft Store o el sitio de Microsoft. Es gratuito.
2. Abre `powerbi/local/observatorio_turismo.pbip`. Si Desktop pide habilitar las opciones de proyecto o formato de informe mejorado, actívalas en Opciones > Características de versión preliminar y reinicia.
3. Pulsa **Actualizar** y espera a que se carguen todas las tablas. No continúes si aparece un error de carga.
4. En la vista de modelo, revisa las siete relaciones y la jerarquía de `Calendario`. La descripción y las filas esperadas están en [modelo_de_datos.md](../docs/lab12/modelo_de_datos.md).
5. Ejecuta `powerbi/comprobaciones.dax` en la vista de consultas DAX. Revisa los totales, los conteos y el observado con uno y con todos los modelos.
6. Comprueba el tema en Vista > Temas y la disponibilidad de Inter o Segoe UI en el equipo. El recurso incrustado coincide con `tema_observatorio.json`.
7. Guarda como `powerbi/observatorio_turismo.pbix`. El proyecto editable sirve para preparar el modelo; el archivo de intercambio del informe sigue siendo el `.pbix`.

Si el `.pbix` ya existe, ábrelo directamente. No vuelvas a generar el proyecto sobre un informe que ya tenga cambios.

## Carpeta de los datos

Los CSV que usa el informe están en la carpeta `data/` del repositorio y coinciden byte por byte con el commit `29a091d`, señalado por `lab10-final`:

- `arrivals_migration_2009_2026.csv`
- `hotel_occupancy_inguat_2022_2024.csv`
- `model_predictions_s0.csv`
- `model_metrics_s0.csv`

Todas las lecturas usan el único parámetro de Power Query `pCarpetaDatos`. Para cambiarlo en un proyecto o `.pbix` abierto: Transformar datos > Administrar parámetros > `pCarpetaDatos`, selecciona la carpeta `data`, aplica y actualiza. El proyecto en Git deja ese parámetro vacío para evitar rutas personales. También puedes preparar una copia con `python scripts/preparar_powerbi.py --data-dir "C:\ruta\repositorio\data"`.

Para repetir la verificación de fuentes sin Desktop:

```powershell
python scripts/verificar_powerbi.py
```

Los resultados registrados están en [validacion_fuentes.json](../docs/lab12/validacion_fuentes.json). Esa verificación no ejecuta Power Query ni DAX y no sustituye la comprobación del `.pbix`.

La integridad del informe y su correspondencia con el `.pbix` se revisan sin dependencias adicionales con:

```powershell
python scripts/verificar_informe_powerbi.py
```

La auditoría opcional del modelo importado usa `pbixray==0.15.5`: después de instalarlo, ejecuta `python scripts/auditar_modelo_powerbi.py`. Comprueba las predicciones y llegadas almacenadas frente a los CSV y recalcula las métricas. Los resultados están en [validacion_modelos_pbix.json](../docs/lab12/validacion_modelos_pbix.json). Tampoco ejecuta las medidas nuevas ni renderiza los visuales.

## Tema

`tema_observatorio.json` contiene la paleta y las fuentes del tablero: azul `#0B5C8E` para lo observado, naranja `#D55E00` para lo estimado, gris `#8A939E` para el contexto y la escala de azules para cantidades. Se aplica en Power BI Desktop desde Vista > Temas > Buscar temas. Usa la fuente Inter si está instalada en el equipo y, si no, Segoe UI.

El proyecto incluye una copia idéntica en `observatorio_turismo.Report/StaticResources/RegisteredResources/`. Si cambia el tema, actualiza también ese recurso; el verificador detecta diferencias entre las dos copias.

## Formato del proyecto

Se usan los formatos documentados por Microsoft: [proyectos PBIP](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [modelo semántico en TMSL](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset) e [informe PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report). No se incluyen cachés ni configuraciones personales de `.pbi/`.
