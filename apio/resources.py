"""Resources module"""

# -*- coding: utf-8 -*-
# -- This file is part of the Apio project
# -- (C) 2016-2019 FPGAwars
# -- Author Jesús Arroyo
# -- Licence GPLv2

import sys
import json
from collections import OrderedDict
import shutil
import click

from apio import util
from apio.profile import Profile

# -- Info message
BOARDS_MSG = (
    """
Use `apio init --board <boardname>` to create a new apio """
    """project for that board"""
)

# ---------- RESOURCES
RESOURCES_DIR = "resources"
# ---------------------------------------
# ---- File: resources/packages.json
# --------------------------------------
# -- This file contains all the information regarding the available apio
# -- packages: Repository, version, name...
# -- This information is access through the Resources.packages method
PACKAGES_JSON = "packages.json"

# -----------------------------------------
# ---- File: resources/boads.json
# -----------------------------------------
# -- Information about all the supported boards
# -- names, fpga family, programmer, ftdi description, vendor id, product id
BOARDS_JSON = "boards.json"

# -----------------------------------------
# ---- File: resources/fpgas.json
# -----------------------------------------
# -- Information about all the supported fpgas
# -- arch, type, size, packaging
FPGAS_JSON = "fpgas.json"

# -----------------------------------------
# ---- File: resources/programmers.json
# -----------------------------------------
# -- Information about all the supported programmers
# -- name, command to execute, arguments...
PROGRAMMERS_JSON = "programmers.json"

# -----------------------------------------
# ---- File: resources/distribution.json
# -----------------------------------------
# -- Information about all the supported apio and pip packages
DISTRIBUTION_JSON = "distribution.json"


class Resources:
    """Resource manager. Class for accesing to all the resources"""

    def __init__(self, platform: str = ""):

        # -- Read the apio packages information
        self.packages = self._load_resource(PACKAGES_JSON)

        # -- Read the boards information
        self.boards = self._load_resource(BOARDS_JSON)

        # -- Read the FPGAs information
        self.fpgas = self._load_resource(FPGAS_JSON)

        # -- Read the programmers information
        self.programmers = self._load_resource(PROGRAMMERS_JSON)

        # -- Read the distribution information
        self.distribution = self._load_resource(DISTRIBUTION_JSON)

        # Check available packages
        self.packages = self._check_packages(self.packages, platform)

        # ---------  Sort resources
        self.packages = OrderedDict(
            sorted(self.packages.items(), key=lambda t: t[0])
        )

        self.boards = OrderedDict(
            sorted(self.boards.items(), key=lambda t: t[0])
        )
        self.fpgas = OrderedDict(
            sorted(self.fpgas.items(), key=lambda t: t[0])
        )

        # -- Default profile file
        self.profile = None

    @staticmethod
    def _load_resource(name: str) -> dict:
        """Load the resources from a given json file
        * INPUTS:
          * Name: Name of the json file
            Use the following constants:
              * PACKAGES_JSON
              * BOARD_JSON
              * FPGAS_JSON
              * PROGRAMMERS_JSON
              * DISTRIBUTION_JSON
        * OUTPUT: The dicctionary with the data
          In case of error it raises an exception and finish
        """

        # -- Build the filepath: Ex. resources/fpgas.json
        filepath = util.get_full_path(RESOURCES_DIR) / name

        # -- Read the json file
        try:
            with filepath.open(encoding="utf8") as file:

                # -- Read the json file
                data_json = file.read()

        # -- json file NOT FOUND! This is an apio system error
        # -- It should never ocurr unless there is a bug in the
        # -- apio system files, or a bug when calling this function
        # -- passing a wrong file
        except FileNotFoundError as exc:

            # -- Display Main error
            click.secho("Apio System Error! JSON file not found", fg="red")

            # -- Display the affected file (in a different color)
            apio_file_msg = click.style("Apio file: ", fg="yellow")
            filename = click.style(f"{filepath}", fg="blue")
            click.secho(f"{apio_file_msg} {filename}")

            # -- Display the specific error message
            click.secho(f"{exc}\n", fg="red")

            # -- Abort!
            sys.exit(2)

        # -- Parse the json format!
        try:
            resource = json.loads(data_json)

        # -- Invalid json format! This is an apio system error
        # -- It should never ocurr unless some develeper has
        # -- made a mistake when changing the json file
        except json.decoder.JSONDecodeError as exc:

            # -- Display Main error
            click.secho("Apio System Error! Invalid JSON file", fg="red")

            # -- Display the affected file (in a different color)
            apio_file_msg = click.style("Apio file: ", fg="yellow")
            filename = click.style(f"{filepath}", fg="blue")
            click.secho(f"{apio_file_msg} {filename}")

            # -- Display the specific error message
            click.secho(f"{exc}\n", fg="red")

            # -- Abort!
            sys.exit(1)

        # -- Return the object for the resource
        return resource

    def get_package_release_name(self, package):
        """DOC: TODO"""

        return self.packages.get(package).get("release").get("package_name")

    def get_packages(self):
        """DOC: TODO"""

        # Classify packages
        installed_packages = []
        notinstalled_packages = []

        for package in self.packages:
            data = {
                "name": package,
                "version": None,
                "description": self.packages.get(package).get("description"),
            }
            if package in self.profile.packages:
                data["version"] = self.profile.get_package_version(
                    package, self.get_package_release_name(package)
                )
                installed_packages += [data]
            else:
                notinstalled_packages += [data]

        for package in self.profile.packages:
            if package not in self.packages:
                data = {
                    "name": package,
                    "version": "Unknown",
                    "description": "Unknown deprecated package",
                }
                installed_packages += [data]

        return installed_packages, notinstalled_packages

    def list_packages(self, installed=True, notinstalled=True):
        """Return a list with all the installed/notinstalled packages"""

        self.profile = Profile()

        # Classify packages
        installed_packages, notinstalled_packages = self.get_packages()

        # Print tables
        terminal_width, _ = shutil.get_terminal_size()

        if installed and installed_packages:
            # - Print installed packages table
            click.echo("\nInstalled packages:\n")

            package_list_tpl = "{name:20} {description:30} {version:<8}"

            click.echo("-" * terminal_width)
            click.echo(
                package_list_tpl.format(
                    name=click.style("Name", fg="cyan"),
                    version="Version",
                    description="Description",
                )
            )
            click.echo("-" * terminal_width)

            for package in installed_packages:
                click.echo(
                    package_list_tpl.format(
                        name=click.style(package.get("name"), fg="cyan"),
                        version=package.get("version"),
                        description=package.get("description"),
                    )
                )

        if notinstalled and notinstalled_packages:
            # - Print not installed packages table
            click.echo("\nNot installed packages:\n")

            package_list_tpl = "{name:20} {description:30}"

            click.echo("-" * terminal_width)
            click.echo(
                package_list_tpl.format(
                    name=click.style("Name", fg="yellow"),
                    description="Description",
                )
            )
            click.echo("-" * terminal_width)

            for package in notinstalled_packages:
                click.echo(
                    package_list_tpl.format(
                        name=click.style(package.get("name"), fg="yellow"),
                        description=package.get("description"),
                    )
                )

        click.echo("\n")

    def list_boards(self):
        """Return a list with all the supported boards"""

        # Print table
        click.echo("\nSupported boards:\n")

        board_list_tpl = (
            "{board:25} {fpga:30} {arch:<8} "
            + "{type:<12} {size:<5} {pack:<10}"
        )
        terminal_width, _ = shutil.get_terminal_size()

        click.echo("-" * terminal_width)
        click.echo(
            board_list_tpl.format(
                board=click.style("Board", fg="cyan"),
                fpga="FPGA",
                arch="Arch",
                type="Type",
                size="Size",
                pack="Pack",
            )
        )
        click.echo("-" * terminal_width)

        for board in self.boards:
            fpga = self.boards.get(board).get("fpga")
            click.echo(
                board_list_tpl.format(
                    board=click.style(board, fg="cyan"),
                    fpga=fpga,
                    arch=self.fpgas.get(fpga).get("arch"),
                    type=self.fpgas.get(fpga).get("type"),
                    size=self.fpgas.get(fpga).get("size"),
                    pack=self.fpgas.get(fpga).get("pack"),
                )
            )

        click.secho(BOARDS_MSG, fg="green")

    def list_fpgas(self):
        """Return a list with all the supported FPGAs"""

        # Print table
        click.echo("\nSupported FPGAs:\n")

        fpga_list_tpl = "{fpga:40} {arch:<8} {type:<12} {size:<5} {pack:<10}"
        terminal_width, _ = shutil.get_terminal_size()

        click.echo("-" * terminal_width)
        click.echo(
            fpga_list_tpl.format(
                fpga=click.style("FPGA", fg="cyan"),
                type="Type",
                arch="Arch",
                size="Size",
                pack="Pack",
            )
        )
        click.echo("-" * terminal_width)

        for fpga in self.fpgas:
            click.echo(
                fpga_list_tpl.format(
                    fpga=click.style(fpga, fg="cyan"),
                    arch=self.fpgas.get(fpga).get("arch"),
                    type=self.fpgas.get(fpga).get("type"),
                    size=self.fpgas.get(fpga).get("size"),
                    pack=self.fpgas.get(fpga).get("pack"),
                )
            )

    @staticmethod
    def _check_packages(packages, given_platform) -> dict:
        """Filter the apio packages available for the given platform.
        Some platforms has special packages (Ex. package Drivers is
        only for windows)
        * INPUT:
          * packages: All the apio packages
          * given_platform: Platform used for filtering the packages.
              If not given,the current system platform is used
        * OUTPUT: It returns only the packages available for the
            given platform
        """

        # -- Final dict with the output packages
        filtered_packages = {}

        # -- If not given platform, use the current
        if not given_platform:
            given_platform = util.get_systype()

        # -- Check all the packages
        for pkg in packages.keys():

            # -- Get the information about the package
            release = packages[pkg]["release"]

            # -- This packages is available only for certain platforms
            if "available_platforms" in release:

                # -- Get the available platforms
                platforms = release["available_platforms"]

                # -- Check all the available platforms
                for platform in platforms:

                    # -- Match!
                    if given_platform in platform:

                        # -- Add it to the output dictionary
                        filtered_packages[pkg] = packages[pkg]

            # -- Package for all the platforms
            else:

                # -- Add it to the output dictionary
                filtered_packages[pkg] = packages[pkg]

        # -- Return the filtered packages
        return filtered_packages
