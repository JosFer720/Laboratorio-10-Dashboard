# Alcance del flujo de estimación

Este documento define qué estima el pipeline, con qué datos, en qué períodos y con qué supuestos. La configuración está en `config/pipeline.yaml`.

## Qué se estima

- **Variable**: visitantes únicos del mes en cada subdestino.
- **Unidad de medida**: personas (visitantes únicos del mes).
- **Nivel de agregación**: subdestino por mes. Son 25 series, una por subdestino. Los visitantes únicos no se suman entre subdestinos ni entre meses, porque una misma persona puede aparecer en varios.
- **Alcance geográfico**: nivel nacional, con los seis destinos del observatorio.

| Hoja | Grupo (`sub_grupo`) | Subdestinos (`destino`) |
|---|---|---|
| Antigua | Antigua Guatemala | Antigua Guatemala, Jocotenango, Volcan Acatenango Fuego |
| Peten | Peten | El Remate Y Alrededores Lago, Isla De Flores, Mundo Maya Aeropuerto |
| Atitlan | Lago Atitlan | Panajachel, San Antonio Palopo, San Juan La Laguna, San Lucas Toliman, San Marcos La Laguna, San Pablo La Laguna, San Pedro La Laguna, Santa Catarina Palopo, Santa Cruz La Laguna, Santiago Atitlan |
| Izabal | Izabal | Livingston, Rio Dulce |
| Alta Verapaz | Coban | Coban, Cuevas De Candelaria, Lanquin |
| Playas Pacifico | Playas Del Pacifico | El Paredon, Las Lisas, Monterrico, Puerto De San Jose |

La base mensual de movilidad no trae una fila con el total de cada destino. Como sumar subdestinos duplicaría visitantes, el flujo trabaja siempre por subdestino y no construye totales por destino.

## Fuentes y columnas

Los archivos se leen de la carpeta que indica la variable de entorno `INGUAT_DATA_DIR`. Son datos institucionales confidenciales y no forman parte del repositorio.

### Movilidad mensual (`BD_moviidad_mensual.xlsx`)

Una hoja por destino, en formato largo. Cada fila es un subdestino, un mes, un país de residencia y un segmento de permanencia.

| Columna | Descripción |
|---|---|
| `destino` | Subdestino (polígono). |
| `sub_grupo` | Grupo al que pertenece el subdestino. |
| `anio`, `mes` | Año y mes numéricos. |
| `pais` | País de residencia del visitante. |
| `es_consecutivo` | Segmento: `mayor a 1 dia` o `menor a 1 dia`. |
| `fecha` | Primer día del mes. |
| `visitantes` | Visitantes únicos del mes. |
| `dias_persona` | Días-persona del mes. |
| `permanencia_prom` | Permanencia promedio; no se promedia, se recalcula como días-persona entre visitantes. |

Cobertura: septiembre a diciembre de 2025 y marzo a agosto de 2026. Entre los dos bloques no hay datos: enero y febrero de 2026 no tienen cobertura.

### Flujo migratorio (`Base_Migracion_2009-2026jun.xlsx`, hoja `Datos`)

Entradas de viajeros internacionales a Guatemala en formato largo. Columnas: `Año`, `Mes cod`, `Mes`, `Vía`, `Frontera`, `País`, `Región`, `Región dos`, `Regiones OMT`, `MCEO`, `Agrupación Residencia`, `Tipo de Viajero` y `Viajero` (la cantidad).

- Cobertura: enero de 2009 a junio de 2026, sin meses faltantes. La base termina en junio, así que julio y agosto de 2026 no tienen entradas nacionales.
- Las entradas nacionales de un mes son la suma de `Viajero` de los tipos `Turista` y `Excursionista`. El tipo `Viajero` no cuenta como visitante.
- Desde 2023 la fuente cambia de metodología y de granularidad de país. Los niveles no son comparables con 2022 hacia atrás, por lo que el pipeline usa solo años desde 2023 (`parameters.migration.first_year`).
- Las cantidades tienen decimales porque son estimaciones expandidas de encuesta.

## Períodos

| Período | Meses | Uso |
|---|---|---|
| Cobertura de movilidad | 2025-09 a 2025-12 y 2026-03 a 2026-08 | Meses con movilidad observada. |
| Cobertura de migración | 2009-01 a 2026-06 | Meses con entradas nacionales. |
| Ajuste | 2025-09 a 2025-12 y 2026-03 a 2026-06 | Meses con ambas fuentes: sirven para calcular el factor de reparto. |
| Evaluación | 2026-03 a 2026-06 | Meses que se ocultan y se estiman como si no estuvieran disponibles. Cada mes se estima solo con los meses de ajuste anteriores a él. |
| Estimación | 2026-01 y 2026-02 | Meses sin cobertura de movilidad que se estiman. |

Julio y agosto de 2026 tienen movilidad observada pero no entradas nacionales, por lo que no entran al factor de reparto. Los errores de la estimación solo se calculan en meses con valor observado comparable; para enero y febrero de 2026 no hay observaciones y no se calcula ningún error.

## Parámetros y supuestos

- **Factor de reparto**: para cada subdestino y mes de ajuste, el cociente entre sus visitantes y las entradas nacionales del mismo mes. El factor del subdestino es el promedio de esos cocientes mensuales (`mean_of_monthly_ratios`). No se suman visitantes de varios meses.
- **Estimación**: visitantes estimados del subdestino en un mes sin cobertura = factor de reparto del subdestino por entradas nacionales de ese mes. La forma estacional la aporta la serie nacional de entradas.
- **Semilla**: `parameters.seed`. El procedimiento descrito no tiene componentes aleatorios; la semilla se fija para cualquier etapa que los agregue y para los datos sintéticos.
- **Versión del procedimiento**: `parameters.procedure_version`.
- Los visitantes de movilidad y las entradas nacionales miden universos distintos (presencia en un polígono frente a entradas al país), por lo que el factor es un cociente de referencia y no una proporción de un total.

## Archivo de resultados

El pipeline escribe un archivo `estimates.csv` en la carpeta de salida (`paths.output_dir`). Contiene solo estimaciones: los meses sin cobertura nunca se rellenan con cero y los valores observados no se incluyen. Cada fila es un subdestino y un mes.

| Columna | Descripción |
|---|---|
| `destination` | Subdestino estimado. |
| `destination_group` | Grupo al que pertenece. |
| `period` | Mes estimado, primer día del mes (`AAAA-MM-01`). |
| `value` | Visitantes únicos estimados. |
| `unit` | Unidad de medida: `visitantes únicos del mes`. |
| `kind` | `estimate`, para distinguir las estimaciones de los valores observados. |
| `run_id` | Identificador de la ejecución que lo generó. |
| `generated_at` | Fecha y hora de generación. |
| `procedure_version` | Versión del procedimiento. |

## Reglas metodológicas que respeta el flujo

- Un período sin cobertura se presenta como sin dato, nunca como cero.
- No se suma la base diaria para obtener el mes: la serie mensual sale de la base mensual.
- No se suman subdestinos para obtener el total de un destino.
- No se suman visitantes mensuales de varios meses para obtener un total del período.
- No se promedia la permanencia promedio.
- Toda cifra estimada se rotula como estimación y se distingue de la observada.
- Los datos institucionales no se publican, no se versionan y no se incluyen en las imágenes de contenedor.
