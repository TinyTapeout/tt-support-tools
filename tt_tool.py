#!/usr/bin/env python3
import sys
import logging
import argparse
import documentation
import project
import reports

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TT setup")
    parser.add_argument('--yaml', help="the project's yaml configuration file", default='info.yaml')
    parser.add_argument('--run-dir', help="OpenLane run directory", default='runs/wokwi')  # set in the github action yaml
    parser.add_argument('--debug', help="debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)

    # reports & summaries
    parser.add_argument('--create-cell-defs', help="create def file", action="store_true")
    parser.add_argument('--print-cell-summary', help="print summary", action="store_true")
    parser.add_argument('--print-cell-category', help="print category", action="store_true")
    parser.add_argument('--print-stats', help="print some stats from the run", action="store_true")
    parser.add_argument('--print-warnings', help="print any warnings", action="store_true")

    # documentation
    parser.add_argument('--check-docs', help="check the documentation part of the yaml", action="store_true")
    parser.add_argument('--create-pdf', help="create a single page PDF", action="store_true")
    parser.add_argument('--create-svg', help="create a svg of the GDS layout", action="store_true")
    parser.add_argument('--create-png', help="create a png of the GDS layout", action="store_true")

    # configure
    parser.add_argument('--create-user-config', help="create the user_config.tcl file with top module and source files", action="store_true")
    parser.add_argument('--harden', help="use a local OpenLane install to harden the project", action="store_true")

    args = parser.parse_args()

    # setup log
    log_format = logging.Formatter('%(asctime)s - %(module)-10s - %(levelname)-8s - %(message)s')
    # configure the client logging
    log = logging.getLogger('')
    # has to be set to debug as is the root logger
    log.setLevel(args.loglevel)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    project_yaml = project.load_yaml(args)

    # handle the options
    if args.check_docs:
        documentation.check_yaml_docs(project_yaml)

    if args.print_cell_summary or args.print_cell_category:
        reports.summarize(args)

    if args.create_cell_defs:
        reports.create_defs(args)

    if args.print_stats:
        reports.print_stats(args)

    if args.print_warnings:
        reports.print_warnings(args)

    if args.create_user_config:
        project.create_user_config(project_yaml)

    if args.harden:
        project.harden()

    if args.create_pdf:
        documentation.create_pdf(project_yaml)

    if args.create_svg or args.create_png:
        documentation.create_svg(args)
