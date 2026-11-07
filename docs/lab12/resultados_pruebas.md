# Resultados de las pruebas

Fecha: 7 de noviembre de 2026. Se ejecutó la referencia `lab10-final` en un worktree separado, con sus propios datos y sin modificarla. El servidor estuvo en `http://127.0.0.1:8051`. Las tres tareas se probaron mediante solicitudes reales al endpoint de callbacks de Dash. Esta es una prueba de integración del servidor, no una medición de navegación de una persona.

## Prueba 1: máximo de llegadas de 2025

Se aplicaron enero a diciembre de 2025, todos los mercados y detalle mensual. El callback produjo «Diciembre de 2025», «365.573» y total anual «3.352.289». Coincide con la referencia. Tiempo de la solicitud de tarea: 41,740 ms.

## Prueba 2: región, país y regreso

Se consultó el peso regional de 2025, se envió el evento de selección de América Central y se consultaron sus mercados. El servidor produjo 2.143.694 llegadas y 63,9 % para la región; El Salvador fue el primero, con 1.582.845 y 73,8 % de la región. El evento de regreso recuperó las cinco regiones. Coincide con la referencia. Tiempo de la secuencia HTTP: 334,347 ms.

## Prueba 3: modelos y errores

Se consultaron los tres modelos y sus errores. Los textos de MAPE fueron 29,2 %, 60,9 % y 59,3 %. LSTM tuvo el menor MAPE y error de diciembre de 2025 de -142130,70322635162, mostrado sin decimales como -142.131. El observado fue 365573,0218067979 con cada modelo. Tiempo de la secuencia HTTP: 170,677 ms.

## Controles adicionales

- Las consultas de las ocho visualizaciones respondieron correctamente.
- Hospedaje en 2025 produjo el mensaje de falta de cobertura; no se imputaron ceros.
- El resumen de llegadas de 2024 produjo «3.274.436».
- Ocho solicitudes repetidas del callback temporal dieron mediana de 42,438 ms, mínimo de 39,787 y máximo de 43,236 ms.
- Pasaron 320 pruebas del repositorio actual y 171 de la referencia de Dash. Los resultados se extrajeron de sus archivos JUnit.
- El validador oficial de Power BI, versión 0.5.0, terminó con cero errores y cero advertencias después de corregir tema, propiedades de segmentadores y metadatos.
- El modelo importado del PBIX conserva su contenido y sus métricas; el informe contiene ocho visualizaciones y quince medidas propias de informe.

## Intentos interactivos y límites

El control de Chrome presentó errores al navegar y leer la página. El intento nativo tampoco permitió continuar la interacción. Se pudo verificar el servidor, pero no se cuentan clics ni se asignan tiempos de uso humano. Las imágenes en `capturas/` son exportaciones de las figuras devueltas por el servidor, identificadas como tales; no son capturas de una sesión interactiva.

Se instalaron y ejecutaron las herramientas oficiales de autoría de Power BI. La consulta de estado y el intento de apertura devolvieron `HOST_UNAVAILABLE` con diagnóstico `UNSUPPORTED_OS`: el puente de Desktop solo está disponible en Windows. El proyecto utiliza un modelo local y no tiene un modelo publicado configurado para la alternativa del servicio. No se ejecutaron DAX, filtros, marcadores ni capturas nativas de Power BI en esta sesión.

Por lo tanto, el protocolo original de dos interfaces en el mismo equipo Windows no pudo completarse. No se considera aprobada la comparación de clics, apertura, actualización o respuesta visual. Los resultados de HTTP no reemplazan esas mediciones.

## Evidencia y reproducción

`evidencia_http/pruebas_http.json` contiene los resultados y tiempos de cada llamada. Los archivos `.plotly.json` conservan las figuras recibidas. `resultado_suites.json`, `validacion_oficial_pbir.json`, `entorno_pruebas.json` y `validacion_modelos_pbix.json` registran las demás comprobaciones.

Para repetir las consultas después de iniciar la referencia en el puerto 8051:

```bash
python scripts/pruebas_http_lab12.py --url http://127.0.0.1:8051
```

Los pasos de interfaz siguen en `protocolo_pruebas.md`; sus casillas no se llenaron con observaciones no realizadas.
