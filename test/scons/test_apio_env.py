"""
Tests of the scons ApioEnv.
"""

import os
from os.path import isfile, exists
from pathlib import Path
from typing import Dict
from test.conftest import ApioRunner
import pytest
import SCons.Script.SConsOptions
from SCons.Node.FS import FS
import SCons.Node.FS
import SCons.Environment
import SCons.Defaults
import SCons.Script.Main
from SCons.Script import SetOption
from pytest import LogCaptureFixture
from apio.scons.apio_env import ApioEnv, SconsArch


class SconsHacks:
    """A collection of staticmethods that encapsulate scons access outside of
    the official scons API. Hopefully this will not be too difficult to adapt
    in future versions of SCons."""

    @staticmethod
    def reset_scons_state() -> None:
        """Reset the relevant SCons global variables. וUnfurtunally scons
        uses a few global variables to hold its state. This works well in
        normal operation where an scons process contains a single scons
        session but with pytest testing, where multiple independent tests
        are running in the same process, we need to reset though variables
        before each test."""

        # -- The Cons.Script.Main.OptionsParser variables contains the command
        # -- line options of scons. We reset them here and tests can access
        # -- them using SetOption() and GetOption().

        parser = SCons.Script.SConsOptions.Parser("my_fake_version")
        values = SCons.Script.SConsOptions.SConsValues(
            parser.get_default_values()
        )
        parser.parse_args(args=[], values=values)
        SCons.Script.Main.OptionsParser = parser

        # -- Reset the scons target list variable.
        SCons.Node.FS.default_fs = None

        # -- Clear the SCons targets
        SCons.Environment.CleanTargets = {}

    @staticmethod
    def get_targets() -> Dict:
        """Get the scons {target -> dependencies} dictionary."""
        return SCons.Environment.CleanTargets


def make_test_apio_env(
    args: Dict[str, str] = None, extra_args: Dict[str, str] = None
) -> ApioEnv:
    """Creates a fresh apio env with given args. The env is created
    with the current directory as the root dir.
    """

    # -- Bring scons to a starting state.
    SconsHacks.reset_scons_state()

    # -- Default, when we don't really care about the content.
    if args is None:
        args = {
            "platform_id": "darwin_arm64",
        }

    # -- If specified, overite/add extra args.
    if extra_args:
        args.update(extra_args)

    # -- Setup required env vars.
    os.environ["YOSYS_LIB"] = "fake yosys lib"
    os.environ["TRELLIS"] = "fake trelis"

    # -- Create and return the apio env.
    return ApioEnv(
        scons_arch=SconsArch.ICE40,
        scons_args=args,
        command_line_targets=["build"],
        is_debug=False,
    )


def test_dependencies(apio_runner: ApioRunner):
    """Test the verilog scanner which scans a verilog file and extract
    reference of files it uses.
    """

    # -- Test file content with references. Contains duplicates and
    # -- references out of alphabetical order.
    file_content = """
        // Dummy file for testing.

        // Icestudio reference.
        parameter v771499 = "v771499.list"

        // System verilog include reference.
        `include "apio_testing.vh"

        // Duplicate icestudio reference.
        parameter v771499 = "v771499.list"

        // Verilog include reference.
        `include "apio_testing.v

        // $readmemh() function reference.
        $readmemh("my_data.hex", State_buff);
        """

    with apio_runner.in_sandbox() as sb:

        # -- Write a test file name in the current directory.
        sb.write_file("test_file.v", file_content)

        # -- Create a scanner
        apio_env = make_test_apio_env()
        scanner = apio_env.verilog_src_scanner()

        # -- Run the scanner. It returns a list of File.
        file = FS.File(FS(), "test_file.v")
        dependency_files = scanner.function(file, apio_env, None)

        # -- Files list should be empty since none of the dependency candidate
        # has a file.
        file_names = [f.name for f in dependency_files]
        assert file_names == []

        # -- Create file lists
        core_dependencies = [
            "apio.ini",
            "boards.json",
            "programmers.json",
            "fpgas.json",
        ]

        file_dependencies = [
            "apio_testing.vh",
            "my_data.hex",
            "v771499.list",
        ]

        # -- Create dummy files. This should cause the dependencies to be
        # -- reported. (Candidate dependencies with no matching file are
        # -- filtered out)
        for f in core_dependencies + file_dependencies + ["non-related.txt"]:
            sb.write_file(f, "dummy-file")

        # -- Run the scanner again
        dependency_files = scanner.function(file, apio_env, None)

        # -- Check the dependnecies
        file_names = [f.name for f in dependency_files]
        assert file_names == sorted(core_dependencies + file_dependencies)


def test_has_testbench_name():
    """Tests the scons_util.test_is_testbench() method"""

    env = make_test_apio_env()

    # -- Testbench names
    assert env.has_testbench_name("aaa_tb.v")
    assert env.has_testbench_name("aaa_tb.out")
    assert env.has_testbench_name("bbb/aaa_tb.v")
    assert env.has_testbench_name("bbb\\aaa_tb.v")
    assert env.has_testbench_name("aaa__tb.v")
    assert env.has_testbench_name("Aaa__Tb.v")
    assert env.has_testbench_name("bbb/aaa_tb.v")
    assert env.has_testbench_name("bbb\\aaa_tb.v")

    # -- Non testbench names.
    assert not env.has_testbench_name("aaatb.v")
    assert not env.has_testbench_name("aaa.v")


def test_is_verilog_src():
    """Tests the scons_util.is_verilog_src() method"""

    e = make_test_apio_env()

    # -- Verilog and system-verilog source names, system-verilog included.
    assert e.is_verilog_src("aaa.v")
    assert e.is_verilog_src("bbb/aaa.v")
    assert e.is_verilog_src("bbb\\aaa.v")
    assert e.is_verilog_src("aaatb.v")
    assert e.is_verilog_src("aaa_tb.v")
    assert e.is_verilog_src("aaa.sv")
    assert e.is_verilog_src("bbb\\aaa.sv")
    assert e.is_verilog_src("aaa_tb.sv")

    # -- Verilog and system-verilog source names, system-verilog excluded.
    assert e.is_verilog_src("aaa.v", include_sv=False)
    assert e.is_verilog_src("bbb/aaa.v", include_sv=False)
    assert e.is_verilog_src("bbb\\aaa.v", include_sv=False)
    assert e.is_verilog_src("aaatb.v", include_sv=False)
    assert e.is_verilog_src("aaa_tb.v", include_sv=False)
    assert not e.is_verilog_src("aaa.sv", include_sv=False)
    assert not e.is_verilog_src("bbb\\aaa.sv", include_sv=False)
    assert not e.is_verilog_src("aaa_tb.sv", include_sv=False)

    # -- Non verilog source names, system-verilog included.
    assert not e.is_verilog_src("aaatb.vv")
    assert not e.is_verilog_src("aaatb.V")
    assert not e.is_verilog_src("aaa_tb.vh")

    # -- Non verilog source names, system-verilog excluded.
    assert not e.is_verilog_src("aaatb.vv", include_sv=False)
    assert not e.is_verilog_src("aaatb.V", include_sv=False)
    assert not e.is_verilog_src("aaa_tb.vh", include_sv=False)


def test_env_args():
    """Tests the scons env args retrieval."""

    env = make_test_apio_env(
        args={
            "platform_id": "my_platform",
            "verbose_all": "True",
        }
    )

    # -- String args
    assert env.args.PLATFORM_ID == "my_platform"
    assert env.args.GRAPH_SPEC == ""

    # -- Bool args.
    assert env.args.VERBOSE_ALL
    assert not env.args.VERBOSE_YOSYS

    # -- Env var strings
    assert env.args.YOSYS_PATH == "fake yosys lib"
    assert env.args.TRELLIS_PATH == "fake trelis"


def test_env_platform_id():
    """Tests the env handling of the paltform_id var."""

    # -- Test with a non windows platform id.
    env = make_test_apio_env({"platform_id": "darwin_arm64"})
    assert not env.is_windows

    # -- Test with a windows platform id.
    env = make_test_apio_env({"platform_id": "windows_amd64"})
    assert env.is_windows


def test_clean_if_requested(apio_runner: ApioRunner):
    """Tests the success path of set_up_cleanup()."""

    with apio_runner.in_sandbox():

        # -- Create an env with 'clean' option set.
        apio_env = make_test_apio_env()

        # -- Create files that shouldn't be cleaned up.
        Path("my_source.v")
        Path("apio.ini")

        # -- Create files that should be cleaned up.
        Path("zadig.ini").touch()
        Path("_build").mkdir()
        Path("_build/aaa").touch()
        Path("_build/bbb").touch()

        # -- Run clean_if_requested with no cleanup requested. It should
        # -- not add any target.
        assert len(SconsHacks.get_targets()) == 0
        apio_env.clean_if_requested()
        assert len(SconsHacks.get_targets()) == 0

        # -- Run the cleanup setup. It's expected to add a single
        # -- target with the dependencies to clean up.
        assert len(SconsHacks.get_targets()) == 0
        SetOption("clean", True)
        apio_env.clean_if_requested()
        assert len(SconsHacks.get_targets()) == 1

        # -- Get the target and its dependencies
        items_list = list(SconsHacks.get_targets().items())
        target, dependencies = items_list[0]

        # -- Verify the tartget name, hard coded in set_up_cleanup()
        assert target.name == "cleanup-target"

        # -- Verif the dependencies. These are the files to delete.
        file_names = [x.name for x in dependencies]
        assert file_names == ["aaa", "bbb", "zadig.ini", "_build"]


def test_map_params():
    """Test the map_params() method."""

    apio_env = make_test_apio_env()

    # -- Empty cases
    assert apio_env.map_params([], "x_{}_y") == ""
    assert apio_env.map_params(["", "   "], "x_{}_y") == ""

    # -- Non empty cases
    assert apio_env.map_params(["a"], "x_{}_y") == "x_a_y"
    assert apio_env.map_params([" a "], "x_{}_y") == "x_a_y"
    assert (
        apio_env.map_params(["a", "a", "b"], "x_{}_y") == "x_a_y x_a_y x_b_y"
    )


def test_targeting():
    """Test the targeting() method."""

    # -- The test env targets 'build'.
    apio_env = make_test_apio_env()

    assert apio_env.targeting("build")
    assert not apio_env.targeting("upload")


def test_log_methods(capsys: LogCaptureFixture):
    """Tests the log methods method."""

    # -- Create the scons env.
    apio_env = make_test_apio_env()

    # -- Test msg()
    apio_env.msg("My msg")
    captured = capsys.readouterr()
    assert "My msg\n" == captured.out

    # -- Test info()
    apio_env.info("My info")
    captured = capsys.readouterr()
    assert "Info: My info\n" == captured.out

    # -- Test warning()
    apio_env.warning("My warning")
    captured = capsys.readouterr()
    assert "\x1b[33mWarning: My warning\x1b[0m\n" == captured.out

    # -- Test error()
    apio_env.error("My error")
    captured = capsys.readouterr()
    assert "\x1b[31mError: My error\x1b[0m\n" == captured.out

    # -- Test fatal_error()
    with pytest.raises(SystemExit) as exp:
        apio_env.fatal_error("My fatal error")
    assert exp.value.code == 1
    captured = capsys.readouterr()
    assert "\x1b[31mError: My fatal error\x1b[0m\n" == captured.out


def test_get_constraint_file(
    capsys: LogCaptureFixture, apio_runner: ApioRunner
):
    """Test the get_constraint_file() method."""

    with apio_runner.in_sandbox():

        apio_env = make_test_apio_env()

        # -- If not .pcf files, should assume main name + extension and
        # -- inform the user about it.
        capsys.readouterr()  # Reset capture
        result = apio_env.get_constraint_file(".pcf", "my_main")
        captured = capsys.readouterr()
        assert "assuming 'my_main.pcf'" in captured.out
        assert result == "my_main.pcf"

        # -- If a single .pcf file, return it.
        Path("pinout.pcf").touch()
        result = apio_env.get_constraint_file(".pcf", "my_main")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert result == "pinout.pcf"

        # -- If thre is more than one, exit with an error message.
        Path("other.pcf").touch()
        capsys.readouterr()  # Reset capture
        with pytest.raises(SystemExit) as e:
            result = apio_env.get_constraint_file(".pcf", "my_main")
        captured = capsys.readouterr()
        assert e.value.code == 1
        assert "Error: Found multiple '*.pcf'" in captured.out


def test_get_programmer_cmd(capsys: LogCaptureFixture):
    """Tests the method get_programmer_cmd()."""

    # -- Without a "prog" arg, expected to return "". This is the case
    # -- when scons handles a command that doesn't use the programmer.
    apio_env = make_test_apio_env()
    assert apio_env.programmer_cmd() == ""

    # -- If prog is specified, expected to return it.
    apio_env = make_test_apio_env(extra_args={"prog": "my_prog aa $SOURCE bb"})
    assert apio_env.programmer_cmd() == "my_prog aa $SOURCE bb"

    # -- If prog string doesn't contains $SOURCE, expected to exit with an
    # -- error message.
    apio_env = make_test_apio_env(extra_args={"prog": "my_prog aa SOURCE bb"})
    with pytest.raises(SystemExit) as e:
        capsys.readouterr()  # Reset capturing.
        apio_env.programmer_cmd()
    captured = capsys.readouterr()
    assert e.value.code == 1
    assert "does not contain the '$SOURCE'" in captured.out


def test_make_verilator_config_builder(apio_runner: ApioRunner):
    """Tests the make_verilator_config_builder() method."""

    with apio_runner.in_sandbox() as sb:

        # -- Create a test scons env.
        apio_env = make_test_apio_env()

        # -- Call the tested method to create a builder.
        builder = apio_env.make_verilator_config_builder("test-text")

        # -- Verify builder suffixes.
        assert builder.suffix == ".vlt"
        assert builder.src_suffix == []

        # -- Create a target that doesn't exist yet.
        assert not exists("hardware.vlt")
        target = FS.File(FS(), "hardware.vlt")

        # -- Invoke the builder's action to create the target.
        builder.action(target, [], apio_env.env)
        assert isfile("hardware.vlt")

        # -- Verify that the file was created with the tiven text.
        text = sb.read_file("hardware.vlt")

        assert text == "test-text"


def test_get_source_files(apio_runner):
    """Tests the get_source_files() method."""

    with apio_runner.in_sandbox():

        # -- Create a test scons env.
        apio_env = make_test_apio_env()

        # -- Make files verilog src names (out of order)
        Path("bbb.v").touch()
        Path("aaa.v").touch()

        # -- Make files with testbench names (out of order)
        Path("ccc_tb.v").touch()
        Path("aaa_tb.v").touch()

        # -- Make files with non related names.
        Path("ddd.vh").touch()
        Path("eee.vlt").touch()
        Path("subdir").mkdir()
        Path("subdir/eee.v").touch()

        # -- Invoked the tested method.
        srcs, testbenches = apio_env.source_files()

        # -- Verify results.
        assert srcs == ["aaa.v", "bbb.v"]
        assert testbenches == ["aaa_tb.v", "ccc_tb.v"]


def test_vlt_path():
    """Tests the vlt_path path string mapping."""

    apio_env = make_test_apio_env()

    assert apio_env.vlt_path("") == ""
    assert apio_env.vlt_path("/aa/bb/cc.xyz") == "/aa/bb/cc.xyz"
    assert apio_env.vlt_path("C:\\aa\\bb/cc.xyz") == "C:/aa/bb/cc.xyz"
