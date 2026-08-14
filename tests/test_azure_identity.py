from src.config.azure_identity import main


def test_identity_preflight_command_fails_closed(monkeypatch, capsys):
    monkeypatch.setattr("src.config.azure_identity.load_dotenv", lambda **_: None)
    monkeypatch.setattr(
        "src.config.azure_identity.verify_azure_cli_identity",
        lambda **_: (_ for _ in ()).throw(RuntimeError("wrong tenant")),
    )

    assert main() == 1
    assert "wrong tenant" in capsys.readouterr().err


def test_identity_preflight_command_reports_verified_context(monkeypatch, capsys):
    monkeypatch.setattr("src.config.azure_identity.load_dotenv", lambda **_: None)
    monkeypatch.setattr(
        "src.config.azure_identity.verify_azure_cli_identity",
        lambda **_: {
            "tenant_id": "admin-diamond-tenant",
            "subscription_id": "admin-diamond-subscription",
            "principal_id": "admin-diamond-principal",
            "user_principal_name": "admin@example.test",
        },
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert '"tenant_id": "admin-diamond-tenant"' in output
    assert '"subscription_id": "admin-diamond-subscription"' in output