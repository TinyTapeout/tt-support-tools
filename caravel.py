import logging


class CaravelConfig():

    def __init__(self, projects, num_projects):
        self.projects = projects
        self.num_projects = num_projects

    # create macro file & positions, power hooks
    def create_macro_config(self):
        # array size
        rows    = 18
        cols    = 14

        # start point (lower left)
        start_x = 50
        start_y = 95

        # module block sizes
        scanchain_w = 30
        scanchain_spc = 6
        module_w = 150
        module_h = 170

        # how much x & y space to leave between blocks
        space_x = 15
        space_y = 15

        # step sizes
        step_x  = scanchain_w + module_w + scanchain_spc + space_x
        step_y  = module_h + space_y

        logging.info(f"start_x {start_x} start_y {start_y} step_x {step_x} step_y {step_y }")

        num_macros_placed = 0

        # macro.cfg: where macros are placed
        logging.info("creating macro.cfg")
        with open("openlane/user_project_wrapper/macro.cfg", 'w') as fh:
            fh.write("scan_controller 100 100 N\n")
            for row in range(rows):
                if row % 2 == 0:
                    col_order = range(cols)
                    orientation = 'N'
                else:
                    # reverse odd rows to place instances in a zig zag pattern, shortening the scan chain wires
                    col_order = range(cols - 1, -1, -1)
                    orientation = 'S'
                for col in col_order:
                    # skip the space where the scan controller goes on the first row
                    if row == 0 and col <= 1:
                        continue

                    if num_macros_placed < self.num_projects:
                        if orientation == 'N':
                            # scanchain first
                            # co-ords are bottom left corner
                            macro_instance = self.projects[num_macros_placed].get_scanchain_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, start_x + col * step_x, start_y + row * step_y, orientation
                            )
                            fh.write(instance)

                            macro_instance = self.projects[num_macros_placed].get_macro_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, start_x + scanchain_spc + scanchain_w + col * step_x, start_y + row * step_y, orientation
                            )
                            fh.write(instance)
                        else:
                            # macro first
                            macro_instance = self.projects[num_macros_placed].get_macro_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, start_x + col * step_x, start_y + row * step_y, orientation
                            )
                            fh.write(instance)

                            macro_instance = self.projects[num_macros_placed].get_scanchain_instance()
                            instance = "{} {:<4} {:<4} {}\n".format(
                                macro_instance, start_x + module_w + scanchain_spc + col * step_x, start_y + row * step_y, orientation
                            )
                            fh.write(instance)

                    num_macros_placed += 1

        logging.info(f"total user macros placed: {num_macros_placed}")

        # macro_power.tcl: extra file for macro power hooks
        logging.info("creating macro_power.tcl")
        with open("openlane/user_project_wrapper/macro_power.tcl", 'w') as fh:
            fh.write('set ::env(FP_PDN_MACRO_HOOKS) "\\\n')
            fh.write("	")
            fh.write("scan_controller")
            fh.write(" vccd1 vssd1 vccd1 vssd1")
            fh.write(", \\\n")
            for i in range(self.num_projects):
                fh.write("	")
                fh.write(self.projects[i].get_scanchain_instance())
                fh.write(" vccd1 vssd1 vccd1 vssd1, \\\n")
                fh.write("	")
                fh.write(self.projects[i].get_macro_instance())
                fh.write(" vccd1 vssd1 vccd1 vssd1")
                if i != self.num_projects - 1:
                    fh.write(", \\\n")
            fh.write('"\n')

        # extra_lef_gds.tcl
        lefs = []
        gdss = []
        logging.info("creating extra_lef_gds.tcl")
        for project in self.projects:
            if not project.is_fill():
                lefs.append(project.get_macro_lef_filename())
                gdss.append(project.get_macro_gds_filename())

        with open("openlane/user_project_wrapper/extra_lef_gds.tcl", 'w') as fh:
            fh.write('set ::env(EXTRA_LEFS) "\\\n')
            fh.write("$script_dir/../../lef/scan_controller.lef \\\n")
            fh.write("$script_dir/../../lef/scanchain.lef \\\n")
            for i, lef in enumerate(lefs):
                fh.write("$script_dir/../../lef/{}".format(lef))
                if i != len(lefs) - 1:
                    fh.write(" \\\n")
                else:
                    fh.write('"\n')
            fh.write('set ::env(EXTRA_GDS_FILES) "\\\n')
            fh.write("$script_dir/../../gds/scan_controller.gds \\\n")
            fh.write("$script_dir/../../gds/scanchain.gds \\\n")
            for i, gds in enumerate(gdss):
                fh.write("$script_dir/../../gds/{}".format(gds))
                if i != len(gdss) - 1:
                    fh.write(" \\\n")
                else:
                    fh.write('"\n')

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
            with open("upw_pre.v", "r") as fh_pre:
                fh.write(fh_pre.read())
            # Indent, join, and insert the module instances
            fh.write("\n".join([("    " + x).rstrip() for x in body]))
            # Insert the Caravel postamble
            with open("upw_post.v", "r") as fh_post:
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
