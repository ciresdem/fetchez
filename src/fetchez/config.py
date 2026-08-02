#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.config
~~~~~~~~~~~~~

config file ~/.fetchez/ ...

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import json
import yaml
from pathlib import Path
import logging

home_dir = Path.home()
CONFIG_PATH = home_dir / ".fetchez"

logger = logging.getLogger(__name__)


def load_user_config(config_name):
    """Load the user's config file. Can be yaml or json."""

    exts = [".yaml", ".yml", ".json"]

    for ext in exts:
        config_file = CONFIG_PATH / Path(config_name + ext)
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    if config_file.suffix == ".json":
                        return json.load(f)
                    else:
                        return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Could not load config file {config_file}: {e}")

    return {}
