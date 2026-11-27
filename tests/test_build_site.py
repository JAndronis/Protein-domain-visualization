import json
import re
import shutil
from pathlib import Path

import build_site

PKG = Path(build_site.__file__).resolve().parent.parent / "src" / "protein_domains"
SOURCES = re.compile(
    r'<script id="py-sources" type="application/json">(.*?)</script>', re.S
)


def sources_of(index: Path) -> dict:
    return json.loads(SOURCES.search(index.read_text(encoding="utf-8")).group(1))


def test_build_writes_one_page_that_carries_every_package_module(tmp_path):
    index = build_site.build(tmp_path)
    assert index == tmp_path / "index.html"
    assert sorted(p.name for p in tmp_path.iterdir()) == [".nojekyll", "index.html"]
    assert sources_of(index) == {
        p.name: p.read_text(encoding="utf-8") for p in PKG.glob("*.py")
    }


def test_build_pins_the_pyodide_script_before_the_page_script(tmp_path):
    html = build_site.build(tmp_path).read_text(encoding="utf-8")
    assert f'<script src="{build_site.PYODIDE}"></script>' in html
    assert "/pyodide/v314.0.7/" in build_site.PYODIDE
    assert (
        html.index(build_site.PYODIDE)
        < html.index('id="py-sources"')
        < html.index("<script>")
    )


def test_pyodide_url_can_be_overridden(tmp_path):
    html = build_site.build(tmp_path, "http://localhost:9/pyodide.js").read_text(
        encoding="utf-8"
    )
    assert '<script src="http://localhost:9/pyodide.js"></script>' in html


def test_source_containing_a_script_end_tag_survives(tmp_path, monkeypatch):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    shutil.copy(PKG / "gui.html", pkg)
    (pkg / "evil.py").write_text('X = "</script><script>alert(1)</script>"\n')
    monkeypatch.setattr(build_site, "PKG", pkg)
    index = build_site.build(tmp_path / "site")
    assert sources_of(index) == {
        "evil.py": 'X = "</script><script>alert(1)</script>"\n'
    }
    assert index.read_text(encoding="utf-8").count("</script>") == 3


def test_second_build_is_byte_identical(tmp_path):
    first = build_site.build(tmp_path / "a").read_bytes()
    build_site.build(tmp_path / "b")
    assert build_site.build(tmp_path / "a").read_bytes() == first
    assert (tmp_path / "b" / "index.html").read_bytes() == first


def test_page_names_no_origin_but_the_cdn_uniprot_and_namespaces(tmp_path):
    html = build_site.build(tmp_path).read_text(encoding="utf-8")
    origins = set(re.findall(r"https?://[^/\s\"'<>\\{}]+", html))
    allowed = {
        "https://cdn.jsdelivr.net",
        "https://rest.uniprot.org",
        "http://www.w3.org",
        "http://127.0.0.1:",  # gui.py's printed address; Python cannot open sockets in the page
    }
    assert origins <= allowed, origins - allowed


def test_main_writes_to_the_directory_given(tmp_path, capsys):
    build_site.main(["-o", str(tmp_path / "out")])
    assert (tmp_path / "out" / "index.html").exists()
    assert "index.html" in capsys.readouterr().out
