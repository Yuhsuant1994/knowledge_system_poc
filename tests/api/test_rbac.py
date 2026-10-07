import pytest

from api.auth.rbac import allowed_domains


@pytest.mark.parametrize("role", ["admin", "dev"])
def test_admin_and_dev_have_everything(role):
    assert allowed_domains(role) == {"hr_rag", "sales_sql", "github"}


def test_user_has_hr_only():
    assert allowed_domains("user") == {"hr_rag"}


def test_sales_has_hr_and_sql():
    assert allowed_domains("sales") == {"hr_rag", "sales_sql"}


def test_unknown_role_has_nothing():
    assert allowed_domains("bogus") == set()
