import logging
import json
import os


class CaravelConfig():

    def __init__(self, config, projects, num_projects):
        self.config = config
        self.projects = projects
        self.num_projects = num_projects
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

    # update caravel config
    def create_macro_config(self):
        with open(os.path.join(self.script_dir, 'caravel_template', 'upw_config.json')) as fh:
            caravel_config = json.load(fh)

        logging.info("GDS and LEF")
        lef_prefix = "dir::../../lef/"
        gds_prefix = "dir::../../gds/"
        for project in self.projects:
            if not project.is_fill():
                caravel_config["EXTRA_LEFS"].append(lef_prefix + project.get_macro_lef_filename())
                caravel_config["EXTRA_GDS_FILES"].append(gds_prefix + project.get_macro_gds_filename())

        with open("openlane/user_project_wrapper/config.json", 'w') as fh:
            json.dump(caravel_config, fh, indent=4)

    # instantiate inside user_project_wrapper
    def instantiate(self):
        # build the blackbox_project_includes.v file - used for blackboxing when building the GDS
        with open('verilog/blackbox_project_includes.v', 'w') as fh:
            for project in self.projects:
                if not project.is_fill():
                    fh.write(f'`include "gl/{project.get_gl_verilog_filename()}"\n')

        # build complete list of filenames for sim
        with open('verilog/includes/includes.rtl.caravel_user_project', 'w') as fh:
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/user_project_wrapper.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/tt_top.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/tt_ctrl.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/tt_mux.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/tt_user_module.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_buf.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_dfrbp.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_diode.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_inv.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_mux4.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_tbuf_pol.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_tbuf.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/tt-multiplexer/proto/prim_generic/tt_prim_zbuf.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/cells.v\n')
            for project in self.projects:
                if not project.is_fill():
                    fh.write(f'-v $(USER_PROJECT_VERILOG)/rtl/{project.get_top_verilog_filename()}\n')

        # build GL includes
        with open('verilog/includes/includes.gl.caravel_user_project', 'w') as fh:
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/user_project_wrapper.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/tt_ctrl.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/tt_mux.v\n')
            for project in self.projects:
                if not project.is_fill():
                    fh.write(f'-v $(USER_PROJECT_VERILOG)/gl/{project.get_gl_verilog_filename()}\n')

    def list(self):
        for project in self.projects:
            if not project.is_fill():
                logging.info(project)
