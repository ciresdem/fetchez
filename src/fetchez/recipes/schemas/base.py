#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.recipes.schemas.base
~~~~~~~~~~~~~~

Generic Schema Registry for the Fetchez Recipe Engine.
Allows external domains (like Globato) to register
custom recipe validations.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import logging

logger = logging.getLogger(__name__)


class BaseSchema:
    """The generic base class for all recipe schemas."""

    name = "base"

    @classmethod
    def validate(cls, config):
        """Validatesthe recipe config based on rules and returns [True/False, {errors}]
        Subclasses must override this to inject their domain-specific rules.
        """

        return config
