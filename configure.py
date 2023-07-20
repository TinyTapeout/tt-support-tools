#!/usr/bin/env python3
import datetime
import yaml
import json
import argparse, logging, sys, os, collections
from project import Project
from documentation import Docs
from caravel import CaravelConfig
from rom import ROMFile


# pipe handling
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)


class Projects():

    def __init__(self, config, args):
        self.args = args
        self.config = config

        if args.test:
            self.project_dir = config['test_project_dir']
        else:
            self.project_dir = config['project_dir']

        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

        self.projects = []
        project_list = [entry for entry in os.listdir(self.project_dir) if os.path.join(self.project_dir, entry)]
        if args.sta_projects:
            project_list = ['tt_um_loopback']

        for index, project_id in enumerate(project_list):
            project_dir = os.path.join(self.project_dir, project_id)

            commit_id_file = os.path.join(project_dir, 'commit_id.json')
            if not os.path.exists(commit_id_file):
                logging.warning(f"no commit_id.json in {project_dir}, skipping")
                continue

            commit_id_data = json.load(open(commit_id_file))

            project = Project(index, commit_id_data['repo'], project_dir, args)

            # projects should now be installed, so load all the data from the yaml files
            # fill projects will load from the fill project's directory
            logging.debug("post clone setup")
            project.post_clone_setup()
            logging.debug(project)

            if args.harden:
                project.create_user_config()
                project.golden_harden()

            if args.update_caravel:
                project.check_ports()
                project.check_num_cells()

            self.projects.append(project)

        all_macro_instances = [project.get_macro_instance() for project in self.projects]
        self.assert_unique(all_macro_instances)

        all_gds_files = [project.get_macro_gds_filename() for project in self.projects]
        self.assert_unique(all_gds_files)

        logging.info(f"loaded {len(self.projects)} projects")

    def assert_unique(self, check):
        duplicates = [item for item, count in collections.Counter(check).items() if count > 1]
        if duplicates:
            logging.error("duplicate projects: {}".format(duplicates))
            exit(1)

    def build_metrics(self):
        total_seconds = 0
        total_wire_length = 0
        total_wires_count = 0
        total_physical_cells = 0
        max_cells = 0
        min_cells = 1000
        max_cell_project = None
        max_util = 0
        min_util = 100
        max_util_project = None
        languages = {}
        tags = []

        for project in self.projects:
            try:
                dt = datetime.datetime.strptime(project.metrics['total_runtime'][:-3], '%Hh%Mm%Ss')
            except KeyError:
                continue

            delt = datetime.timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second)
            total_seconds += delt.total_seconds()

            total_wire_length += int(project.metrics['wire_length'])
            total_wires_count += int(project.metrics['wires_count'])
            util = float(project.metrics['OpenDP_Util'])
            num_cells = project.get_cell_count_from_synth()
            total_physical_cells += num_cells

            yaml_data = project.get_project_doc_yaml()
            lang = yaml_data['language'].lower()
            if lang in languages:
                languages[lang] += 1
            else:
                languages[lang] = 1

            if num_cells > max_cells:
                max_cells = num_cells
                max_cell_project = project
            if num_cells < min_cells:
                min_cells = num_cells

            if util > max_util:
                max_util = util
                max_util_project = project
            if util < min_util:
                min_util = util

            try:
                tags += yaml_data['tag'].split(',')
            except KeyError:
                pass

        logging.info(f"build time for all projects {total_seconds / 3600} hrs")
        logging.info(f"total wire length {total_wire_length} um")
        logging.info(f"total cells {total_physical_cells}")
        logging.info(f"max cells {max_cells} for project {max_cell_project}")
        logging.info(f"min cells {min_cells}")
        logging.info(f"max util {max_util} for project {max_util_project}")
        logging.info(f"min util {min_util}")
        logging.info(f"languages {languages}")
        tags = [x.strip().lower() for x in tags]
        tags = list(filter(lambda a: a != "", tags))

        def count_items(lst):
            freq = {}
            for item in lst:
                if item not in freq:
                    freq[item] = 1
                else:
                    freq[item] += 1

            sorted_items = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            for item, count in sorted_items[0:9]:
                logging.info(f"{item:10}: {count}")

        logging.info("top 10 tags")
        count_items(tags)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TinyTapeout configuration and docs")

    with open('config.yaml') as fh:
        config = yaml.safe_load(fh)
    
    parser.add_argument('--list', help="list projects", action='store_const', const=True)
    parser.add_argument('--single', help="do action on single project", type=int, default=-1)
    parser.add_argument('--update-caravel', help='configure caravel for build', action='store_const', const=True)
    parser.add_argument('--harden', help="harden project", action="store_const", const=True)
    parser.add_argument('--test', help='use test projects', action='store_const', const=True)
    parser.add_argument('--sta-projects', help='use sta projects', action='store_const', const=True)
    parser.add_argument('--debug', help="debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('--log-email', help="print persons email in messages", action="store_const", const=True)
    parser.add_argument('--update-image', help="update the image", action="store_const", const=True)
    parser.add_argument('--dump-json', help="dump json of all project data to given file")
    parser.add_argument('--dump-markdown', help="dump markdown of all project data to given file")
    parser.add_argument('--dump-pdf', help="create pdf from the markdown")
    parser.add_argument('--build-hugo-content', help="directory to where to build hugo content")
    parser.add_argument('--metrics', help="print some project metrics", action="store_const", const=True)

    args = parser.parse_args()

    # setup log
    log_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
    # configure the client logging
    log = logging.getLogger('')
    # has to be set to debug as is the root logger
    log.setLevel(args.loglevel)

    # create console handler and set level to info
    ch = logging.StreamHandler(sys.stdout)
    # create formatter for console
    ch.setFormatter(log_format)
    log.addHandler(ch)

    projects = Projects(config, args)

    if args.sta_projects:
        modules_yaml_name = "modules_sta.yaml"
    else:
        modules_yaml_name = "modules.yaml"

    docs = Docs(projects.projects, args=args)
    caravel = CaravelConfig(config, projects.projects, modules_yaml_name)
    rom = ROMFile(config, projects.projects)

    if args.list:
        caravel.list()

    if args.metrics:
        projects.build_metrics()

    if args.update_caravel:
        caravel.instantiate()
        rom.write_rom()
        if not args.test:
            docs.build_index()

    if args.update_image:
        docs.update_image()

    if args.dump_json:
        docs.dump_json()

    if args.dump_markdown:
        docs.dump_markdown()

    if args.build_hugo_content:
        docs.build_hugo_content()
