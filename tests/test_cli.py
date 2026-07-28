# test_cli.py
import pytest
import subprocess
import sys

from fetchez.utils import parse_hook_string
from fetchez.cli import cli

from click.testing import CliRunner

# Testing CLI using subprocess

# CMD will run Fetchez
CMD = [sys.executable, "-m", "fetchez.cli.__init__"]


@pytest.fixture
def runner():
    """Fixture to provide a Click CliRunner for all tests."""

    return CliRunner()


def run_fetchez(args):
    """Run fetchez and return result."""

    return subprocess.run(CMD + args, capture_output=True, text=True)


def test_help():
    """Does the help menu work?"""

    result = run_fetchez(["--help"])
    assert result.returncode == 0


def test_version():
    """Does version print?"""

    result = run_fetchez(["--version"])
    assert result.returncode == 0


def test_list_modules():
    """Can we list modules without crashing?"""

    result = run_fetchez(["modules", "list"])
    assert result.returncode == 0
    assert "multibeam" in result.stdout
    assert "local" in result.stdout


def test_list_hooks():
    """Can we list hooks?"""

    result = run_fetchez(["hooks", "list"])
    assert result.returncode == 0
    assert "dryrun" in result.stdout
    assert "enrich" in result.stdout


def test_hook_info():
    """Does the hook-info flag work?"""

    result = run_fetchez(["hooks", "info", "audit"])
    assert result.returncode == 0
    assert "Save a run summary of fetch entries to disk" in result.stdout


# this test randomly fails sometimes, due to network issues
# def test_dry_run_ipinfo():
#     """Run a simple module."""

#     result = run_fetchez(["run", "ipinfo", "--ip", "8.8.8.8", "--hook", "dryrun"])
#     assert result.returncode == 0


# test module string parsing in cli (no supported atm)
# def test_dry_run_ipinfo():
#     """Run a simple module."""

#     result = run_fetchez(["run", "ipinfo:ip=8.8.8.8", "--hook", "dryrun"])
#     assert result.returncode == 0


# Testing cli functions from python


def test_parse_hook_string_simple():
    """Test basic hook parsing with string arguments."""

    hook = parse_hook_string("reproject:crs=EPSG:3857")
    assert hook["name"] == "reproject"
    assert hook["args"] == {"crs": "EPSG:3857"}


def test_parse_hook_string_type_inference():
    """Test if the parser correctly identifies booleans and numbers."""

    hook = parse_hook_string("filter:match=.tif,force=true,retries=3")
    assert hook["name"] == "filter"
    assert hook["args"]["match"] == ".tif"
    assert hook["args"]["force"] is True
    assert hook["args"]["retries"] == 3


def test_parse_hook_string_no_args():
    """Test a hook string that has no arguments."""

    hook = parse_hook_string("unzip")
    assert hook["name"] == "unzip"
    assert hook.get("args") is None


def test_region_echo_bbox(runner):
    """Test the spatial parsing engine (No network required)."""

    result = runner.invoke(
        cli, ["regions", "echo", "-R", "-120/-119/34/35", "-F", "gmt"]
    )

    assert result.exit_code == 0
    assert "-120.0/-119.0/34.0/35.0" in result.output.strip()
