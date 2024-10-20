#!/bin/bash
# Based on sg13g2-update.py from IHP

# Klayout
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/sg13g2.lyp $ORFS_ROOT/flow/platforms/ihp-sg13g2/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/sg13g2.lyt $ORFS_ROOT/flow/platforms/ihp-sg13g2/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/sg13g2.map $ORFS_ROOT/flow/platforms/ihp-sg13g2/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/drc/sg13g2_maximal.lydrc $ORFS_ROOT/flow/platforms/ihp-sg13g2/drc/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/drc/sg13g2_minimal.lydrc $ORFS_ROOT/flow/platforms/ihp-sg13g2/drc/

# LIB
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p35V_125C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_fast_1p32V_m40C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_fast_1p65V_m40C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p50V_25C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_dummy.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_fast_1p32V_3p6V_m40C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_fast_1p65V_3p6V_m40C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_slow_1p08V_3p0V_125C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_slow_1p35V_3p0V_125C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_typ_1p2V_3p3V_25C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lib/sg13g2_io_typ_1p5V_3p3V_25C.lib $ORFS_ROOT/flow/platforms/ihp-sg13g2/lib/

# GDS
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds $ORFS_ROOT/flow/platforms/ihp-sg13g2/gds/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/gds/sg13g2_io.gds $ORFS_ROOT/flow/platforms/ihp-sg13g2/gds/

# LEF
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef $ORFS_ROOT/flow/platforms/ihp-sg13g2/lef/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef $ORFS_ROOT/flow/platforms/ihp-sg13g2/lef/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lef/sg13g2_io.lef $ORFS_ROOT/flow/platforms/ihp-sg13g2/lef/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/lef/sg13g2_io_notracks.lef $ORFS_ROOT/flow/platforms/ihp-sg13g2/lef/

# Verilog
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v $ORFS_ROOT/flow/platforms/ihp-sg13g2/verilog/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v $ORFS_ROOT/flow/platforms/ihp-sg13g2/verilog/

# CDL
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_stdcell/cdl/sg13g2_stdcell.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_io/cdl/sg13g2_io.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_1024x64_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_1024x64_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_2048x64_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_256x48_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_256x64_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_512x64_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/
cp $IHP_PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/cdl/RM_IHPSG13_1P_64x64_c2_bm_bist.cdl $ORFS_ROOT/flow/platforms/ihp-sg13g2/cdl/

