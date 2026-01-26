#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Compatibility wrapper.

The CRUD API implementation now lives in script.py (single source of truth).
You can still run this file for convenience.
"""

import os

from script import create_app, get_default_mysql_config


if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8001"))
    debug = bool(int(os.getenv("API_DEBUG", "1")))

    mysql_cfg = get_default_mysql_config()
    app = create_app(mysql_cfg)
    app.run(host=host, port=port, debug=debug, use_reloader=False)
