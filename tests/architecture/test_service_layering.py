"""The business layer must not know the database exists.

Services work with domain objects and reach the database only through the
repositories exposed by the unit of work. This test fails the moment a service
imports SQLAlchemy or the ORM models directly.
"""

import ast
from pathlib import Path

import pytest

SERVICES = Path(__file__).resolve().parents[2] / "app" / "services"
FORBIDDEN = ("sqlalchemy", "app.infra")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize(
    "path",
    sorted(SERVICES.glob("*.py")),
    ids=lambda path: path.name,
)
def test_service_does_not_import_the_database(path: Path) -> None:
    offenders = {
        module
        for module in imported_modules(path)
        if module.split(".")[0] in {"sqlalchemy"}
        or module == "app.infra"
        or module.startswith("app.infra.")
    }
    assert not offenders, f"{path.name} imports the database layer: {sorted(offenders)}"


def test_every_service_is_covered() -> None:
    files = {path.name for path in SERVICES.glob("*.py")}
    assert files, "no service files found, the check is not running"
