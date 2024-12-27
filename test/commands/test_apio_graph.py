"""
  Test for the "apio graph" command
"""

from test.conftest import ApioRunner
from apio.commands.apio import cli as apio


# R0801: Similar lines in 2 files
# pylint: disable=R0801
def test_graph_no_apio_ini(apio_runner: ApioRunner):
    """Test: apio graph with no apio.ini"""

    with apio_runner.in_sandbox() as sb:

        # -- Execute "apio graph"
        result = sb.invoke_apio_cmd(apio, ["graph"])
        assert result.exit_code == 1, result.output
        assert "Error: missing project file apio.ini" in result.output


def test_graph_with_apio_ini(apio_runner: ApioRunner):
    """Test: apio graph with apio.ini"""

    with apio_runner.in_sandbox() as sb:

        # -- Create an apio.ini file
        sb.write_default_apio_ini()

        # -- Execute "apio graph"
        result = sb.invoke_apio_cmd(apio, ["graph"])
        assert result.exit_code == 1, result.output
        assert "package 'oss-cad-suite' is not installed" in result.output

        # -- Execute "apio graph -pdf"
        result = sb.invoke_apio_cmd(apio, ["graph"])
        assert result.exit_code == 1, result.output
        assert "package 'oss-cad-suite' is not installed" in result.output

        # -- Execute "apio graph -png"
        result = sb.invoke_apio_cmd(apio, ["graph"])
        assert result.exit_code == 1, result.output
        assert "package 'oss-cad-suite' is not installed" in result.output