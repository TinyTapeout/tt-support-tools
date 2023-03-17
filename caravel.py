import logging
import json
import os


class CaravelConfig():

    def __init__(self, config, projects, num_projects):
        self.config = config
        self.projects = projects
        self.num_projects = num_projects
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

    # create macro file & positions, power hooks
    def create_macro_config(self):
        # array size
        c = self.config['layout']

        # step sizes
        step_x  = c['scanchain_w'] + c['module_w'] + c['scanchain_spc'] + c['space_x']
        step_y  = c['module_h'] + c['space_y']

        logging.info(f"start_x {c['start_x']} start_y {c['start_y']} step_x {step_x} step_y {step_y}")

        num_macros_placed = 0

        # macro.cfg: where macros are placed
        logging.info("creating macro.cfg")
        with open("openlane/user_project_wrapper/macro.cfg", 'w') as fh:
            fh.write(f"scan_controller {c['scan_control_x']} {c['scan_control_y']} N\n")
            for row in range(c['rows']):
                if row % 2 == 0:
                    col_order = range(c['cols'])
                    orientation = 'N'
                else:
                    # reverse odd rows to place instances in a zig zag pattern, shortening the scan chain wires
                    col_order = range(c['cols'] - 1, -1, -1)
                    orientation = 'S'
                for col in col_order:
                    # skip the space where the scan controller goes on the first row
                    if row == 0 and col <= 1:
                        continue

                    logging.debug(self.num_projects)
                    if num_macros_placed < self.num_projects:
                        if orientation == 'N':
                            # scanchain first
                            # co-ords are bottom left corner
                            macro_instance = self.projects[num_macros_placed].get_scanchain_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, c['start_x'] + col * step_x, c['start_y'] + row * step_y, orientation
                            )
                            fh.write(instance)

                            macro_instance = self.projects[num_macros_placed].get_macro_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, c['start_x'] + c['scanchain_spc'] + c['scanchain_w'] + col * step_x, c['start_y'] + row * step_y, orientation
                            )
                            fh.write(instance)
                        else:
                            # macro first
                            macro_instance = self.projects[num_macros_placed].get_macro_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, c['start_x'] + col * step_x, c['start_y'] + row * step_y, orientation
                            )
                            fh.write(instance)

                            macro_instance = self.projects[num_macros_placed].get_scanchain_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, c['start_x'] + c['module_w'] + c['scanchain_spc'] + col * step_x, c['start_y'] + row * step_y, orientation
                            )
                            fh.write(instance)

                    num_macros_placed += 1

        logging.info(f"total user macros placed: {num_macros_placed}")

        with open(os.path.join(self.script_dir, 'caravel_template', 'upw_config.json')) as fh:
            caravel_config = json.load(fh)

        power_domains = "vccd1 vssd1 vccd1 vssd1"
        power_config = []
        logging.info("creating macro hooks")

        for i in range(self.num_projects):
            power_config.append(f"{self.projects[i].get_scanchain_instance()} {power_domains},")
            power_config.append(f"{self.projects[i].get_macro_instance()} {power_domains},")
        power_config.append(f"scan_controller {power_domains}")  # no trailing comma

        caravel_config["FP_PDN_MACRO_HOOKS"] = power_config

        logging.info("GDS and LEF")
        lef_prefix = "dir::../../lef/"
        gds_prefix = "dir::../../gds/"
        caravel_config["EXTRA_LEFS"].append(lef_prefix + "scan_controller.lef")
        caravel_config["EXTRA_LEFS"].append(lef_prefix + "scanchain.lef")
        caravel_config["EXTRA_GDS_FILES"].append(gds_prefix + "scan_controller.gds")
        caravel_config["EXTRA_GDS_FILES"].append(gds_prefix + "scanchain.gds")
        for project in self.projects:
            if not project.is_fill():
                caravel_config["EXTRA_LEFS"].append(lef_prefix + project.get_macro_lef_filename())
                caravel_config["EXTRA_GDS_FILES"].append(gds_prefix + project.get_macro_gds_filename())

        with open("openlane/user_project_wrapper/config.json", 'w') as fh:
            json.dump(caravel_config, fh, indent=4)

    # instantiate inside user_project_wrapper
    def instantiate(self):
        logging.info("instantiating designs in user_project_wrapper.v")

        # NOTE: The user project wrapper initially used vectored signals for clk,
        #       scan, and latch signals. However, this leads to atrocious sim
        #       performance, as any change within the vectored signal is
        #       interpreted as a trigger condition for re-evaluating logic (at
        #       least this is the case under Icarus and Verilator). Therefore
        #       single bit signals are used between stages to limit the impact
        #       of any wire changing.

        # Instance the scan controller
        body = [
            "",
            "wire sc_clk_out, sc_data_out, sc_latch_out, sc_scan_out;",
            "wire sc_clk_in,  sc_data_in;",
            "",
            f"scan_controller #(.NUM_DESIGNS({self.num_projects})) scan_controller (",
            "   .clk                    (wb_clk_i),",
            "   .reset                  (wb_rst_i),",
            "   .active_select          (io_in[20:12]),",
            "   .inputs                 (io_in[28:21]),",
            "   .outputs                (io_out[36:29]),",
            "   .ready                  (io_out[37]),",
            "   .slow_clk               (io_out[10]),",
            "   .set_clk_div            (io_in[11]),",
            "",
            "   .scan_clk_out           (sc_clk_out),",
            "   .scan_clk_in            (sc_clk_in),",
            "   .scan_data_out          (sc_data_out),",
            "   .scan_data_in           (sc_data_in),",
            "   .scan_select            (sc_scan_out),",
            "   .scan_latch_en          (sc_latch_out),",
            "",
            "   .la_scan_clk_in         (la_data_in[0]),",
            "   .la_scan_data_in        (la_data_in[1]),",
            "   .la_scan_data_out       (la_data_out[0]),",
            "   .la_scan_select         (la_data_in[2]),",
            "   .la_scan_latch_en       (la_data_in[3]),",
            "",
            "   .driver_sel             (io_in[9:8]),",
            "",
            "   .oeb                    (io_oeb)",
            ");",
        ]

        # Instance every design on the scan chain
        for idx in range(self.num_projects):
            # First design driven by scan controller, all others are chained
            pfx      = f"sw_{idx:03d}"
            prev_pfx = f"sw_{idx-1:03d}" if idx > 0 else "sc"
            # Pickup the Wokwi design ID and github URL for the project
            giturl = self.projects[idx].get_git_url()

            # Append the instance to the body
            body += [
                "",
                f"// [{idx:03d}] {giturl}",
                f"wire {pfx}_clk_out, {pfx}_data_out, {pfx}_scan_out, {pfx}_latch_out;",
                f"wire [7:0] {pfx}_module_data_in;",
                f"wire [7:0] {pfx}_module_data_out;",
                f"scanchain #(.NUM_IOS(8)) {self.projects[idx].get_scanchain_instance()} (",
                f"    .clk_in          ({prev_pfx}_clk_out),",
                f"    .data_in         ({prev_pfx}_data_out),",
                f"    .scan_select_in  ({prev_pfx}_scan_out),",
                f"    .latch_enable_in ({prev_pfx}_latch_out),",
                f"    .clk_out         ({pfx}_clk_out),",
                f"    .data_out        ({pfx}_data_out),",
                f"    .scan_select_out ({pfx}_scan_out),",
                f"    .latch_enable_out({pfx}_latch_out),",
                f"    .module_data_in  ({pfx}_module_data_in),",
                f"    .module_data_out ({pfx}_module_data_out)",
                ");"
            ]

            # Append the user module to the body
            body += [
                "",
                f"{self.projects[idx].get_macro_name()} {self.projects[idx].get_macro_instance()} (",
                f"    .io_in  ({pfx}_module_data_in),",
                f"    .io_out ({pfx}_module_data_out)",
                ");"

            ]

        # Link the final design back to the scan controller
        body += [
            "",
            "// Connect final signals back to the scan controller",
            f"assign sc_clk_in  = sw_{idx:03d}_clk_out;",
            f"assign sc_data_in = sw_{idx:03d}_data_out;",
            "",
            ""
        ]

        # Write to file
        with open('verilog/rtl/user_project_wrapper.v', 'w') as fh:
            # Insert the Caravel preamble
            with open(os.path.join(self.script_dir, 'caravel_template', 'upw_pre.v')) as fh_pre:
                fh.write(fh_pre.read())
            # Indent, join, and insert the module instances
            fh.write("\n".join([("    " + x).rstrip() for x in body]))
            # Insert the Caravel postamble
            with open(os.path.join(self.script_dir, 'caravel_template', 'upw_post.v')) as fh_post:
                fh.write(fh_post.read())

        # build the blackbox_project_includes.v file - used for blackboxing when building the GDS
        with open('verilog/blackbox_project_includes.v', 'w') as fh:
            fh.write('`include "rtl/scan_controller/scan_controller.v"\n')
            fh.write('`include "rtl/scanchain/scanchain.v"\n')
            for project in self.projects:
                if not project.is_fill():
                    fh.write(f'`include "gl/{project.get_gl_verilog_filename()}"\n')

        # build complete list of filenames for sim
        with open('verilog/includes/includes.rtl.caravel_user_project', 'w') as fh:
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/user_project_wrapper.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/scan_controller/scan_controller.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/scanchain/scanchain.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/rtl/cells.v\n')
            for project in self.projects:
                if not project.is_fill():
                    fh.write(f'-v $(USER_PROJECT_VERILOG)/rtl/{project.get_top_verilog_filename()}\n')

        # build GL includes
        with open('verilog/includes/includes.gl.caravel_user_project', 'w') as fh:
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/user_project_wrapper.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/scan_controller.v\n')
            fh.write('-v $(USER_PROJECT_VERILOG)/gl/scanchain.v\n')
            for project in self.projects:
                if not project.is_fill():
                    fh.write(f'-v $(USER_PROJECT_VERILOG)/gl/{project.get_gl_verilog_filename()}\n')

    def list(self):
        for project in self.projects:
            logging.info(project)
