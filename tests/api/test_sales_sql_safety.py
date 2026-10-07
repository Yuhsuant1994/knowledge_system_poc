import pytest

from api.agents.sales_sql_agent import _clean_sql, _validate


def test_clean_sql_strips_fences():
    assert _clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1"


def test_clean_sql_strips_trailing_semicolon():
    assert _clean_sql("SELECT 1;") == "SELECT 1"


def test_validate_accepts_select():
    _validate("SELECT * FROM orders")


def test_validate_accepts_cte():
    _validate("WITH x AS (SELECT 1) SELECT * FROM x")


def test_validate_rejects_insert():
    with pytest.raises(ValueError):
        _validate("INSERT INTO orders VALUES (1)")


def test_validate_rejects_drop():
    with pytest.raises(ValueError):
        _validate("DROP TABLE orders")


def test_validate_rejects_semicolon_stacking():
    with pytest.raises(ValueError):
        _validate("SELECT 1; DROP TABLE orders")
