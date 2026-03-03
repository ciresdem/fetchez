import subprocess
import sys

from fetchez.cli import parse_hook_arg

# Testing CLI using subprocess

# CMD will run Fetchez
CMD = [sys.executable, "-m", "fetchez.cli"]


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

    result = run_fetchez(["--modules"])
    assert result.returncode == 0
    assert "multibeam" in result.stdout
    assert "local" in result.stdout


def test_list_hooks():
    """Can we list hooks?"""

    result = run_fetchez(["--list-hooks"])
    assert result.returncode == 0
    assert "dryrun" in result.stdout
    assert "enrich" in result.stdout


def test_hook_info():
    """Does the hook-info flag work?"""

    result = run_fetchez(["--hook-info", "audit"])
    assert result.returncode == 0
    assert "Write a summary of all operations" in result.stdout


def test_dry_run_ipinfo():
    """Run a simple module."""

    result = run_fetchez(["ipinfo:ip=8.8.8.8", "--hook", "dryrun"])
    assert result.returncode == 0


# Testing cli functions from python


def test_parse_hook_arg_simple():
    """Test basic hook parsing with string arguments."""

    name, kwargs = parse_hook_arg("reproject:crs=EPSG:3857")
    assert name == "reproject"
    assert kwargs == {"crs": "EPSG:3857"}


def test_parse_hook_arg_type_inference():
    """Test if the parser correctly identifies booleans and numbers."""

    name, kwargs = parse_hook_arg("filter:match=.tif,force=true,retries=3")
    assert name == "filter"
    assert kwargs["match"] == ".tif"
    assert kwargs["force"] is True
    assert kwargs["retries"] == 3


def test_parse_hook_arg_no_args():
    """Test a hook string that has no arguments."""

    name, kwargs = parse_hook_arg("unzip")
    assert name == "unzip"
    assert kwargs == {}
