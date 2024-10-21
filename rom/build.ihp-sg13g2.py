#!/usr/bin/env python3

#
# OpenLane2 build script to harden the tt_um_chip_rom macro
#
# Copyright (c) 2023 Sylvain Munaut <tnt@246tNt.com>
# Copyright (c) 2024 Tiny Tapeout LTD
# SPDX-License-Identifier: Apache-2.0
#

import os
from typing import List, Type

from openlane.flows.sequential import SequentialFlow
from openlane.steps import Checker, KLayout, Odb, OpenROAD, Step, Yosys


class MuxFlow(SequentialFlow):
    Steps: List[Type[Step]] = [
        Yosys.Synthesis,
        Checker.YosysUnmappedCells,
        # 		Checker.YosysSynthChecks,	# FIXME: Doesn't support tristate
        # 		OpenROAD.CheckSDCFiles,
        OpenROAD.Floorplan,
        # 		OpenROAD.TapEndcapInsertion,	# FIXME: Use CutRows instead
        OpenROAD.GeneratePDN,
        Odb.ApplyDEFTemplate,
        OpenROAD.GlobalPlacement,
        OpenROAD.DetailedPlacement,
        OpenROAD.GlobalRouting,
        OpenROAD.DetailedRouting,
        Checker.TrDRC,
        Odb.ReportDisconnectedPins,
        Checker.DisconnectedPins,
        Odb.ReportWireLength,
        Checker.WireLength,
        OpenROAD.FillInsertion,
        OpenROAD.RCX,
        # 		OpenROAD.STAPostPNR,
        # 		OpenROAD.IRDropReport,
        # 		Magic.StreamOut,
        # 		Magic.WriteLEF,
        OpenROAD.WriteAbstractLEF,
        KLayout.StreamOut,
        # 		KLayout.XOR,
        # 		Checker.XOR,
        KLayout.DRC,
        # 		Magic.DRC,
        # 		Checker.MagicDRC,
        # 		Magic.SpiceExtraction,
        # 		Checker.IllegalOverlap,
        # 		Netgen.LVS,
        # 		Checker.LVS,
    ]


if __name__ == "__main__":
    # Get PDK root out of environment
    PDK_ROOT = os.getenv("PDK_ROOT")
    PDK = os.getenv("PDK")

    flow_cfg = {
        # Main design properties
        "DESIGN_NAME": "tt_um_chip_rom",
        "DESIGN_IS_CORE": False,
        # Sources
        "VERILOG_FILES": [
            "./tt_um_chip_rom.v",
        ],
        # Floorplanning
        "DIE_AREA": [0, 0, 212.16, 154.98],
        "FP_DEF_TEMPLATE": "ref::$DESIGN_DIR/../ihp/def/tt_block_1x1.def",
        "FP_SIZING": "absolute",
        "BOTTOM_MARGIN_MULT": 1,
        "TOP_MARGIN_MULT": 1,
        "LEFT_MARGIN_MULT": 6,
        "RIGHT_MARGIN_MULT": 6,
        "CLOCK_PERIOD": 20,
        "CLOCK_PORT": "clk",
        # Placement
        "PL_TARGET_DENSITY_PCT": 50,
        # Routing
        "DIODE_PADDING": 0,
        "RT_MAX_LAYER": "Metal5",
    }

    flow = MuxFlow(
        flow_cfg,
        design_dir=".",
        pdk_root=PDK_ROOT,
        pdk=PDK,
    )
    flow.start()
