"""Contratos del informe compartido por los cinco repositorios."""
import importlib.util
from pathlib import Path
import pytest


ruta = Path(__file__).resolve().parents[1] / ".github/actions/coordinacion/coordinar.py"
spec = importlib.util.spec_from_file_location("coordinacion", ruta)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def test_version_acepta_comentarios_y_rechaza_ambiguedad():
    sha = "a" * 40
    assert c.version("# proveedor\n" + sha + " # integrado\n") == sha
    for invalida in ("main", sha[:7], sha + "\n" + sha, ""):
        with pytest.raises(ValueError):
            c.version(invalida)


def test_cruces_solo_en_una_base_comun():
    def pr(n, base, *rutas):
        return {"n": n, "base": base, "rutas": set(rutas)}

    assert list(c.cruces([pr(1, "main", "cubo.py", "doc.md"), pr(2, "main", "cubo.py"),
                          pr(3, "otra", "cubo.py")])) == [(1, 2, ["cubo.py"])]


@pytest.mark.parametrize("propio,esperado", [(c.G7B, False), (c.WEB, True)])
def test_visibilidad_y_divergencia(tmp_path, monkeypatch, propio, esperado):
    consultas = []
    def informar(repo, lineas):
        consultas.append(repo)
        return "principal", "c" * 40

    monkeypatch.setenv("GITHUB_REPOSITORY", c.OWNER + "/" + propio)
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "resumen"))
    monkeypatch.setattr(c, "informar", informar)
    monkeypatch.setattr(c, "fijadas", lambda repo, local, sha: {c.MOTOR: "a" * 40, c.G7B: ("a" if repo == c.API else "b") * 40})
    monkeypatch.setattr(c, "api", lambda *args: {"status": "ahead"})
    assert c.main() is esperado
    assert (c.WEB in consultas) is esperado
    assert ("fijan versiones distintas" in (tmp_path / "resumen").read_text(encoding="utf-8")) is esperado
