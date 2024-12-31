"""Scons script of ECP5 FPGAs."""

# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2024 FPGAwars
# -- Authors Juan Gonzáles, Jesús Arroyo
# -- Licence GPLv2

# pylint: disable=too-many-locals
# pylint: disable=invalid-name
# pylint: disable=consider-using-f-string
# pylint: disable=too-many-statements
# pylint: disable=fixme

# -- Similar lines
# pylint: disable= R0801

import os
from SCons.Script import (
    Builder,
    GetOption,
    COMMAND_LINE_TARGETS,
    ARGUMENTS,
)
from apio.scons.apio_env import (
    ApioEnv,
    unused,
    TARGET,
    SconsArch,
    BUILD_DIR,
)


def scons_handler():
    """Scons handler for ecp5."""

    # -- Create the apio environment.
    apio_env = ApioEnv(SconsArch.ECP5, ARGUMENTS)

    # -- Parse scons arguments.
    FPGA_TYPE = apio_env.arg_str("fpga_type", "")
    FPGA_PACK = apio_env.arg_str("fpga_pack", "")
    TOP_MODULE = apio_env.arg_str("top_module", "")
    FPGA_IDCODE = apio_env.arg_str("fpga_idcode", "")
    VERBOSE_ALL = apio_env.arg_bool("verbose_all", False)
    VERBOSE_YOSYS = apio_env.arg_bool("verbose_yosys", False)
    VERBOSE_PNR = apio_env.arg_bool("verbose_pnr", False)
    TESTBENCH = apio_env.arg_str("testbench", "")
    FORCE_SIM = apio_env.arg_bool("force_sim", False)
    VERILATOR_ALL = apio_env.arg_bool("all", False)
    VERILATOR_NO_STYLE = apio_env.arg_bool("nostyle", False)
    VERILATOR_NOWARNS = apio_env.arg_str("nowarn", "").split(",")
    VERILATOR_WARNS = apio_env.arg_str("warn", "").split(",")
    GRAPH_SPEC = apio_env.arg_str("graph_spec", "")

    # -- Resources paths
    YOSYS_PATH = os.environ["YOSYS_LIB"]
    TRELLIS_PATH = os.environ["TRELLIS"]
    DATABASE_PATH = os.path.join(TRELLIS_PATH, "database")

    assert YOSYS_PATH, "Missing required env variable YOSYS_LIB"
    assert TRELLIS_PATH, "Missing required env variable TRELLIS"

    YOSYS_LIB_DIR = YOSYS_PATH + "/ecp5"
    CONSTRAIN_FILE_EXTENSION = ".lpf"

    # -- Create a source file scannenr that identifies references to other
    # -- files in verilog files. We add this to the dependency graph.
    verilog_src_scanner = apio_env.verilog_src_scanner()

    # -- Get a list of the synthesizable files (e.g. "main.v") and a list of
    # -- the testbench files (e.g. "main_tb.v")
    synth_srcs, test_srcs = apio_env.source_files()

    # -- Get the FPGA constrain file name.
    constrain_file: str = apio_env.get_constraint_file(
        CONSTRAIN_FILE_EXTENSION,
        TOP_MODULE,
    )

    # --------- Builders.

    # -- The synthesis builder.
    apio_env.builder(
        "SynthBuilder",
        Builder(
            action='yosys -p "synth_ecp5 {0} -json $TARGET" {1} '
            "$SOURCES".format(
                ("-top " + TOP_MODULE) if TOP_MODULE else "",
                "" if VERBOSE_ALL or VERBOSE_YOSYS else "-q",
            ),
            suffix=".json",
            src_suffix=".v",
            source_scanner=verilog_src_scanner,
        ),
    )

    # -- The name of the report file generated by nextpnr.
    PNR_REPORT_FILE: str = TARGET + ".pnr"

    def pnr_emitter(target, source, env):
        """A scons emmiter for the pnr builder. It informs scons that the
        nextpnr builder creates an additional second file called
        'hardware.pnr'."""
        unused(env)
        target.append(PNR_REPORT_FILE)
        return target, source

    # -- The place-and-route builder.
    apio_env.builder(
        "PnrBuilder",
        Builder(
            action=(
                "nextpnr-ecp5 --{0} --package {1} "
                "--json $SOURCE --textcfg $TARGET "
                "--report {2} --lpf {3} {4} --timing-allow-fail --force"
            ).format(
                # TODO: Explain why 12k -> 25k.
                # TODO: 12k looks more like size than type. Why?
                "25k" if (FPGA_TYPE == "12k") else FPGA_TYPE,
                FPGA_PACK,
                PNR_REPORT_FILE,
                constrain_file,
                "" if VERBOSE_ALL or VERBOSE_PNR else "-q",
            ),
            suffix=".config",
            src_suffix=".json",
            emitter=pnr_emitter,
        ),
    )

    # -- The bitstream builder.
    apio_env.builder(
        "BitstreamBuilder",
        Builder(
            action="ecppack --compress --db {0} {1} $SOURCE "
            "{2}/hardware.bit".format(
                DATABASE_PATH,
                "" if not FPGA_IDCODE else f"--idcode {FPGA_IDCODE}",
                BUILD_DIR,
            ),
            suffix=".bit",
            src_suffix=".config",
        ),
    )

    def iverilog_tb_generator(source, target, env, for_signature):
        """Construct the action string for the iverilog_tb_builder builder
        for a given testbench target."""
        unused(source, env, for_signature)
        # Extract testbench name from target file name.
        testbench_file = str(target[0])
        assert apio_env.has_testbench_name(testbench_file), testbench_file
        testbench_name = apio_env.basename(testbench_file)

        # Construct the actions list.
        action = [
            # -- Scan source files for issues.
            apio_env.source_file_issue_action(),
            # -- Perform the actual test or sim compilation.
            apio_env.iverilog_action(
                verbose=VERBOSE_ALL,
                vcd_output_name=testbench_name,
                is_interactive=("sim" in COMMAND_LINE_TARGETS),
                lib_dirs=[YOSYS_LIB_DIR],
            ),
        ]
        return action

    # -- The IVerilog testbench compiler builder.
    apio_env.builder(
        "IVerilogTestbenchBuilder",
        Builder(
            # Action string is different for sim and for
            generator=iverilog_tb_generator,
            suffix=".out",
            src_suffix=".v",
            source_scanner=verilog_src_scanner,
        ),
    )

    # -- The yosys .dot file (graph) builder.
    apio_env.builder(
        "YosysDotBuilder",
        apio_env.dot_builder(
            top_module=TOP_MODULE,
            verilog_src_scanner=verilog_src_scanner,
            verbose=VERBOSE_ALL,
        ),
    )

    # -- The graphviz svg/pdf/png renderer builder.
    apio_env.builder(
        "GraphvizRedererBuilder", apio_env.graphviz_builder(GRAPH_SPEC)
    )

    # -- The testbench vcd builder. These are the signals files that gtkwave
    # -- shows.
    apio_env.builder(
        "TestbenchVcdBuilder",
        Builder(
            action="vvp $SOURCE -dumpfile=$TARGET",
            suffix=".vcd",
            src_suffix=".out",
        ),
    )

    # -- The Verilator lint builder which lints the source files(s).
    apio_env.builder(
        "VerilatorLintBuilder",
        Builder(
            action=apio_env.verilator_lint_action(
                warnings_all=VERILATOR_ALL,
                warnings_no_style=VERILATOR_NO_STYLE,
                no_warns=VERILATOR_NOWARNS,
                warns=VERILATOR_WARNS,
                top_module=TOP_MODULE,
                lib_dirs=[YOSYS_LIB_DIR],
            ),
            src_suffix=".v",
            source_scanner=verilog_src_scanner,
        ),
    )

    # -- A verilator lint config builder which creates the verilator lint
    # -- rules file.
    yosys_vlt_path = apio_env.vlt_path(YOSYS_LIB_DIR)
    apio_env.builder(
        "VerilatorLintConfigBuilder",
        apio_env.make_verilator_config_builder(
            "`verilator_config\n"
            f'lint_off -rule COMBDLY     -file "{yosys_vlt_path}/*"\n'
            f'lint_off -rule WIDTHEXPAND -file "{yosys_vlt_path}/*"\n'
            f'lint_off -rule PINMISSING  -file "{yosys_vlt_path}/*"\n'
            f'lint_off -rule ASSIGNIN    -file "{yosys_vlt_path}/*"\n'
            f'lint_off -rule WIDTHTRUNC  -file "{yosys_vlt_path}/*"\n'
            f'lint_off -rule INITIALDLY  -file "{yosys_vlt_path}/*"\n'
        ),
    )

    # --------- Targets.

    # -- The "build" target and its dependencies.
    synth_target = apio_env.builder_target(
        builder_id="SynthBuilder",
        target=TARGET,
        sources=[synth_srcs],
        always_build=(VERBOSE_ALL or VERBOSE_YOSYS),
    )
    pnr_target = apio_env.builder_target(
        builder_id="PnrBuilder",
        target=TARGET,
        sources=[synth_target, constrain_file],
        always_build=(VERBOSE_ALL or VERBOSE_PNR),
    )
    bin_target = apio_env.builder_target(
        builder_id="BitstreamBuilder",
        target=TARGET,
        sources=pnr_target,
    )
    apio_env.alias(
        "build",
        source=bin_target,
        allways_build=(VERBOSE_ALL or VERBOSE_YOSYS or VERBOSE_PNR),
    )

    # -- The "report" target.
    apio_env.alias(
        "report",
        source=PNR_REPORT_FILE,
        action=apio_env.report_action(VERBOSE_PNR),
        allways_build=True,
    )

    # -- The "upload" target.
    apio_env.alias(
        "upload",
        source=bin_target,
        action=apio_env.programmer_cmd(),
        allways_build=True,
    )

    # -- The 'graph' target and its dependencies.
    dot_target = apio_env.builder_target(
        builder_id="YosysDotBuilder",
        target=TARGET,
        sources=synth_srcs,
        always_build=True,
    )
    graphviz_target = apio_env.builder_target(
        builder_id="GraphvizRedererBuilder",
        target=TARGET,
        sources=dot_target,
        always_build=True,
    )
    apio_env.alias(
        "graph",
        source=graphviz_target,
        allways_build=True,
    )

    # -- The 'sim' target and its dependencies, to simulate and display the
    # -- results of a single testbench.
    if "sim" in COMMAND_LINE_TARGETS:
        sim_config = apio_env.get_sim_config(TESTBENCH, synth_srcs)
        sim_out_target = apio_env.builder_target(
            builder_id="IVerilogTestbenchBuilder",
            target=sim_config.build_testbench_name,
            sources=sim_config.srcs,
            always_build=FORCE_SIM,
        )
        sim_vcd_target = apio_env.builder_target(
            builder_id="TestbenchVcdBuilder",
            target=sim_config.build_testbench_name,
            sources=[sim_out_target],
            always_build=FORCE_SIM,
        )
        apio_env.waves_target(
            "sim",
            sim_vcd_target,
            sim_config,
            allways_build=True,
        )

    # -- The  "test" target and its dependencies, to test one or more
    # -- testbenches.
    if "test" in COMMAND_LINE_TARGETS:
        tests_configs = apio_env.get_tests_configs(
            TESTBENCH, synth_srcs, test_srcs
        )
        tests_targets = []
        for test_config in tests_configs:
            test_out_target = apio_env.builder_target(
                builder_id="IVerilogTestbenchBuilder",
                target=test_config.build_testbench_name,
                sources=test_config.srcs,
                always_build=True,
            )

            test_vcd_target = apio_env.builder_target(
                builder_id="TestbenchVcdBuilder",
                target=test_config.build_testbench_name,
                sources=[test_out_target],
                always_build=True,
            )
            test_target = apio_env.alias(
                test_config.build_testbench_name,
                source=[test_vcd_target],
            )
            tests_targets.append(test_target)

        # -- The top 'test' target.
        apio_env.alias("test", source=tests_targets, allways_build=True)

    # -- The "lint" target and its dependencies.
    lint_config_target = apio_env.builder_target(
        builder_id="VerilatorLintConfigBuilder",
        target=TARGET,
        sources=[],
    )
    lint_out_target = apio_env.builder_target(
        builder_id="VerilatorLintBuilder",
        target=TARGET,
        sources=synth_srcs + test_srcs,
    )
    apio_env.depends(lint_out_target, lint_config_target)
    apio_env.alias(
        "lint",
        source=lint_out_target,
        allways_build=True,
    )

    # -- Handle the cleanu of the artifact files.
    if GetOption("clean"):
        apio_env.set_up_cleanup()
