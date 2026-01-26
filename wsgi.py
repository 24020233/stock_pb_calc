#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""WSGI entrypoint for production servers (e.g. gunicorn).

Runs the Flask app defined in script.py.
"""

from script import create_app, get_default_mysql_config

app = create_app(get_default_mysql_config())
