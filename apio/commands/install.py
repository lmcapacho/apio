# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2019 FPGAwars
# -- Author Jesús Arroyo
# -- Licence GPLv2
"""Main implementation of APIO INSTALL command"""

import click
from apio.managers.installer import Installer
from apio.resources import Resources
from apio import util


def install_packages(packages: list, platform: str, force: bool):
    """Install the apio packages passed as a list
    * INPUTS:
      - packages: List of packages (Ex. ['examples', 'oss-cad-suite'])
      - platform: Specific platform (Advanced, just for developers)
      - force: Force package installation
    """
    # -- Install packages, one by one...
    for package in packages:

        # -- The instalation is performed by the Installer object
        inst = Installer(package, platform, force)

        # -- Install the package!
        inst.install()


@click.command("install", context_settings=util.context_settings())
@click.pass_context
@click.argument("packages", nargs=-1)
@click.option("-a", "--all", is_flag=True, help="Install all packages.")
@click.option(
    "-l", "--list", is_flag=True, help="List all available packages."
)
@click.option(
    "-f", "--force", is_flag=True, help="Force the packages installation."
)
@click.option(
    "-p",
    "--platform",
    type=click.Choice(util.PLATFORMS),
    metavar="",
    help=(
        f"Set the platform [{', '.join(util.PLATFORMS)}] "
        "(Advanced, for developers)."
    ),
)
def cli(ctx, **kwargs):
    """Install apio packages."""

    # -- Extract the arguments
    packages = kwargs["packages"]  # -- tuple
    platform = kwargs["platform"]  # -- str
    _all = kwargs["all"]  # -- bool
    _list = kwargs["list"]  # -- bool
    force = kwargs["force"]  # -- bool

    # -- Install the given apio packages
    if packages:
        install_packages(packages, platform, force)

    # -- Install all the available packages
    elif _all:

        # -- Get all the resources
        resources = Resources(platform)

        # -- Install all the available packages for this platform!
        install_packages(resources.packages, platform, force)

    # -- List all the packages (installed or not)
    elif _list:
        # -- Get all the resources
        resources = Resources(platform)

        # -- List the packages
        resources.list_packages()

    # -- Invalid option. Just show the help
    else:
        click.secho(ctx.get_help())
