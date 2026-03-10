#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.schemas.base
~~~~~~~~~~~~~~

Generic Schema Registry for the Fetchez Recipe Engine.
Allows external domains (like Globato) to register
custom recipe mutators.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaseSchema:
    """The generic base class for all recipe schemas."""

    name = "base"

    @classmethod
    def apply(cls, config):
        """Mutates and returns the recipe config.
        Subclasses must override this to inject their domain-specific rules.
        """

        return config
