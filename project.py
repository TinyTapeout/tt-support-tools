import yaml
import glob
import os
import logging
import re
import subprocess
import gdstk
import cairosvg
import csv
import json
import git_utils
import git
import shutil

CELL_URL = 'https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_sc_hd/cells/'


with open(os.path.join(os.path.dirname(__file__), 'tile_sizes.yaml'), 'r') as stream:
    tile_sizes = (yaml.safe_load(stream))


class Project():

    def __init__(self, index, git_url, local_dir, args, fill=False):
        self.git_url = git_url
        self.args = args
        self.index = index
        self.fill = fill
        self.local_dir = local_dir

    def post_clone_setup(self):
        self.load_yaml()
        self.setup_source_files()
        self.load_metrics()

    def load_metrics(self):
        try:
            with open(self.get_metrics_path()) as fh:
                self.metrics = next(csv.DictReader(fh))
        except FileNotFoundError:
            self.metrics = {}

    def check_ports(self):
        top = self.get_macro_name()
        sources = [os.path.join(self.local_dir, 'src', src) for src in self.src_files]
        source_list = " ".join(sources)

        json_file = 'ports.json'
        yosys_cmd = f"yosys -qp 'read_verilog -lib -sv {source_list}; hierarchy -top {top} ; proc; write_json {json_file}'"
        p = subprocess.run(yosys_cmd, shell=True)
        if p.returncode != 0:
            logging.error(f"yosys port read failed for {self}")
            exit(1)

        with open(json_file) as fh:
            ports = json.load(fh)
        os.unlink(json_file)

        module_ports = ports['modules'][top]['ports']
        required_ports = [
            ['clk', 1],
            ['ena', 1],
            ['rst_n', 1],
            ['ui_in', 8],
            ['uio_in', 8],
            ['uio_oe', 8],
            ['uio_out', 8],
            ['uo_out', 8],
        ]
        for port, bits in required_ports:
            if port not in module_ports:
                logging.error(f"{self} {port} not found in top")
                exit(1)
            if len(module_ports[port]['bits']) != bits:
                logging.error(f"{self} {port} doesn't have {bits} bits")
                exit(1)

    def check_num_cells(self):
        num_cells = self.get_cell_count_from_synth()
        if self.is_hdl():
            if num_cells < 20:
                logging.warning(f"{self} only has {num_cells} cells")
        else:
            if num_cells < 11:
                logging.warning(f"{self} only has {num_cells} cells")

    def is_fill(self):
        return self.fill

    def is_wokwi(self):
        if self.wokwi_id != 0:
            return True

    def is_hdl(self):
        return not self.is_wokwi()

    def load_yaml(self):
        try:
            with open(os.path.join(self.local_dir, 'info.yaml')) as fh:
                self.yaml = yaml.safe_load(fh)
        except FileNotFoundError:
            logging.error(f"yaml file not found for {self} - do you need to --clone the project repos?")
            exit(1)

    # find and save the location of the source files
    # get name of top module and the verilog module that contains the top
    def setup_source_files(self):
        # wokwi_id must be an int or 0
        try:
            self.wokwi_id = int(self.yaml['project']['wokwi_id'])
        except ValueError:
            logging.error("wokwi id must be an integer")
            exit(1)

        self.yaml['project']['git_url'] = self.git_url

        if self.is_hdl():
            self.top_module             = self.yaml['project']['top_module']
            self.src_files              = self.get_hdl_source()
            self.top_verilog_filename   = self.find_top_verilog()
        else:
            self.top_module             = f"tt_um_wokwi_{self.wokwi_id}"
            self.src_files              = self.get_wokwi_source()
            self.top_verilog_filename   = self.src_files[0]
        
        if not self.top_module.startswith("tt_um_"):
            logging.error(f'top module name must start with "tt_um_" (current value: "{self.top_module}")')
            exit(1)

        self.macro_instance         = f"{self.top_module}_{self.index :03}"

    def get_wokwi_source(self):
        src_file = "tt_um_wokwi_{}.v".format(self.wokwi_id)
        return [src_file, 'cells.v']

    def get_hdl_source(self):
        if 'source_files' not in self.yaml['project']:
            logging.error("source files must be provided if wokwi_id is set to 0")
            exit(1)

        source_files = self.yaml['project']['source_files']
        if source_files is None:
            logging.error("must be more than 1 source file")
            exit(1)

        if len(source_files) == 0:
            logging.error("must be more than 1 source file")
            exit(1)

        if 'top_module' not in self.yaml['project']:
            logging.error("must provide a top module name")
            exit(1)

        if self.yaml['project']['top_module'] == 'top':
            logging.error("top module cannot be called top - prepend your repo name to make it unique")
            exit(1)

        for filename in source_files:
            if '*' in filename:
                logging.error("* not allowed, please specify each file")
                exit(1)
            if not os.path.exists(os.path.join(self.local_dir, 'src', filename)):
                logging.error(f"{filename} doesn't exist in the repo")
                exit(1)

        return source_files

    def get_yaml(self):
        return self.yaml

    def get_hugo_row(self):
        return f'| {self.index} | [{self.yaml["documentation"]["title"]}]({self.index :03}) | {self.yaml["documentation"]["author"]}|\n'

    # docs stuff for index on README.md
    def get_index_row(self):
        return f'| {self.index} | {self.yaml["documentation"]["author"]} | {self.yaml["documentation"]["title"]} | {self.get_project_type_string()} | {self.git_url} |\n'

    def get_project_type_string(self):
        if self.is_wokwi():
            return f"[Wokwi]({self.get_wokwi_url()})"
        else:
            return "HDL"

    def get_project_doc_yaml(self):
        # fstring dict support is limited to one level deep, so put the git url and wokwi url in the docs key
        docs = self.yaml['documentation']
        docs['project_type'] = self.get_project_type_string()
        docs['git_url'] = self.git_url
        return docs

    def get_wokwi_url(self):
        return f'https://wokwi.com/projects/{self.wokwi_id}'

    # top module name is defined in one of the source files, which one?
    def find_top_verilog(self):
        rgx_mod  = re.compile(r"(?:^|[\s])module[\s]{1,}([\w]+)")
        top_verilog = []
        for src in self.src_files:
            print(f'SRC {src}')
            with open(os.path.join(self.local_dir, 'src', src)) as fh:
                for line in fh.readlines():
                    for match in rgx_mod.finditer(line):
                        if match.group(1) == self.top_module:
                            top_verilog.append(src)
        assert len(top_verilog) == 1
        return top_verilog[0]

    def get_git_remote(self):
        return list(git.Repo(self.local_dir).remotes[0].urls)[0]

    def clone(self):
        if os.path.exists(self.local_dir):
            git_remote = self.get_git_remote()
            if self.git_url == git_remote:
                logging.info("git repo already exists and is correct - skipping")
            else:
                logging.error("git repo exists and remote doesn't match - abort")
                logging.error(f"{self.git_url} != {git_remote}")
                exit(1)
        else:
            logging.debug("clone")
            git.Repo.clone_from(self.git_url, self.local_dir, recursive=True)

    def pull(self):
        repo = git.Repo(self.local_dir)
        # reset
        repo.git.reset('--hard')
        o = repo.remotes.origin
        o.pull()

    def __str__(self):
        """
        if self.args.log_email:
            return f"[{self.index:03} : {self.email} : {self.git_url}]"
        else:
        """
        return f"[{self.index:03} : {self.git_url}]"

    def fetch_gds(self):
        git_utils.install_artifacts(self.git_url, self.local_dir)

    def get_latest_action_url(self):
        return git_utils.get_latest_action_url(self.git_url, self.local_dir)

    def get_macro_name(self):
        return self.top_module

    # instance name of the project, different for each id
    def get_macro_instance(self):
        return self.macro_instance

    # unique id
    def get_index(self):
        return self.index

    # metrics
    def get_metrics_path(self):
        return os.path.join(self.local_dir, 'runs/wokwi/reports/metrics.csv')

    # name of the gds file
    def get_macro_gds_filename(self):
        return f"{self.top_module}.gds"

    def get_macro_lef_filename(self):
        return f"{self.top_module}.lef"

    def get_macro_spef_filename(self):
        return f"{self.top_module}.spef"

    # for GL sims & blackboxing
    def get_gl_verilog_filename(self):
        return f"{self.top_module}.v"

    # for simulations
    def get_top_verilog_filename(self):
        if self.is_hdl():
            # make sure it's unique & without leading directories
            # a few people use 'top.v', which is OK as long as the top module is called something more unique
            # but then it needs to be made unique so the source can be found
            filename = os.path.basename(self.top_verilog_filename)
            return f'{self.index :03}_{filename}'
        else:
            return self.top_verilog_filename

    def get_git_url(self):
        return self.git_url

    def copy_files_to_caravel(self):
        files = [
            (f"runs/wokwi/results/final/gds/{self.get_macro_gds_filename()}", f"gds/{self.get_macro_gds_filename()}"),
            (f"runs/wokwi/results/final/spef/{self.get_macro_spef_filename()}", f"spef/{self.get_macro_spef_filename()}"),
            (f"runs/wokwi/results/final/lef/{self.get_macro_lef_filename()}", f"lef/{self.get_macro_lef_filename()}"),
            (f"runs/wokwi/results/final/verilog/gl/{self.get_gl_verilog_filename()}", f"verilog/gl/{self.get_gl_verilog_filename()}"),
            (f"src/{self.top_verilog_filename}", f"verilog/rtl/{self.get_top_verilog_filename()}"),
            ]
        # copy RTL verilog to openlane2 mux directory:
        if os.path.isdir("tt-multiplexer/ol2/tt_top/verilog"):
            files.append((f"src/{self.top_verilog_filename}", f"tt-multiplexer/ol2/tt_top/verilog/{self.get_gl_verilog_filename()}"))

        logging.debug("copying files into position")
        for from_path, to_path in files:
            from_path = os.path.join(self.local_dir, from_path)
            logging.debug(f"copy {from_path} to {to_path}")
            shutil.copyfile(from_path, to_path)

    def print_wokwi_id(self):
        print(self.wokwi_id)

    def fetch_wokwi_files(self):
        logging.info("fetching wokwi files")
        src_file = self.src_files[0]
        url = f"https://wokwi.com/api/projects/{self.wokwi_id}/verilog"
        git_utils.fetch_file(url, os.path.join(self.local_dir, "src", src_file))

        # also fetch the wokwi diagram
        url = f"https://wokwi.com/api/projects/{self.wokwi_id}/diagram.json"
        diagram_file = "wokwi_diagram.json"
        git_utils.fetch_file(url, os.path.join(self.local_dir, "src", diagram_file))

        # attempt to download the *optional* truthtable for the project
        truthtable_file = "truthtable.md"
        url = f"https://wokwi.com/api/projects/{self.wokwi_id}/{truthtable_file}"
        try:
            git_utils.fetch_file(url, os.path.join(self.local_dir, "src", truthtable_file))
            logging.info(f'Wokwi project {self.wokwi_id} has a truthtable included, will test!')
            self.install_wokwi_testing()
        except FileNotFoundError:
            pass

    def install_wokwi_testing(self, destination_dir='src', resource_dir=None):
        if resource_dir is None or not len(resource_dir):
            resource_dir = os.path.join(os.path.dirname(__file__), 'testing')

        # directories in testing/lib to copy over
        pyLibsDir = os.path.join(resource_dir, 'lib')

        # src template dir
        srcTplDir = os.path.join(resource_dir, 'src-tpl')

        for libfullpath in glob.glob(os.path.join(pyLibsDir, '*')):
            logging.info(f'Copying {libfullpath} to {destination_dir}')
            shutil.copytree(
                libfullpath,
                os.path.join(destination_dir, os.path.basename(libfullpath)),
                dirs_exist_ok=True)

        for srcTemplate in glob.glob(os.path.join(srcTplDir, '*')):
            with open(srcTemplate, 'r') as f:
                contents = f.read()
                customizedContents = re.sub('WOKWI_ID', str(self.wokwi_id), contents)
                outputFname = os.path.basename(srcTemplate)
                with open(os.path.join(destination_dir, outputFname), 'w') as outf:
                    logging.info(f'writing src tpl to {outputFname}')
                    outf.write(customizedContents)
                    outf.close()

    def create_user_config(self):
        if self.is_wokwi():
            self.fetch_wokwi_files()
        logging.info("creating include file")
        filename = 'user_config.tcl'
        with open(os.path.join(self.local_dir, 'src', filename), 'w') as fh:
            fh.write("set ::env(DESIGN_NAME) {}\n".format(self.top_module))
            fh.write('set ::env(VERILOG_FILES) "\\\n')
            for line, source in enumerate(self.src_files):
                fh.write("    $::env(DESIGN_DIR)/" + source)
                if line != len(self.src_files) - 1:
                    fh.write(' \\\n')
            fh.write('"\n\n')
            tiles = self.yaml['project']['tiles']
            die_area = tile_sizes[tiles]
            fh.write(f'# Project area: {tiles} tiles\n')
            fh.write(f'set ::env(DIE_AREA) "{die_area}"\n')
            fh.write(f'set ::env(FP_DEF_TEMPLATE) "$::env(DESIGN_DIR)/../tt/def/tt_block_{tiles}.def"\n')

    def golden_harden(self):
        logging.info(f"hardening {self}")
        # copy golden config
        shutil.copyfile('golden_config.tcl', os.path.join(self.local_dir, 'src', 'config.tcl'))
        self.harden()

    def harden(self):
        cwd = os.getcwd()
        os.chdir(self.local_dir)
        # requires PDK, PDK_ROOT, OPENLANE_ROOT & OPENLANE_IMAGE_NAME to be set in local environment
        harden_cmd = 'docker run --rm -v $OPENLANE_ROOT:/openlane -v $PDK_ROOT:$PDK_ROOT -v $(pwd):/work -e PDK=$PDK -e PDK_ROOT=$PDK_ROOT -u $(id -u $USER):$(id -g $USER) $OPENLANE_IMAGE_NAME /bin/bash -c "./flow.tcl -overwrite -design /work/src -run_path /work/runs -tag wokwi"'
        logging.debug(harden_cmd)
        env = os.environ.copy()
        p = subprocess.run(harden_cmd, shell=True, env=env)
        if p.returncode != 0:
            logging.error("harden failed")
            exit(1)

        os.chdir(cwd)

    # doc check
    # makes sure that the basic info is present
    def check_yaml_docs(self):
        yaml = self.yaml
        logging.info("checking docs")
        for key in ['author', 'title', 'description', 'how_it_works', 'how_to_test', 'language', 'inputs', 'outputs', 'bidirectional']:
            if key not in yaml['documentation']:
                logging.error("missing key {} in documentation".format(key))
                exit(1)
            if yaml['documentation'][key] == "":
                logging.error("missing value for {} in documentation".format(key))
                exit(1)

    # use pandoc to create a single page PDF preview
    def create_pdf(self):
        yaml = self.yaml
        yaml = yaml['documentation']
        logging.info("creating pdf")
        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, "docs/project_header.md")) as fh:
            doc_header = fh.read()
        with open(os.path.join(script_dir, "docs/project_preview.md")) as fh:
            doc_template = fh.read()

        with open('datasheet.md', 'w') as fh:
            fh.write(doc_header)
            # handle pictures
            yaml['picture_link'] = ''
            if yaml['picture']:
                # skip SVG for now, not supported by pandoc
                picture_name = yaml['picture']
                if 'svg' not in picture_name:
                    yaml['picture_link'] = '![picture]({})'.format(picture_name)
                else:
                    logging.warning("svg not supported")

            # now build the doc & print it
            try:
                doc = doc_template.format(**yaml)
                fh.write(doc)
                fh.write("\n\pagebreak\n")
            except IndexError:
                logging.warning("missing pins in info.yaml, skipping")

        pdf_cmd = 'pandoc --pdf-engine=xelatex -i datasheet.md -o datasheet.pdf'
        logging.info(pdf_cmd)
        p = subprocess.run(pdf_cmd, shell=True)
        if p.returncode != 0:
            logging.error("pdf command failed")

    # SVG and PNG renders of the GDS
    def create_svg(self):
        gds = glob.glob(os.path.join(self.local_dir, 'runs/wokwi/results/final/gds/*gds'))
        library = gdstk.read_gds(gds[0])
        top_cells = library.top_level()
        top_cells[0].write_svg('gds_render.svg')

        if self.args.create_png:
            cairosvg.svg2png(url='gds_render.svg', write_to='gds_render.png')

    def print_warnings(self):
        warnings = []
        with open(os.path.join(self.local_dir, 'runs/wokwi/logs/synthesis/1-synthesis.log')) as f:
            for line in f.readlines():
                if line.startswith('Warning:'):
                    # bogus warning https://github.com/YosysHQ/yosys/commit/bfacaddca8a2e113e4bc3d6177612ccdba1555c8
                    if 'WIDTHLABEL' not in line:
                        warnings.append(line.strip())
        if len(warnings):
            print('# Synthesis warnings')
            print()
            for warning in warnings:
                print(f'* {warning}')

    def print_stats(self):
        print('# Routing stats')
        print()
        print('| Utilisation (%) | Wire length (um) |')
        print('|-------------|------------------|')
        print('| {} | {} |'.format(self.metrics['OpenDP_Util'], self.metrics['wire_length']))

    # Print the summaries
    def summarize(self):
        cell_count = self.get_cell_counts_from_gl()
        script_dir = os.path.dirname(os.path.realpath(__file__))

        with open(os.path.join(script_dir, 'categories.json')) as fh:
            categories = json.load(fh)
        with open(os.path.join(script_dir, 'defs.json')) as fh:
            defs = json.load(fh)

        # print all used cells, sorted by frequency
        total = 0
        if self.args.print_cell_summary:
            print('# Cell usage')
            print()
            print('| Cell Name | Description | Count |')
            print('|-----------|-------------|-------|')
            for name, count in sorted(cell_count.items(), key=lambda item: item[1], reverse=True):
                if count > 0:
                    total += count
                    cell_link = f'{CELL_URL}{name}'
                    print(f'| [{name}]({cell_link}) | {defs[name]["description"]} |{count} |')

            print(f'| | Total | {total} |')

        if self.args.print_cell_category:
            by_category = {}
            total = 0
            for cell_name in cell_count:
                cat_index = categories['map'][cell_name]
                cat_name = categories['categories'][cat_index]
                if cat_name in by_category:
                    by_category[cat_name]['count'] += cell_count[cell_name]
                    by_category[cat_name]['examples'].append(cell_name)
                else:
                    by_category[cat_name] = {'count' : cell_count[cell_name], 'examples' : [cell_name]}

                if cat_name not in ['Fill', 'Tap']:
                    total += cell_count[cell_name]

            print('# Cell usage by Category')
            print()
            print('| Category | Cells | Count |')
            print('|---------------|----------|-------|')
            for cat_name, cat_dict in sorted(by_category.items(), key=lambda x: x[1]['count'], reverse=True):
                cell_links = [f'[{name}]({CELL_URL}{name})' for name in cat_dict['examples']]
                print(f'|{cat_name} | {" ".join(cell_links)} | {cat_dict["count"]}|')

            print(f'## {total} total cells (excluding fill and tap cells)')

    # get cell count from synth report
    def get_cell_count_from_synth(self):
        num_cells = 0
        try:
            yosys_report = glob.glob(f'{self.local_dir}/runs/wokwi/reports/synthesis/1-synthesis.*0.stat.rpt')[0]  # can't open a file with \ in the path
            with open(yosys_report) as fh:
                for line in fh.readlines():
                    m = re.search(r'Number of cells:\s+(\d+)', line)
                    if m is not None:
                        num_cells = int(m.group(1))

        except IndexError:
            logging.warning(f"couldn't open yosys cell report for cell checking {self}")

        return num_cells

    # Parse the lib, cell and drive strength an OpenLane gate-level Verilog file
    def get_cell_counts_from_gl(self):
        cell_count = {}
        total = 0
        gl_files = glob.glob(os.path.join(self.local_dir, 'runs/wokwi/results/final/verilog/gl/*.nl.v'))
        with open(gl_files[0]) as fh:
            for line in fh.readlines():
                m = re.search(r'sky130_(\S+)__(\S+)_(\d+)', line)
                if m is not None:
                    total += 1
                    cell_lib = m.group(1)
                    cell_name = m.group(2)
                    cell_drive = m.group(3)
                    assert cell_lib in ['fd_sc_hd', 'ef_sc_hd']
                    assert int(cell_drive) > 0
                    try:
                        cell_count[cell_name] += 1
                    except KeyError:
                        cell_count[cell_name] = 1
        return (cell_count)

    # Load all the json defs and combine into one big dict, keyed by cellname
    # Needs access to the PDK
    def create_defs(self):
        # replace this with a find
        json_files = glob.glob('sky130_fd_sc_hd/latest/cells/*/definition.json')
        definitions = {}
        for json_file in json_files:
            with open(json_file) as fh:
                definition = json.load(fh)
                definitions[definition['name']] = definition

        with open('defs.json', 'w') as fh:
            json.dump(definitions, fh)
