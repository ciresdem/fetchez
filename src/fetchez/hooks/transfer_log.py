#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.transfer_log
~~~~~~~~~~~~~~~~~~~~~~~~~~
Generates a report of successful and failed downloads.
"""

import os
import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


class TransferLog(FetchHook):
    """Write a clear summary of failed and successful downloads."""

    name = "transfer_log"
    meta_desc = "Generates a clear report of download successes and failures."
    meta_stage = "post"
    meta_category = "metadata"

    def __init__(self, file="download_report.txt", **kwargs):
        super().__init__(**kwargs)
        self.filename = file

    def run(self, all_results):
        if not all_results:
            return all_results

        successes = []
        failures = []

        for mod, entry in all_results:
            # Status 0 indicates success in fetchez
            if entry.get("status") == 0:
                successes.append(entry)
            else:
                failures.append(entry)

        try:
            with open(self.filename, "w") as f:
                f.write("=" * 80 + "\n")
                f.write("FETCHEZ DOWNLOAD TRANSFER REPORT\n")
                f.write("=" * 80 + "\n\n")

                # Put failures at the very top so they are impossible to miss!
                f.write(f"FAILED DOWNLOADS ({len(failures)}):\n")
                f.write("-" * 80 + "\n")
                if not failures:
                    f.write("  None! All files downloaded successfully.\n")
                else:
                    for entry in failures:
                        f.write(f"  [FAIL] {entry.get('url', 'Unknown URL')}\n")
                        f.write(f"         Target: {entry.get('dst_fn', 'Unknown')}\n")

                f.write("\n" + "=" * 80 + "\n")
                f.write(f"SUCCESSFUL DOWNLOADS ({len(successes)}):\n")
                f.write("-" * 80 + "\n")
                for entry in successes:
                    f.write(f"  [OK] {os.path.basename(str(entry.get('dst_fn')))}\n")

            logger.info(f"Transfer log written to {self.filename}")

            if failures:
                logger.warning(
                    f"Pipeline finished with {len(failures)} failed downloads. Check {self.filename}."
                )

        except Exception as e:
            logger.error(f"Failed to write transfer log: {e}")

        return all_results
