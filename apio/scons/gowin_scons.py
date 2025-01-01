"""Scons script of Gowin FPGAs."""

# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2024 FPGAwars
# -- Authors Juan Gonzáles, Jesús Arroyo
# -- Licence GPLv2

# pylint: disable=too-many-locals
# pylint: disable=invalid-name
# pylint: disable=consider-using-f-string
# pylint: disable=too-many-statements
# -- Similar lines
# pylint: disable= R0801

from SCons.Script import Builder
from apio.scons.apio_env import (
    ApioEnv,
    unused,
    TARGET,
    SconsArch,
)


def scons_handler(apio_env: ApioEnv):
    """Scons handler for gowin."""

    # -- Check that the env matches.
    assert apio_env.scons_arch == SconsArch.GOWIN

    # -- Keep a shortbut to the args.
    args = apio_env.args

    YOSYS_LIB_DIR = args.YOSYS_PATH + "/gowin"
    CONSTRAIN_FILE_EXTENSION = ".cst"

    # -- Create a source file scannenr that identifies references to other
    # -- files in verilog files. We add this to the dependency graph.
    verilog_src_scanner = apio_env.verilog_src_scanner()

    # -- Get a list of the synthesizable files (e.g. "main.v") and a list of
    # -- the testbench files (e.g. "main_tb.v")
    synth_srcs, test_srcs = apio_env.source_files()

    # -- Get the FPGA constrain file name.
    constrain_file: str = apio_env.get_constraint_file(
        CONSTRAIN_FILE_EXTENSION,
        args.TOP_MODULE,
    )

    # --------- Builders.

    # -- The synthesis builder.
    apio_env.builder(
        "SynthBuilder",
        Builder(
            action=(
                'yosys -p "synth_gowin {0} -json $TARGET" {1} $SOURCES'
            ).format(
                ("-top " + args.TOP_MODULE) if args.TOP_MODULE else "",
                "" if args.VERBOSE_ALL or args.VERBOSE_YOSYS else "-q",
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
                "nextpnr-himbaechel --device {0} --json $SOURCE "
                "--write $TARGET --report {1} --vopt family={2} "
                "--vopt cst={3} {4}"
            ).format(
                args.FPGA_MODEL,
                PNR_REPORT_FILE,
                args.FPGA_TYPE,
                constrain_file,
                "" if args.VERBOSE_ALL or args.VERBOSE_PNR else "-q",
            ),
            suffix=".pnr.json",
            src_suffix=".json",
            emitter=pnr_emitter,
        ),
    )

    # -- The bitstream builder.
    apio_env.builder(
        "BitstreamBuilder",
        Builder(
            action="gowin_pack -d {0} -o $TARGET $SOURCE".format(
                args.FPGA_TYPE.upper()
            ),
            suffix=".fs",
            src_suffix=".pnr.json",
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
                verbose=args.VERBOSE_ALL,
                vcd_output_name=testbench_name,
                is_interactive=apio_env.targeting("sim"),
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
            top_module=args.TOP_MODULE,
            verilog_src_scanner=verilog_src_scanner,
            verbose=args.VERBOSE_ALL,
        ),
    )

    # -- The graphviz svg/pdf/png renderer builder.
    apio_env.builder(
        "GraphvizRedererBuilder",
        apio_env.graphviz_builder(args.GRAPH_SPEC),
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
                warnings_all=args.VERILATOR_ALL,
                warnings_no_style=args.VERILATOR_NO_STYLE,
                no_warns=args.VERILATOR_NOWARNS,
                warns=args.VERILATOR_WARNS,
                top_module=args.TOP_MODULE,
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
        ),
    )

    # --------- Targets.

    # -- The "build" target and its dependencies.
    synth_target = apio_env.builder_target(
        builder_id="SynthBuilder",
        target=TARGET,
        sources=[synth_srcs],
        always_build=(args.VERBOSE_ALL or args.VERBOSE_YOSYS),
    )
    pnr_target = apio_env.builder_target(
        builder_id="PnrBuilder",
        target=TARGET,
        sources=[synth_target, constrain_file],
        always_build=(args.VERBOSE_ALL or args.VERBOSE_PNR),
    )
    bin_target = apio_env.builder_target(
        builder_id="BitstreamBuilder",
        target=TARGET,
        sources=pnr_target,
    )
    apio_env.alias(
        "build",
        source=bin_target,
        allways_build=(
            args.VERBOSE_ALL or args.VERBOSE_YOSYS or args.VERBOSE_PNR
        ),
    )

    # -- The "report" target.
    apio_env.alias(
        "report",
        source=PNR_REPORT_FILE,
        action=apio_env.report_action(args.VERBOSE_PNR),
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
    if apio_env.targeting("sim"):
        sim_config = apio_env.get_sim_config(args.TESTBENCH, synth_srcs)
        sim_out_target = apio_env.builder_target(
            builder_id="IVerilogTestbenchBuilder",
            target=sim_config.build_testbench_name,
            sources=sim_config.srcs,
            always_build=args.FORCE_SIM,
        )
        sim_vcd_target = apio_env.builder_target(
            builder_id="TestbenchVcdBuilder",
            target=sim_config.build_testbench_name,
            sources=[sim_out_target],
            always_build=args.FORCE_SIM,
        )
        apio_env.waves_target(
            "sim",
            sim_vcd_target,
            sim_config,
            allways_build=True,
        )

    # -- The  "test" target and its dependencies, to test one or more
    # -- testbenches.
    if apio_env.targeting("test"):
        tests_configs = apio_env.get_tests_configs(
            args.TESTBENCH, synth_srcs, test_srcs
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
    apio_env.clean_if_requested()
