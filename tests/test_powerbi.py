"""Controles de portabilidad y de integridad de las fuentes del informe."""

from __future__ import annotations

import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preparar_powerbi import prepare  # noqa: E402
from verificar_powerbi import FILES, verify  # noqa: E402


def test_reference_totals_and_single_monthly_observed():
    result = verify(ROOT / "data")
    assert result["filas_esperadas"]["Predicciones"] == 189
    assert result["filas_esperadas"]["Observados"] == 63
    assert Decimal(result["llegadas_total_sin_redondear"]).quantize(Decimal(1)) == Decimal(46711913)
    assert Decimal(result["observado_diciembre_2025"]) == Decimal("365573.0218067979")
    assert result["mes_maximo"]["date"] == "2019-12-01"


def test_changed_source_is_rejected(tmp_path):
    for name in FILES:
        shutil.copy2(ROOT / "data" / name, tmp_path / name)
    predictions = tmp_path / "model_predictions_s0.csv"
    content = predictions.read_text(encoding="utf-8")
    predictions.write_text(content.replace("365573.0218067979", "1096719.0654203937", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="difiere del commit"):
        verify(tmp_path)


def test_local_project_does_not_change_tracked_parameter_or_overwrite_work(tmp_path):
    model_path = ROOT / "powerbi/observatorio_turismo.SemanticModel/model.bim"
    original = model_path.read_bytes()
    local_data = tmp_path / "datos turismo"
    local_data.mkdir()
    for name in FILES:
        shutil.copy2(ROOT / "data" / name, local_data / name)
    output = tmp_path / "proyecto"
    project = prepare(local_data, output)
    assert project.is_file()
    database = json.loads((output / "observatorio_turismo.SemanticModel/model.bim").read_text(encoding="utf-8"))
    parameter = next(e for e in database["model"]["expressions"] if e["name"] == "pCarpetaDatos")
    literal = '"' + local_data.as_posix().replace('"', '""') + '"'
    assert parameter["expression"][0].startswith(literal + " meta ")
    assert model_path.read_bytes() == original
    marker = output / "edicion.txt"
    marker.write_text("conservar esta edición", encoding="utf-8")
    with pytest.raises(FileExistsError, match="ya existe"):
        prepare(local_data, output)
    assert marker.read_text(encoding="utf-8") == "conservar esta edición"
