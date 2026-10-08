# cli/tests/test_client.py
from du_cli import client

def test_auth_headers():
    h = client.auth_headers("k1", None)
    assert h == {"X-API-Key": "k1"}
    h2 = client.auth_headers("k1", "idem-1")
    assert h2["Idempotency-Key"] == "idem-1"

def test_error_hint_maps_401_402_503():
    assert "du configure" in client.error_hint(401, "bad key")
    assert "Wallet" in client.error_hint(402, "insufficient_balance")
    assert "retry" in client.error_hint(503, "saturated").lower()

def test_raise_for_api_raises_clierror():
    try:
        client.raise_for_api(401, "bad key")
    except client.CliError as e:
        assert e.status == 401
        assert "du configure" in e.hint
    else:
        raise AssertionError("should raise")

def test_diarize_404_hint():
    try:
        client.raise_for_api(404, "not found", path="/diarize")
    except client.CliError as e:
        assert "not deployed yet" in e.hint
    else:
        raise AssertionError("should raise")

def test_make_client_timeout():
    c = client.make_client()
    assert c.timeout.read == 300.0
    c.close()
