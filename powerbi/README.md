# Informe en Power BI

## Versión de Power BI Desktop

El informe se actualizó y guardó con Power BI Desktop `2.159.1231.0 (64 bits)` en Windows.

## Resultados comprobados en Desktop

La actualización terminó correctamente el 5 de noviembre de 2026. Se cargaron las ocho tablas y se conservaron las siete relaciones del modelo. Las consultas de `comprobaciones.dax` dieron estos resultados:

- total histórico: `46,711,912.89`, mostrado como `46,711,913`;
- máximo histórico: diciembre de 2019, con `449,114.07`, mostrado como `449,114`;
- observado de diciembre de 2025: `365573.0218067979`, mostrado como `365,573.02`, sin variar al seleccionar uno o todos los modelos.

La página **Llegadas y mercados** incluye una línea temporal con la jerarquía año > trimestre > mes y barras por mercado de origen. La selección de un período en la primera visualización filtra la segunda. Ambas usan la medida:

```DAX
Llegadas = SUM(Llegadas[arrivals])
```

## Abrir el informe

La definición editable está en `observatorio_turismo.pbip`, con el modelo en `observatorio_turismo.SemanticModel/model.bim` y el informe en `observatorio_turismo.Report/`. El archivo actualizado para continuar el trabajo está en `observatorio_turismo.pbix`.

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

## Tema

`tema_observatorio.json` contiene la paleta y las fuentes del tablero: azul `#0B5C8E` para lo observado, naranja `#D55E00` para lo estimado, gris `#8A939E` para el contexto y la escala de azules para cantidades. Se aplica en Power BI Desktop desde Vista > Temas > Buscar temas. Usa la fuente Inter si está instalada en el equipo y, si no, Segoe UI.

El proyecto incluye una copia idéntica en `observatorio_turismo.Report/StaticResources/RegisteredResources/`. Si cambia el tema, actualiza también ese recurso; el verificador detecta diferencias entre las dos copias.

## Formato del proyecto

Se usan los formatos documentados por Microsoft: [proyectos PBIP](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [modelo semántico en TMSL](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset) e [informe PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report). No se incluyen cachés ni configuraciones personales de `.pbi/`.
