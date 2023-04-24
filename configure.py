#!/usr/bin/env python3
from orders import Orders
import datetime
import yaml
import argparse, logging, sys, os, collections
from project import Project
from documentation import Docs
from caravel import CaravelConfig


# pipe handling
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)


class Projects():

    def __init__(self, config, args):
        self.args = args
        self.config = config

        if args.test:
            self.projects_file = 'test_projects.yaml'
            self.project_dir = config['test_project_dir']
        else:
            self.projects_file = 'projects.yaml'
            self.project_dir = config['project_dir']

        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

        try:
            with open(self.projects_file) as fh:
                self.project_config = yaml.safe_load(fh)
        except FileNotFoundError:
            logging.error("projects.yaml not found, create it with --update-orders")
            exit(1)

        """
        # useful for contacting people when I find problems in the repo
        try:
            with open('git_url_to_email.json') as fh:
                self.git_url_to_email_map = json.load(fh)
        except FileNotFoundError:
            self.git_url_to_email_map = {}
        """

        self.projects = []
        for index in range(args.limit_num_projects):
            if args.single >= 0 and args.single != index:
                continue
            if index < args.start_from:
                continue
            if args.end_at != 0 and index > args.end_at:
                continue

            """
            try:
                email = self.git_url_to_email_map[git_url]
            except KeyError:
                email = 'none'
            """

            git_url = self.project_config[index]['url']
            filler = self.project_config[index]['fill']

            # not sure if this is a good idea
            if self.project_config[index]['status'] == 'disable':
                filler = True

            # fill projects don't have their own directory, reuse the first project which is always fill
            if filler:
                project_dir = os.path.join(os.path.join(self.project_dir, f'{0 :03}'))
            else:
                project_dir = os.path.join(os.path.join(self.project_dir, f'{index :03}'))

            project = Project(index, git_url, project_dir, args, fill=filler)

            # clone git repos locally & gds artifacts from action build
            if args.clone_all:
                if filler is False:
                    logging.info(f"cloning {project}")
                    project.clone()

            if args.fetch_gds:
                if filler is False:
                    logging.info(f"fetching gds for {project}")
                    project.fetch_gds()

            if args.update_all:
                if filler is False:
                    # only updates code, not gds artifacts
                    logging.info(f"git pull for {project}")
                    project.pull()

            # projects should now be installed, so load all the data from the yaml files
            # fill projects will load from the fill project's directory
            logging.debug("post clone setup")
            project.post_clone_setup()
            logging.debug(project)

            # fetch the wokwi source
            if args.clone_all:
                if not project.is_fill() and project.is_wokwi():
                    project.fetch_wokwi_files()

            if args.harden:
                if filler is False:
                    project.create_user_config()
                    project.golden_harden()

            if args.update_caravel:
                logging.debug("copying files to caravel")
                if filler is False:
                    project.copy_files_to_caravel()

                    # check all top level module ports are correct
                    project.check_ports()
                    project.check_num_cells()

            self.projects.append(project)

        # now do some sanity checks
        for project in self.projects:
            if project.get_git_remote() != project.git_url:
                logging.warning(f"{project} doesn't match remote: {project.get_git_remote()}")
                exit(1)

        all_macro_instances = [project.get_macro_instance() for project in self.projects]
        self.assert_unique(all_macro_instances)

        all_top_files = [project.get_top_verilog_filename() for project in self.projects if not project.is_fill()]
        self.assert_unique(all_top_files)

        all_gds_files = [project.get_macro_gds_filename() for project in self.projects if not project.is_fill()]
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

        for project in self.projects:
            if not project.is_fill():
                dt = datetime.datetime.strptime(project.metrics['total_runtime'][:-3], '%Hh%Mm%Ss')
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

        logging.info(f"build time for all projects {total_seconds / 3600} hrs")
        logging.info(f"total wire length {total_wire_length} um")
        logging.info(f"total cells {total_physical_cells}")
        logging.info(f"max cells {max_cells} for project {max_cell_project}")
        logging.info(f"min cells {min_cells}")
        logging.info(f"max util {max_util} for project {max_util_project}")
        logging.info(f"min util {min_util}")
        logging.info(f"languages {languages}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TinyTapeout configuration and docs")

    with open('config.yaml') as fh:
        config = yaml.safe_load(fh)
    # default max projects is row * col - 2 (scan controller takes first 2 slots)
    config['num_projects'] = config['layout']['rows'] * config['layout']['cols'] - 2

    parser.add_argument('--update-orders', help="update the order config file", action="store_const", const=True)
    parser.add_argument('--list', help="list projects", action='store_const', const=True)
    parser.add_argument('--clone-all', help="clone all projects", action="store_const", const=True)
    parser.add_argument('--update-all', help="git pull all projects", action="store_const", const=True)
    parser.add_argument('--fetch-gds', help="git fetch latest gds", action="store_const", const=True)
    parser.add_argument('--single', help="do action on single project", type=int, default=-1)
    parser.add_argument('--start-from', help="do action on projects after this index", type=int, default=0)
    parser.add_argument('--end-at', help="do action on projects before this index", type=int, default=0)
    parser.add_argument('--update-caravel', help='configure caravel for build', action='store_const', const=True)
    parser.add_argument('--harden', help="harden project", action="store_const", const=True)
    parser.add_argument('--limit-num-projects', help='only configure for the first n projects', type=int, default=int(config['num_projects']))
    parser.add_argument('--test', help='use test projects', action='store_const', const=True)
    parser.add_argument('--debug', help="debug logging", action="store_const", dest="loglevel", const=logging.DEBUG, default=logging.INFO)
    parser.add_argument('--log-email', help="print persons email in messages", action="store_const", const=True)
    parser.add_argument('--update-image', help="update the image", action="store_const", const=True)
    parser.add_argument('--dump-json', help="dump json of all project data to given file")
    parser.add_argument('--dump-markdown', help="dump markdown of all project data to given file")
    parser.add_argument('--dump-pdf', help="create pdf from the markdown")
    parser.add_argument('--build-hugo-content', help="directory to where to build hugo content")
    parser.add_argument('--metrics', help="print some project metrics", action="store_const", const=True)
    parser.add_argument('--add-extra-project', help="specify a github url to add. Project is added to the extra_projects list specifed in config.yaml")

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

    if args.update_orders:
        # don't instantiate orders unless we have to as it needs stripe token
        orders = Orders(config)
        orders.fetch_orders()
        orders.update_project_list()

    if args.add_extra_project:
        orders = Orders(config)
        orders.add_extra_project(args.add_extra_project)

    projects = Projects(config, args)

    docs = Docs(projects.projects, args=args)
    caravel = CaravelConfig(config, projects.projects, num_projects=args.limit_num_projects)

    if args.list:
        caravel.list()

    if args.metrics:
        projects.build_metrics()

    if args.update_caravel:
        caravel.create_macro_config()
        caravel.instantiate()
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
