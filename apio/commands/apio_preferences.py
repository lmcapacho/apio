# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2024 FPGAwars
# -- Authors
# --  * Jesús Arroyo (2016-2019)
# --  * Juan Gonzalez (obijuan) (2019-2024)
# -- Licence GPLv2
"""Implementation of 'apio preferences' command"""

import click
from click import secho, echo, style
from apio.utils import cmd_util
from apio.apio_context import ApioContext, ApioContextScope
from apio.utils.cmd_util import ApioGroup, ApioSubgroup

# ---- apio preferences list


APIO_PREFERENCES_LIST_HELP = """
The command ‘apio preferences list’ lists the current user preferences.

\b
Examples:
  apio preferences list         # List the user preferences.

  """


@click.command(
    name="list",
    short_help="List the apio user preferences.",
    help=APIO_PREFERENCES_LIST_HELP,
)
def _list_cli():
    """Implements the 'apio preferences list' command."""

    # -- Create the apio context.
    apio_ctx = ApioContext(scope=ApioContextScope.NO_PROJECT)

    # -- Print title.
    secho("Apio user preferences:", fg="magenta")

    # -- Show colors preference.
    value = apio_ctx.profile.preferences.get("colors", "on")
    styled_value = style(value, fg="cyan", bold=True)
    echo(f"Colors:   {styled_value}")


# ---- apio preferences set


APIO_PREF_SET_HELP = """
The command ‘apio preferences set' allows to set the supported user
preferences.

\b
Examples:
  apio preferences set --colors yes   # Select multi-color output.
  apio preferences set --colors no    # Select monochrome output.

The apio colors are optimized for a terminal windows with a white background.
"""

colors_options = click.option(
    "colors",  # Var name
    "-c",
    "--colors",
    required=True,
    type=click.Choice(["on", "off"], case_sensitive=True),
    help="Set/reset colors mode.",
    cls=cmd_util.ApioOption,
)


@click.command(
    name="set",
    short_help="Set the apio user preferences.",
    help=APIO_PREF_SET_HELP,
)
@colors_options
def _set_cli(colors: str):
    """Implements the 'apio preferences set' command."""

    # -- Create the apio context.
    apio_ctx = ApioContext(scope=ApioContextScope.NO_PROJECT)

    # -- Set the colors preference value.
    apio_ctx.profile.set_preferences_colors(colors)

    # -- Show the result. The new colors preference is already in effect.
    color = apio_ctx.profile.preferences["colors"]
    secho(f"Colors set to [{color}]", fg="green", bold=True)


# --- apio preferences

APIO_PREFERENCES_HELP = """
The command group ‘apio preferences' contains subcommands to manage
the apio user preferences. These are user configurations that affect all the
apio project on the same computer.

The user preference is not part of any apio project and typically are not
shared when multiple user colaborate on the same project.
"""

# -- We have only a single group with the title 'Subcommands'.
SUBGROUPS = [
    ApioSubgroup(
        "Subcommands",
        [
            _list_cli,
            _set_cli,
        ],
    )
]


@click.command(
    name="preferences",
    cls=ApioGroup,
    subgroups=SUBGROUPS,
    short_help="Manage the apio user preferences.",
    help=APIO_PREFERENCES_HELP,
)
def cli():
    """Implements the apio preferences command."""

    # pass
