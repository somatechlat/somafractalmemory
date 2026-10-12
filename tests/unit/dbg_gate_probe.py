"""TEMPORARY probe — delete after diagnosis."""

from __future__ import annotations


def test_dbg_gate():
    from django.conf import settings

    cfg = settings.DATABASES["default"]
    print(
        "CFG:", {k: cfg[k] for k in ("NAME", "USER", "HOST", "PORT")}, "pwlen", len(cfg["PASSWORD"])
    )
    try:
        import psycopg

        conn = psycopg.connect(
            host=cfg["HOST"],
            port=int(cfg["PORT"]),
            dbname=cfg["NAME"],
            user=cfg["USER"],
            password=cfg["PASSWORD"],
            connect_timeout=2,
        )
        print("CONNECT OK")
        conn.close()
    except Exception as e:
        print("CONNECT FAIL:", type(e).__name__, e)
    raise AssertionError("force output")
