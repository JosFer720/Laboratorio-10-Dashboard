"""Regresiones de integridad, selección de modelos y conservación del PBIX."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from empaquetar_powerbi import package  # noqa: E402
from verificar_informe_powerbi import PAGES, verify  # noqa: E402


REPORT = ROOT / "powerbi/observatorio_turismo.Report"
PBIX = ROOT / "powerbi/observatorio_turismo.pbix"


def test_complete_report_keeps_all_visuals_and_imported_data():
    result = verify()
    assert result["visualizaciones_principales"] == 8
    assert result["modelo_importado_conservado"]
    assert result["pbir_y_pbix_coinciden"]


def test_heat_matrix_cannot_be_replaced_by_another_visual(tmp_path):
    report = tmp_path / "informe.Report"
    shutil.copytree(REPORT, report)
    path = report / f"definition/pages/{PAGES['Temporadas y hospedaje']}/visuals/v3_estacionalidad/visual.json"
    visual = json.loads(path.read_text(encoding="utf-8"))
    visual["visual"]["visualType"] = "scatterChart"
    path.write_text(json.dumps(visual), encoding="utf-8")
    with pytest.raises(ValueError, match="Falta V3"):
        verify(report_dir=report)


def test_v7_model_slicer_cannot_filter_out_comparison_models(tmp_path):
    report = tmp_path / "informe.Report"
    shutil.copytree(REPORT, report)
    path = report / f"definition/pages/{PAGES['Predicciones y modelos']}/page.json"
    page = json.loads(path.read_text(encoding="utf-8"))
    for rule in page["visualInteractions"]:
        if rule["source"] == "filtro_modelo" and rule["target"] == "tabla_metricas":
            rule["type"] = "DataFilter"
    path.write_text(json.dumps(page), encoding="utf-8")
    with pytest.raises(ValueError, match="comparación de los tres modelos"):
        verify(report_dir=report)


def test_packaging_is_repeatable_without_modifying_the_imported_model(tmp_path):
    output = tmp_path / "informe.pbix"
    with zipfile.ZipFile(PBIX) as original:
        expected_model = original.read("DataModel")
    first = package(PBIX, REPORT, output)
    package(output, REPORT, output)
    with zipfile.ZipFile(output) as result:
        assert result.read("DataModel") == expected_model
        assert result.testzip() is None
        assert len(result.namelist()) == len(set(result.namelist()))
    assert first["sha256_modelo_conservado"] == hashlib.sha256(expected_model).hexdigest()
    assert verify(pbix_path=output)["pbir_y_pbix_coinciden"]
