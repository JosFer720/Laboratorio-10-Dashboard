from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.ingestion import SHEET_COLUMN


VISITOR_COLUMNS = ("sheet", "destination_group", "destination", "period", "visitors")
ENTRY_COLUMNS = ("period", "entries")
COVERAGE_COLUMNS = ("period", "mobility", "migration", "status")
COVERAGE_STATUS = {
    (True, True): "ambas fuentes",
    (True, False): "solo movilidad",
    (False, True): "solo entradas nacionales",
    (False, False): "sin cobertura",
}


@dataclass(frozen=True)
class PreparedData:
    visitors: pd.DataFrame
    entries: pd.DataFrame
    coverage: pd.DataFrame


def national_entries(migration: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Entradas nacionales de cada mes: suma de `Viajero` de los tipos configurados.

    Solo se usan los años desde `first_year`. Un mes sin filas no aparece en la
    serie; no se completa con cero.
    """
    settings = config.parameters.migration
    rows = migration.loc[
        migration["Tipo de Viajero"].isin(settings.traveler_types)
        & (migration["Año"] >= settings.first_year)
    ]
    months = pd.to_datetime(
        pd.DataFrame({"year": rows["Año"], "month": rows["Mes cod"], "day": 1})
    )
    entries = rows["Viajero"].groupby(months).sum(min_count=1).dropna()
    result = entries.rename_axis("period").rename("entries").reset_index()
    return result.loc[:, ENTRY_COLUMNS]


def subdestination_visitors(mobility: pd.DataFrame) -> pd.DataFrame:
    """Visitantes únicos de cada subdestino y mes según la base mensual.

    Dentro de un mismo subdestino y mes, las filas por país de residencia y por
    segmento de permanencia son grupos distintos de personas, así que se suman.
    Nunca se suman meses ni subdestinos entre sí. Los meses sin cobertura no
    tienen filas y quedan ausentes.
    """
    rows = mobility.assign(period=pd.to_datetime(mobility["fecha"]))
    monthly = (
        rows.groupby([SHEET_COLUMN, "sub_grupo", "destino", "period"], sort=True)[
            "visitantes"
        ]
        .sum(min_count=1)
        .dropna()
        .reset_index()
        .rename(
            columns={
                SHEET_COLUMN: "sheet",
                "sub_grupo": "destination_group",
                "destino": "destination",
                "visitantes": "visitors",
            }
        )
    )
    return monthly.loc[:, VISITOR_COLUMNS]


def coverage_table(
    visitors: pd.DataFrame, entries: pd.DataFrame, config: PipelineConfig
) -> pd.DataFrame:
    """Indica qué fuente tiene datos en cada mes de la ventana de trabajo."""
    periods = config.periods
    window = (*periods.mobility_coverage, *periods.estimate)
    months = pd.date_range(min(window), max(window), freq="MS")
    mobility_months = set(visitors["period"])
    entry_months = set(entries["period"])
    table = pd.DataFrame({"period": months})
    table["mobility"] = table["period"].isin(mobility_months)
    table["migration"] = table["period"].isin(entry_months)
    table["status"] = [
        COVERAGE_STATUS[(mobility, migration)]
        for mobility, migration in zip(table["mobility"], table["migration"])
    ]
    return table.loc[:, COVERAGE_COLUMNS]


def prepare(
    mobility: pd.DataFrame, migration: pd.DataFrame, config: PipelineConfig
) -> PreparedData:
    visitors = subdestination_visitors(mobility)
    entries = national_entries(migration, config)
    return PreparedData(
        visitors=visitors,
        entries=entries,
        coverage=coverage_table(visitors, entries, config),
    )
