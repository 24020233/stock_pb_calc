#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from datetime import datetime

try:
    import mysql.connector
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "missing dependency: mysql-connector-python\n"
        "install: pip install mysql-connector-python\n"
        f"detail: {e}"
    )

from script import mysql_config_from_env


def _today_ymd() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear sector summary rows for a given day (default: today).")
    parser.add_argument("--date", default="", help="YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--only",
        default="",
        choices=["", "sectors", "picks"],
        help="Optionally clear only one table: sectors or picks (default: both)",
    )
    args = parser.parse_args()

    ymd = (args.date or "").strip() or _today_ymd()

    cfg = mysql_config_from_env()
    if not (cfg.get("password") or "").strip():
        raise SystemExit("Missing MySQL password. Set MYSQL_PASSWORD in .env and retry.")

    conn = mysql.connector.connect(**cfg)
    try:
        cur = conn.cursor()
        deleted_sectors = 0
        deleted_picks = 0

        if args.only in ("", "sectors"):
            cur.execute("DELETE FROM wx_sector_daily WHERE day=%s", (ymd,))
            deleted_sectors = int(cur.rowcount or 0)

        if args.only in ("", "picks"):
            cur.execute("DELETE FROM wx_sector_stock_pick WHERE day=%s", (ymd,))
            deleted_picks = int(cur.rowcount or 0)

        conn.commit()
        cur.close()
    finally:
        conn.close()

    if args.only == "sectors":
        print(f"Deleted {deleted_sectors} row(s) from wx_sector_daily for day={ymd}")
    elif args.only == "picks":
        print(f"Deleted {deleted_picks} row(s) from wx_sector_stock_pick for day={ymd}")
    else:
        print(f"Deleted {deleted_sectors} row(s) from wx_sector_daily for day={ymd}")
        print(f"Deleted {deleted_picks} row(s) from wx_sector_stock_pick for day={ymd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
