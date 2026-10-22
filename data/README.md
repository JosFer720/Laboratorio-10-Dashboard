# Llegadas de visitantes no residentes a Guatemala

`arrivals_inguat_2022_2024.csv` contiene las llegadas mensuales de visitantes no residentes a Guatemala entre enero de 2022 y diciembre de 2024. Cada fila representa un mes y todos los valores son cantidades de visitantes.

## Fuente

La fuente es el Instituto Guatemalteco de Turismo (INGUAT), tabla “Visitantes no residentes por mes y país de residencia” de los boletines estadísticos anuales 2022, 2023 y 2024. La tabla de 2024 se contrastó también con el boletín del segundo semestre del mismo año para conservar la versión oficial más reciente.

El portal de INGUAT migró y sus antiguos identificadores de descarga dejaron de resolver correctamente. Los documentos se localizan en estas rutas institucionales vigentes:

- [Catálogo oficial de boletines estadísticos de turismo 1969–2025](https://biblioteca.inguat.gob.gt/opac/record/8002), donde se buscan los títulos “Boletín estadísticas de turismo anual 2022”, “Boletín estadísticas de turismo anual 2023” y “Boletín estadísticas de turismo anual 2024”.
- [Boletín anual 2024 en la biblioteca de INGUAT](https://biblioteca.inguat.gob.gt/library/images/2/2e/B-anual2024.pdf).
- [Índice institucional de información estadística](https://inguat.gob.gt/es/actualidad/uncategorised/estadisticas-2/), que describe la frecuencia y el contenido de los boletines.

Los boletines atribuyen los datos al Instituto Guatemalteco de Migración y a la Estimación de Flujos Terrestres del Departamento de Investigación y Análisis de Mercados de INGUAT.

## Transformación

- Los meses se normalizaron como fechas ISO (`YYYY-MM-01`).
- Canadá, Estados Unidos, México, Belice, El Salvador y Honduras se transcribieron de sus filas de país.
- `rest_of_central_america` conserva la categoría oficial `Resto de Centroamérica`, definida por INGUAT como el agregado de América del Centro excluyendo Belice, El Salvador y Honduras.
- América del Sur, Europa, Resto del Mundo y Cruceristas se conservaron como los agregados publicados.
- En la tabla de 2023 se excluyeron los subtotales trimestrales intercalados y se conservaron solamente los doce meses.
- No se imputaron, redondearon ni ajustaron valores para forzar igualdad con el total mensual.

## Columnas

| Columna | Descripción |
|---|---|
| `date` | Mes de observación. |
| `canada` | Residentes de Canadá. |
| `united_states` | Residentes de Estados Unidos. |
| `mexico` | Residentes de México. |
| `belize` | Residentes de Belice. |
| `el_salvador` | Residentes de El Salvador. |
| `honduras` | Residentes de Honduras. |
| `rest_of_central_america` | Resto de residentes de América Central. |
| `south_america` | Agregado de América del Sur. |
| `europe` | Agregado de Europa. |
| `rest_of_world` | Agregado del resto del mundo. |
| `cruise_passengers` | Cruceristas. |
| `reported_total` | Total mensual publicado por INGUAT; se incluye para auditoría. |

## Validación e inconsistencias de la fuente

Para cada mes se sumaron las once categorías y se compararon con `reported_total`. Los 24 meses de 2022 y 2023 coinciden exactamente. En 2024 coinciden nueve meses y la fuente presenta tres diferencias aritméticas de una unidad:

| Mes | Suma de categorías | Total publicado | Diferencia |
|---|---:|---:|---:|
| 2024-02 | 237,275 | 237,274 | +1 |
| 2024-04 | 238,085 | 238,084 | +1 |
| 2024-10 | 220,637 | 220,638 | -1 |

Estas diferencias se conservan deliberadamente para mantener fidelidad a los valores oficiales. `reported_total` permite auditarlas sin alterar ninguna categoría.
