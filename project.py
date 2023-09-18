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
from markdown_utils import limit_markdown_headings

CELL_URL = 'https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_sc_hd/cells/'


with open(os.path.join(os.path.dirname(__file__), 'tile_sizes.yaml'), 'r') as stream:
    tile_sizes = (yaml.safe_load(stream))


class Project():

    def __init__(self, index, git_url, local_dir, args, is_user_project):
        self.git_url = git_url
        self.args = args
        self.index = index
        self.local_dir = local_dir
        self.is_user_project = is_user_project
        self.src_dir = os.path.join(self.local_dir, 'src') if self.is_user_project else self.local_dir

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
        if not self.is_user_project and top == "tt_um_chip_rom":
            return # Chip ROM is auto generated, so we don't have the verilog yet
        sources = [os.path.join(self.src_dir, src) for src in self.src_files]
        source_list = " ".join(sources)

        json_file = 'ports.json'
        yosys_cmd = f"yowasp-yosys -qp 'read_verilog -lib -sv {source_list}; hierarchy -top {top} ; proc; write_json {json_file}'"
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
                logging.error(f"{self} port '{port}' missing from top module ('{top}')")
                exit(1)
            actual_bits = len(module_ports[port]['bits'])
            if actual_bits != bits:
                logging.error(f"{self} incorrect width for port '{port}' in module '{top}': {bits} bits required, {actual_bits} found")
                exit(1)

    def check_num_cells(self):
        num_cells = self.get_cell_count_from_synth()
        if self.is_hdl():
            if num_cells < 20:
                logging.warning(f"{self} only has {num_cells} cells")
        else:
            if num_cells < 11:
                logging.warning(f"{self} only has {num_cells} cells")

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
            if self.is_user_project:
                self.src_files              = self.get_hdl_source()
                self.top_verilog_filename   = self.find_top_verilog()
        else:
            self.top_module             = f"tt_um_wokwi_{self.wokwi_id}"
            if self.is_user_project:
                self.src_files              = self.get_wokwi_source()
                self.top_verilog_filename   = self.src_files[0]

        if not self.is_user_project:
            self.src_files              = [self.get_gl_verilog_filename()]
        
        self.unprefixed_name             = re.sub('^tt_um_', '', self.top_module)
        
        if not self.top_module.startswith("tt_um_"):
            logging.error(f'top module name must start with "tt_um_" (current value: "{self.top_module}")')
            exit(1)

        self.macro_instance         = f"{self.top_module}"

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
            if not os.path.exists(os.path.join(self.src_dir, filename)):
                logging.error(f"{filename} doesn't exist in the repo")
                exit(1)

        return source_files

    def get_yaml(self):
        return self.yaml

    def get_hugo_row(self):
        return f'| {self.index} | [{self.yaml["documentation"]["title"]}]({self.index :03}) | {self.yaml["documentation"]["author"]}|\n'

    # docs stuff for index on README.md
    def get_index_row(self):
        return f'| {self.mux_address} | {self.yaml["documentation"]["author"]} | {self.yaml["documentation"]["title"]} | {self.get_project_type_string()} | {self.git_url} |\n'

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
        # "How it works" and "How to test" may include markdown headings - make sure they don't break the ToC
        docs['how_it_works'] = limit_markdown_headings(docs['how_it_works'], min_level=4)
        docs['how_to_test'] = limit_markdown_headings(docs['how_to_test'], min_level=4)
        return docs

    def get_wokwi_url(self):
        return f'https://wokwi.com/projects/{self.wokwi_id}'

    # top module name is defined in one of the source files, which one?
    def find_top_verilog(self):
        rgx_mod  = re.compile(r"(?:^|[\s])module[\s]{1,}([\w]+)")
        top_verilog = []
        for src in self.src_files:
            with open(os.path.join(self.src_dir, src)) as fh:
                for line in fh.readlines():
                    for match in rgx_mod.finditer(line):
                        if match.group(1) == self.top_module:
                            top_verilog.append(src)
        if len(top_verilog) == 0:
            logging.error(f"Couldn't find verilog module '{self.top_module}' in any of the project's source files")
            exit(1)
        if len(top_verilog) > 1:
            logging.error(f"Top verilog module '{self.top_module}' found in multiple source files: {', '.join(top_verilog)}")
            exit(1)
        return top_verilog[0]

    def get_git_remote(self):
        return list(git.Repo(self.local_dir).remotes[0].urls)[0]
    
    def get_git_commit_hash(self):
        return git.Repo(self.local_dir).commit().hexsha
    
    def get_tt_tools_version(self):
        repo = git.Repo(os.path.join(self.local_dir, "tt"))
        return f"{repo.active_branch.name} {repo.commit().hexsha[:8]}"
    
    def get_workflow_url(self):
        GITHUB_SERVER_URL = os.getenv('GITHUB_SERVER_URL')
        GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY')
        GITHUB_RUN_ID = os.getenv('GITHUB_RUN_ID')
        if GITHUB_SERVER_URL and GITHUB_REPOSITORY and GITHUB_RUN_ID:
            return f"{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}"

    def __str__(self):
        """
        if self.args.log_email:
            return f"[{self.index:03} : {self.email} : {self.git_url}]"
        else:
        """
        return f"[{self.index:03} : {self.git_url}]"

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
        if self.is_user_project:
            if self.args.openlane2:
                return os.path.join(self.local_dir, 'runs/wokwi/final/metrics.csv')
            else:
                return os.path.join(self.local_dir, 'runs/wokwi/reports/metrics.csv')
        else:
            return os.path.join(self.local_dir, 'metrics.csv')
        
    def get_gl_path(self):
        if self.is_user_project:
            if self.args.openlane2:
                return glob.glob(os.path.join(self.local_dir, 'runs/wokwi/final/nl/*.nl.v'))[0]
            else:
                return glob.glob(os.path.join(self.local_dir, 'runs/wokwi/results/final/verilog/gl/*.nl.v'))[0]
        else:
            return os.path.join(self.local_dir, f'{self.top_module}.v')

    # name of the gds file
    def get_macro_gds_filename(self):
        return f"{self.top_module}.gds"

    def get_macro_info_filename(self):
        return f"{self.top_module}.info.json"

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

    def print_wokwi_id(self):
        print(self.wokwi_id)

    def fetch_wokwi_files(self):
        logging.info("fetching wokwi files")
        src_file = self.src_files[0]
        url = f"https://wokwi.com/api/projects/{self.wokwi_id}/verilog"
        git_utils.fetch_file(url, os.path.join(self.src_dir, src_file))

        # also fetch the wokwi diagram
        url = f"https://wokwi.com/api/projects/{self.wokwi_id}/diagram.json"
        diagram_file = "wokwi_diagram.json"
        git_utils.fetch_file(url, os.path.join(self.src_dir, diagram_file))

        # attempt to download the *optional* truthtable for the project
        truthtable_file = "truthtable.md"
        url = f"https://wokwi.com/api/projects/{self.wokwi_id}/{truthtable_file}"
        try:
            git_utils.fetch_file(url, os.path.join(self.src_dir, truthtable_file))
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
        self.check_ports()
        logging.info("creating include file")
        filename = 'user_config.tcl'
        with open(os.path.join(self.src_dir, filename), 'w') as fh:
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
        shutil.copyfile('golden_config.tcl', os.path.join(self.src_dir, 'config.tcl'))
        self.harden()

    def copy_picture_for_docs(self):
        picture = self.yaml['documentation']['picture']
        if not picture:
            return
        extension = os.path.splitext(picture)[1]
        supported_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.pdf']
        if not os.path.exists(picture):
            logging.warning(f"Picture file '{picture}' not found in repo, skipping")
        elif extension not in supported_extensions:
            logging.warning(f"Picture file '{picture}' has unsupported extension '{extension}' (we support {', '.join(supported_extensions)}), skipping")
        else:
            picture_dir = os.path.join(self.local_dir, 'src/__tinytapeout')
            os.makedirs(picture_dir, exist_ok=True)
            shutil.copyfile(picture, os.path.join(picture_dir, f'picture{extension}'))

    def harden(self):
        cwd = os.getcwd()
        os.chdir(self.local_dir)
      
        repo = self.get_git_remote()
        commit_hash = self.get_git_commit_hash()
        tt_version = self.get_tt_tools_version()
        workflow_url = self.get_workflow_url()
      
        if self.args.openlane2:
            if not os.path.exists('runs/wokwi'):
                print("OpenLane 2 harden not supported yet, please run OpenLane 2 manually")
                exit(1)
            print("Writing commit information on top of the existing OpenLane 2 run (runs/wokwi)")
        else:
            # requires PDK, PDK_ROOT, OPENLANE_ROOT & OPENLANE_IMAGE_NAME to be set in local environment
            harden_cmd = 'docker run --rm -v $OPENLANE_ROOT:/openlane -v $PDK_ROOT:$PDK_ROOT -v $(pwd):/work -e PDK=$PDK -e PDK_ROOT=$PDK_ROOT -u $(id -u $USER):$(id -g $USER) $OPENLANE_IMAGE_NAME /bin/bash -c "./flow.tcl -overwrite -design /work/src -run_path /work/runs -tag wokwi"'
            logging.debug(harden_cmd)
            env = os.environ.copy()
            p = subprocess.run(harden_cmd, shell=True, env=env)
            if p.returncode != 0:
                logging.error("harden failed")
                exit(1)
        
        # Write commit information
        commit_id_json_path = 'runs/wokwi/results/final/commit_id.json'
        if self.args.openlane2:
            commit_id_json_path = 'runs/wokwi/final/commit_id.json'
        with open(os.path.join(self.local_dir, commit_id_json_path), 'w') as f:
            json.dump({
                "app": f"Tiny Tapeout {tt_version}",
                "repo": repo,
                "commit": commit_hash,
                "workflow_url": workflow_url,
            }, f, indent=2)
            f.write("\n")
        
        # Copy user provided picture (if exists) to project directory
        self.copy_picture_for_docs()

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
                picture_name = yaml['picture']
                yaml['picture_link'] = '![picture]({})'.format(picture_name)

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
    
    # Read and return top-level GDS data from the final GDS file, using gdstk:
    def get_final_gds_top_cells(self):
        gds = glob.glob(os.path.join(self.local_dir, 'runs/wokwi/results/final/gds/*gds'))
        if self.args.openlane2:
            gds = glob.glob(os.path.join(self.local_dir, 'runs/wokwi/final/gds/*gds'))
        library = gdstk.read_gds(gds[0])
        top_cells = library.top_level()
        return top_cells[0]

    # SVG and PNG renders of the GDS
    def create_svg(self):
        top_cells = self.get_final_gds_top_cells()
        top_cells.write_svg('gds_render.svg')

        if self.args.create_png:
            cairosvg.svg2png(url='gds_render.svg', write_to='gds_render.png')

    # Try various QUICK methods to create a more-compressed PNG render of the GDS,
    # and fall back to create_svg if it doesn't work. This is designed for speed,
    # and in particular for use by the GitHub Actions.
    # For more info, see:
    # https://github.com/TinyTapeout/tt-gds-action/issues/8
    def create_png_preview(self):

        logging.info('Loading GDS data...')
        top_cells = self.get_final_gds_top_cells()

        # Remove label layers (i.e. delete text), then generate SVG:
        sky130_label_layers = [
            (64,59),    # 64/59 - pwell.label
            (64,5),     # 64/5  - nwell.label
            (67,5),     # 67/5  - li1.label
            (68,5),     # 68/5  - met1.label
            (69,5),     # 69/5  - met2.label
            (70,5),     # 70/5  - met3.label
            (71,5),     # 71/5  - met4.label
        ]
        top_cells.filter(sky130_label_layers)
        svg = 'gds_render_preview.svg'
        logging.info('Rendering SVG without text label layers: {}'.format(svg))
        top_cells.write_svg(svg, pad=0)
        # We should now have gds_render_preview.svg

        # Try converting using 'rsvg-convert' command-line utility.
        # This should create gds_render_preview.png
        png = 'gds_render_preview.png'
        logging.info('Converting to PNG using rsvg-convert: {}'.format(png))


        p = subprocess.run('rsvg-convert --unlimited {} -o {} --no-keep-image-data'.format(svg, png), shell=True, capture_output=True)

        if p.returncode == 127:
            logging.warning('rsvg-convert not found; is librsvg2-bin installed? Falling back to cairosvg. This might take a while...')
            # Fall back to cairosvg:
            cairosvg.svg2png(url=svg, write_to=png)

        elif p.returncode != 0 and b'cannot load more than' in p.stderr:
            logging.warning('Too many SVG elements ("{}"). Reducing complexity...'.format(p.stderr.decode().strip()))
            # Remove more layers that are hardly visible anyway:
            sky130_buried_layers = [
                (64,16), # 64/16 - nwell.pin
                (65,44), # 65/44 - tap.drawing
                (68,16), # 68/16 - met1.pin
                (68,44), # 68/44 - via.drawing
                (81,4 ), # 81/4  - areaid.standardc
                (70,20), # 70/20 - met3.drawing
                # Important:
                # (68,20), # 68/20 - met1.drawing
                # Less important, but keep for now:
                # (69,20), # 69/20 - met2.drawing
            ]
            top_cells.filter(sky130_buried_layers)
            svg_alt = 'gds_render_preview_alt.svg'
            logging.info('Rendering SVG with more layers removed: {}'.format(svg_alt))
            top_cells.write_svg(svg_alt, pad=0)
            logging.info('Converting to PNG using rsvg-convert: {}'.format(png))

            p = subprocess.run('rsvg-convert --unlimited {} -o {} --no-keep-image-data'.format(svg_alt, png), shell=True, capture_output=True)

            if p.returncode != 0:
                logging.warning('Still cannot convert to SVG ("{}"). Falling back to cairosvg. This might take a while...'.format(p.stderr.decode().strip()))
                # Fall back to cairosvg, and since we're doing that, might as well use the original full-detail SVG anyway:
                cairosvg.svg2png(url=svg, write_to=png)

        # By now we should have gds_render_preview.png

        # Compress with pngquant:
        final_png = 'gds_render.png'
        if self.yaml['project']['tiles'] == '8x2':
            quality = '0-10' # Compress more for 8x2 tiles.
        else:
            quality = '0-30'
        logging.info('Compressing PNG further with pngquant to: {}'.format(final_png))
        p = subprocess.run('pngquant --quality {} --speed 1 --nofs --strip --force --output {} {}'.format(quality, final_png, png), shell=True, capture_output=True)
        if p.returncode == 127:
            logging.warning('pngquant not found; is the package installed? Using intermediate (uncompressed) PNG file')
            os.rename(png, final_png)
        elif p.returncode !=0:
            logging.warning('pngquant error {} ("{}"). Using intermediate (uncompressed) PNG file'.format(p.returncode, p.stderr.decode().strip()))
            os.rename(png, final_png)
        logging.info('Final PNG is {} ({:,} bytes)'.format(final_png, os.path.getsize(final_png)))


    def print_warnings(self):
        warnings = []
        synth_log = 'runs/wokwi/logs/synthesis/1-synthesis.log'
        if self.args.openlane2:
            synth_log = 'runs/wokwi/02-yosys-synthesis/yosys-synthesis.log'
        with open(os.path.join(self.local_dir, synth_log)) as f:
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
            yosys_report = f'{self.local_dir}/synthesis-stats.txt'
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
        with open(self.get_gl_path()) as fh:
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
