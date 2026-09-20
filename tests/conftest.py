"""Stub `basedosdados` so the package imports offline in CI (no BigQuery needed)."""
import sys
import types

if "basedosdados" not in sys.modules:
    stub = types.ModuleType("basedosdados")

    def read_sql(*args, **kwargs):
        raise RuntimeError("basedosdados stub: BigQuery is not available in tests")

    stub.read_sql = read_sql
    sys.modules["basedosdados"] = stub
