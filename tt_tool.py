#!/usr/bin/env python3
import argparse
import logging

from project import Project
from project_checks import check_project_docs
from tech import TechName
from tt_logging import setup_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TT setup")
    parser.add_argument("--project-dir", help="location of the project", default=".")
    parser.add_argument(
        "--yaml", help="the project's yaml configuration file", default="info.yaml"
    )
    parser.add_argument(
        "--debug",
        help="debug logging",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    parser.add_argument(
        "--ihp",
        help="use IHP PDK",
        action="store_const",
        const=True,
        default=False,
    )
    parser.add_argument(
        "--gf",
        help="use gf180mcuD PDK",
        action="store_const",
        const=True,
        default=False,
    )

    # reports & summaries
    parser.add_argument(
        "--print-cell-summary",
        help="print summary",
        action="store_const",
        const=True,
        default=False,
    )
    parser.add_argument(
        "--print-cell-category",
        help="print category",
        action="store_const",
        const=True,
        default=False,
    )
    parser.add_argument(
        "--print-stats",
        help="print some stats from the run",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--print-warnings", help="print any warnings", action="store_const", const=True
    )
    parser.add_argument(
        "--print-wokwi-id",
        help="prints the Wokwi project id",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--print-top-module",
        help="prints the name of the top module",
        action="store_const",
        const=True,
    )

    # documentation
    parser.add_argument(
        "--check-docs",
        help="check the documentation part of the yaml",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--create-pdf",
        help="create a datasheet for the current project",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--template-version",
        help="set typst template version (default 1.0.0)",
        default="1.0.0",
        nargs="?",
    )
    parser.add_argument(
        "--create-svg",
        help="create a svg of the GDS layout",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--create-png",
        help="create a png of the GDS layout",
        action="store_const",
        const=True,
    )

    # Hardening and submission
    parser.add_argument(
        "--create-user-config",
        help="create the user_config.json file with top module and source files",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--harden",
        help="use a local LibreLane install to harden the project",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--create-tt-submission",
        help="Copy the hardened design to the tt_submission directory",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--open-in-klayout",
        help="open the hardened design in KLayout",
        action="store_const",
        const=True,
    )
    parser.add_argument(
        "--open-in-openroad",
        help="open the hardened design in OpenROAD",
        action="store_const",
        const=True,
    )

    args = parser.parse_args()

    setup_logging(args.loglevel)

    pdk: TechName = "ihp-sg13g2" if args.ihp else "gf180mcuD" if args.gf else "sky130A"

    if args.check_docs:
        check_project_docs(args.project_dir, pdk)

    project = Project(0, "unknown", args.project_dir, pdk, is_user_project=True)
    project.post_clone_setup()

    if args.print_cell_summary or args.print_cell_category:
        project.summarize(
            print_cell_category=args.print_cell_category,
            print_cell_summary=args.print_cell_summary,
        )

    if args.print_stats:
        project.print_stats()

    if args.print_warnings:
        project.print_warnings()

    if args.print_wokwi_id:
        project.print_wokwi_id()

    if args.print_top_module:
        project.print_top_module()

    if args.create_user_config:
        project.create_user_config()

    if args.harden:
        project.harden()

    if args.create_tt_submission:
        project.create_tt_submission()

    if args.open_in_klayout:
        project.run_custom_librelane_flow("OpenInKLayout")

    if args.open_in_openroad:
        project.run_custom_librelane_flow("OpenInOpenROAD")

    if args.create_pdf:
        project.create_project_datasheet(args.template_version)

    if args.create_png:
        project.create_png()

    if args.create_svg:
        project.create_svg()
