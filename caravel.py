import logging
import os
import yaml
import json

class CaravelConfig():

    def __init__(self, config, projects, modules_yaml_name: str):
        self.config = config
        self.projects = projects
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.modules_yaml_name = modules_yaml_name

    # instantiate inside user_project_wrapper
    def instantiate(self):
        # build the blackbox_project_includes.v file - used for blackboxing when building the GDS
        with open('verilog/blackbox_project_includes.v', 'w') as fh:
            for project in self.projects:
                fh.write(f'`include "gl/{project.get_gl_verilog_filename()}"\n')

        # build GL includes
        with open('verilog/includes/includes.gl.caravel_user_project', 'w') as fh:
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/user_project_wrapper.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/tt_ctrl.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/tt_mux.v\n')
            for project in self.projects:
                fh.write(f'-v $(USER_PROJECT_VERILOG)/gl/{project.get_gl_verilog_filename()}\n')

        with open(self.modules_yaml_name, 'r') as modules_file:
            module_config = yaml.safe_load(modules_file)
            configured_macros = set(map(lambda mod: mod['name'], module_config['modules']))
            logging.info(f"found {len(configured_macros)} preconfigured macros: {configured_macros}")
            for project in self.projects:
                if project.unprefixed_name not in configured_macros:
                    module_config['modules'].append({'name': project.unprefixed_name})

        with open('tt-multiplexer/cfg/modules.yaml', 'w') as mux_modules_file:
            yaml.dump(module_config, mux_modules_file)

        res = os.system("make -C tt-multiplexer gensrc")
        if res != 0:
            logging.error("Failed to generate multiplexer placement configuration")
            exit(1)

        mux_index = {}
        mux_index_reverse = {}
        with open('tt-multiplexer/cfg/modules_placed.yaml') as placed_modules_file:
            placed_modules = yaml.safe_load(placed_modules_file)
            for module in placed_modules['modules']:
                mux_address = (module['y'] << 5) + module['x']
                module_name = 'tt_um_' + module['name']
                mux_index[mux_address] = module_name
                mux_index_reverse[module_name] = mux_address
            
        for project in self.projects:
            if project.top_module not in mux_index_reverse:
                logging.error(f"no placement found for {project}!")
                exit(1)
            project.mux_address = mux_index_reverse[project.top_module]
        
        with open('mux_index.json', 'w') as mux_index_file:
            json.dump(mux_index, mux_index_file)

    def list(self):
        for project in self.projects:
            logging.info(project)
