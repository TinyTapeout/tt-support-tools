# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2024-2025 Tiny Tapeout LTD
# Author: Uri Shaked
# Description: This script initializes a new Magic project for an analog design on Tiny Tapeout.

# Important: before running this script, download the the .def file from
# https://raw.githubusercontent.com/TinyTapeout/tt-support-tools/main/tech/sky130A/def/analog/tt_analog_1x2.def

# Change the settings below to match your design:
# ------------------------------------------------
set TOP_LEVEL_CELL     tt_um_analog_example
set TEMPLATE_FILE      tt_analog_1x2.def
set POWER_STRIPE_WIDTH 2um                 ;# The minimum width is 1.2um

# Power stripes: NET name, x position. You can add additional power stripes for each net, as needed.
set POWER_STRIPES {
    VDPWR 1um
    VGND  4um
}
# If you use the 3v3 template, uncomment the line below:
#lappend POWER_STRIPES VAPWR 7um

# Read in the pin positions
# -------------------------
def read $TEMPLATE_FILE
cellname rename tt_um_template $TOP_LEVEL_CELL

# Draw the power stripes
# --------------------------------
proc draw_power_stripe {name x} {
    global POWER_STRIPE_WIDTH
    box $x 5um $x 220.76um
    box width $POWER_STRIPE_WIDTH
    paint met4
    label $name FreeSans 0.25u -met4
    port make
    port use [expr {$name eq "VGND" ? "ground" : "power"}]
    port class bidirectional
    port connections n s e w
}

# You can extra power stripes, as you need.
foreach {name x} $POWER_STRIPES {
    puts "Drawing power stripe $name at $x"
    draw_power_stripe $name $x
}

# Save the layout and export GDS/LEF
# ----------------------------------
save ${TOP_LEVEL_CELL}.mag
file mkdir gds
gds write gds/${TOP_LEVEL_CELL}.gds
file mkdir lef
lef write lef/${TOP_LEVEL_CELL}.lef -hide -pinonly
