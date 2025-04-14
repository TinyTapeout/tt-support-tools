"""

Wokwi Tiny Tapeout truth-table based auto test sequence.

SPDX-FileCopyrightText: © 2023 Pat Deegan, https://psychogenic.com
SPDX-License-Identifier: Apache2.0
"""

import cocotb
import testutils.truthtable as truthtable


@cocotb.test()
async def truthTableCompare(parentDUT):
    """
    truthTableCompare  -- loads markdown truth table and, if load succeeded, actually performs the tests.
    """
    usermodule = parentDUT.dut
    i_bus = parentDUT.ui_in
    o_bus = parentDUT.uo_out
    tt = truthtable.loadMarkdownTruthTable("truthtable.md", usermodule._log)
    if tt is None:
        usermodule._log.info("No truth table loaded, no table compare test to run")
        return

    usermodule._log.debug(str(tt))
    await tt.testAll(i_bus, o_bus, usermodule._log)
