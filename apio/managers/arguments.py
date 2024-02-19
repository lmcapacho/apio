# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2019 FPGAwars
# -- Author Jesús Arroyo
# -- Licence GPLv2
"""TODO"""

from functools import wraps

import click
from apio.managers.project import Project

# -- Class for accesing api resources (boards, fpgas...)
from apio.resources import Resources


# ----- Constant for accesing dicctionaries
BOARD = "board"  # -- Key for the board name
FPGA = "fpga"  # -- Key for the fpga
ARCH = "arch"  # -- Key for the FPGA Architecture
TYPE = "type"  # -- Key for the FPGA Type
SIZE = "size"  # -- Key for the FPGA size
PACK = "pack"  # -- Key for the FPGA pack
IDCODE = "idcode"  # -- Key for the FPGA IDCODE


def debug_params(fun):
    """DEBUG. Use it as a decorator. It prints the received arguments
    and the return value
    INPUTS:
      * fun: Function to DEBUG
    """

    @wraps(fun)
    def outer(*args):

        # -- Print the arguments
        print(f"--> DEBUG!. Function {fun.__name__}(). BEGIN")
        print("    * Arguments:")
        for arg in args:

            # -- Print all the key,values if it is a dictionary
            if isinstance(arg, dict):
                print("        * Dict:")
                for key, value in arg.items():
                    print(f"          * {key}: {value}")

            # -- Print the plain argument if it is not a dicctionary
            else:
                print(f"        * {arg}")
        print()

        # -- Call the function
        result = fun(*args)

        # -- Print its output
        print(f"--> DEBUG!. Function {fun.__name__}(). END")
        print("     Returns: ")

        # -- The return object always is a tuple
        if isinstance(result, tuple):

            # -- Print all the values in the tuple
            for value in result:
                print(f"      * {value}")

        # -- But just in case it is not a tuple (because of an error...)
        else:
            print(f"      * No tuple: {result}")
        print()

        return result

    return outer


@debug_params
def process_arguments(
    config_ini: dict, resources: type[Resources]
) -> tuple:  # noqa
    """Get the final CONFIGURATION, depending on the board and
    arguments passed in the command line.
    The config_ini parameter has higher priority. If not specified,
    they are read from the Project file (apio.ini)
    * INPUTS:
       * config_ini: Dictionary with the initial configuration:
         {
           'board': str,  //-- Board name
           'fpga': str,   //-- FPGA name
           'size': str,   //-- FPGA size
           'type': str,   //-- FPGA type
           'pack': str,   //-- FPGA packaging
           'verbose': dict  //-- Verbose level
           'top-module`: str  //-- Top module name
         }
       * Resources: Object for accessing the apio resources
    * OUTPUT:
      * Return a tuple (flags, board, arch)
        - flags: A list of strings with the flags valures:
          ['fpga_arch=ice40', 'fpga_size=8k', 'fpga_type=hx',
          fpga_pack='tq144:4k']...
        - board: Board name ('alhambra-ii', 'icezum'...)
        - arch: FPGA architecture ('ice40', 'ecp5'...)
    """

    # -- Current configuration
    # -- Initially it is the default project configuration
    config = {
        BOARD: None,
        FPGA: None,
        ARCH: None,
        TYPE: None,
        SIZE: None,
        PACK: None,
        IDCODE: None,
        "verbose": None,
        "top-module": None,
    }

    # -- Merge the initial configuration to the current configuration
    config.update(config_ini)

    # -- Read the apio project file (apio.ini)
    proj = Project()
    proj.read()

    # -- proj.board:
    # --   * None: No apio.ini file
    # --   * "name": Board name (str)

    # -- DEBUG: Print both: project board and configuration board
    debug_config_item(config, BOARD, proj.board)

    # -- Board name given in the command line
    if config[BOARD]:

        # -- If there is a project file (apio.ini) the board
        # -- give by command line overrides it
        # -- (command line has the highest priority)
        if proj.board:

            # -- As the command line has more priority, and the board
            # -- given in args is different than the one in the project,
            # -- inform the user
            if config[BOARD] != proj.board:
                click.secho("Info: ignore apio.ini board", fg="yellow")

    # -- Board name given in the project file
    else:
        # -- ...read it from the apio.ini file
        config[BOARD] = proj.board

    # -- The board is given (either by argumetns or by project)
    if config[BOARD]:

        # -- First, check if the board is valid
        # -- If not, exit
        if config[BOARD] not in resources.boards:
            raise ValueError(f"unknown board: {config[BOARD]}")

        # -- Read the FPGA name for the current board
        fpga = resources.boards.get(config[BOARD]).get(FPGA)

        # -- Add it to the current configuration
        update_config_item(config, FPGA, fpga)

        # -- Check if the FPGA is valid
        # -- If not, exit
        if fpga not in resources.fpgas:
            raise ValueError(f"unknown FPGA: {config[FPGA]}")

        # -- Debug
        update_config_fpga_item(config, ARCH, resources)
        update_config_fpga_item(config, TYPE, resources)
        update_config_fpga_item(config, SIZE, resources)
        update_config_fpga_item(config, PACK, resources)
        update_config_fpga_item(config, IDCODE, resources)

    # -- Debug
    print(f"(Debug) ---> Board: {config[BOARD]}")
    print(f"(Debug) ---> FPGA: {config[FPGA]}")
    print(f"(Debug) ---> FPGA ARCH: {config[ARCH]}")
    print(f"(Debug) ---> FPGA TYPE: {config[TYPE]}")
    print(f"(Debug) ---> FPGA SIZE: {config[SIZE]}")
    print(f"(Debug) ---> FPGA PACK: {config[PACK]}")
    print(f"(Debug) ---> FPGA IDCODE: {config[IDCODE]}")

    # -- Check the current config
    # -- At least it should have arch, type, size and pack
    if not config[FPGA]:
        raise ValueError("Missing FPGA")

    # if not config[ARCH]:
    #    raise ValueError("Missing FPGA architecture")

    if not config[TYPE]:
        raise ValueError("Missing FPGA type")

    if not config[SIZE]:
        raise ValueError("Missing FPGA size")

    if not config[PACK]:
        raise ValueError("Missing FPGA packaging")

    # -- Debug: Store arguments in local variables
    var_verbose = config["verbose"]
    var_topmodule = config["top-module"]

    print(f"DEBUG!!!! TOP-MODULE: {var_topmodule}")

    # click.secho(
    #       "Error: insufficient arguments: missing board",
    #       fg="red",
    #   )
    #   click.secho(
    #       "You have two options:\n"
    #       + "  1) Execute your command with\n"
    #       + "       `--board <boardname>`\n"
    #       + "  2) Create an ini file using\n"
    #       + "       `apio init --board <boardname>`",
    #       fg="yellow",
    #   )
    #   raise ValueError("Missing board")

    # -- Build Scons variables list
    variables = format_vars(
        {
            "fpga_arch": config[ARCH],
            "fpga_size": config[SIZE],
            "fpga_type": config[TYPE],
            "fpga_pack": config[PACK],
            "fpga_idcode": config[IDCODE],
            "verbose_all": var_verbose.get("all"),
            "verbose_yosys": var_verbose.get("yosys"),
            "verbose_pnr": var_verbose.get("pnr"),
            "top_module": var_topmodule,
        }
    )

    return variables, config[BOARD], config[ARCH]


def update_config_fpga_item(config, item, resources):
    """Update an item for the current FPGA configuration, if there is no
    contradiction.
    It raises an exception in case of contradiction: the current FPGA item
    in the configuration has already a value, but another has been specified
    * INPUTS:
      * Config: Current configuration
      * item: FPGA item to update: ARCH, TYPE, SIZE, PACK, IDCODE
      * value: New valur for the FPGA item, if there is no contradiction
    """

    # -- Read the FPGA item from the apio resources
    fpga_item = resources.fpgas.get(config[FPGA]).get(item)

    # -- Update the current configuration with that item
    # -- and check that there are no contradictions
    update_config_item(config, item, fpga_item)


def update_config_item(config: dict, item: str, value: str) -> None:
    """Update the value of the configuration item, if there is no contradiction
    It raises an exception in case of contradiction: the current item in the
    configuration has one value (ex. size='1k') but another has been specified
    * INPUTS:
      * Config: Current configuration
      * item: Item to update (key): BOARD, ARCH,TYPE, SIZE...
      * value: New value for the item, if there are no contradictions
    """

    # -- Debug messages
    debug_config_item(config, item, value)

    # -- This item has not been set in the current configuration: ok, set it!
    if config[item] is None:
        config[item] = value

    # -- That item already has a value... and another difffernt is being
    # -- given.. This is a contradiction!!!
    else:
        # -- It is a contradiction if their names are different
        # -- When the name is the same, it is redundant...
        # -- but it is not a problem
        if value != config[item]:
            raise ValueError(f"contradictory arguments: {value, config[item]}")


def debug_config_item(config: dict, item: str, value: str) -> None:
    """Print a Debug message related to the project configuration
    INPUTS:
      * config: Current configuration
      * item: item name to print. It is a key of the configuration:
        BOARD, ARCH, TYPE, SIZE, PACK, IDCODE....
      * Value: Value of that item specified in the project
    """
    print(f"(Debug): {item}, Project: {value}, Argument: {config[item]}")


def format_vars(args):
    """Format the given vars in the form: 'flag=value'"""
    variables = []
    for key, value in args.items():
        if value:
            variables += [f"{key}={value}"]
    return variables
