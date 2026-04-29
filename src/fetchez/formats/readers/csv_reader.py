#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.formats.readers.csv_reader
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Basic CSV reader.

:copyright: (c) 2016 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import csv
from .. import BaseReader


class CSVReader(BaseReader):
    meta_dtype = "csv"
    meta_extensions = ["csv", "dat", "xyz", "txt"]
    meta_desc = "Read and stream CSV data as list or dict."

    def __init__(self, path, newline="", encoding="utf-8", as_dict=False, **kwargs):
        super().__init__(path, **kwargs)
        self.newline = newline
        self.encoding = encoding
        self.as_dict = as_dict

    def yield_chunks(self):
        # just reads the data and yields generic chunks as list or dict
        with open(self.path, mode='r', newline=self.newline, encoding=self.encoding) as file:
            if self.as_dict:
                for chunk in csv.DictReader(file):
                    yield chunk
            else:
                for chunk in csv.reader(file):
                    yield chunk
