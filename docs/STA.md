# Toplevel STA and Spice analysis for TinyTapeout-02 and 03.

Contributed by J. Birch 22 March 2023

## Introduction

TinyTapeout is built using the OpenLane flow and consists of three major components:

1) up to 250 user designs with a common interface, each of which has been composed using the OpenLane flow,
2) a scanchain block that is instanced for each user design to provide input data and to sink output data,
3) a scan chain controller.

The OpenLane flow allows for timing analysis of each of these individual blocks but does not provide for
analysis of the assembly of them, which leaves potential holes in timing that could cause failures.

This work allows a single design to be assembled out of the sub-blocks and this can then be submitted to
STA for analysis.

In addition, an example critical path (for the clock that is passed along the scanchain) is created using
a Python script so that it can be run through SPICE.

## GitHub action

The [STA github action](.github/workflows/sta.yaml) automatically runs the STA when the repository is updated.

## Prerequisites

To run STA, the following files need to be available:

1) a gate level verilog netlist of the top level design (verilog/rtl/user_project_wrapper.v)
2) a gate level verilog netlist for each sub-block (verilog/rtl/)
3) a SPEF format parasitics file for the top level wiring (spef/)
4) a SPEF format parasitics file for each sub-block (spef/)
5) the relevant SkyWater libraries for STA analysis - installed with the PDK
6) OpenSTA 2.4.0 (or later) needs to be on the PATH. rundocker.sh shows how to use STA included in the OpenLane docker
7) python3.9 or later
8) verilog parser (pip3 install verilog-parser)
9) a constraints file (sta_top/top.sdc)

## Assumptions

* all of the Verilog files are in a single directory
* all of the SPEF files are in a single directory

## Issues

The Verilog parser has two bugs: it does not recognise 'inout' and it does not cope
with escaped names (starting with a '\'). Locally this has been fixed but to use the
off-the-shelf parser we preprocess the file to change inout to input and remove the escapes and
substitute the [nnn] with _nnn_ in the names 

## Invoking STA analysis

    sta_top/toplevel_sta.py <path to verilog> <path to spef> <sdc> 

eg:

    sta_top/toplevel_sta.py ./verilog/gl/user_project_wrapper.v 
    ./spef/user_project_wrapper.spef ./sta_top/top.sdc > sta.log

Alternatively you can enter interactive mode after analysis:

    sta_top/toplevel_sta.py ./verilog/gl/user_project_wrapper.v 
    ./spef/user_project_wrapper.spef ./sta_top/top.sdc -i

## How it works

* preprocesses the main Verilog
* parses the main Verilog to find which modules are used
* creates a new merged Verilog containing all the module netlists and the main netlist
* creates a tcl script in the spef directory to load the relevant spefs for each instanced module in the main verilog
* creates all_sta.tcl in the verilog/gl directory that does the main STA steps (loading design, loading constraints,
running analyses) - this mimics what OpenLane does
* creates a script sta.sh in the verilog/gl directory which sets up the environment and invokes STA to run all_sta.tcl
* runs sta.sh

## Invoking Spice simulation:

### Important notes

* This uses at least ngspice-34, tested on ngspice-39, which has features to increase speed
and reduce memory image when running with the SkyWater spice models. In addition the following
needs to be set in ~/spice.rc and/or ~/.spiceinit:

    set ngbehavior=hs

* Note the spelling of ngbehavior (no u). If this is not set then the simulation will run out of memory]
* If the critical path changes then the spice_path.py script will need to be adapted to follow suit

### Instructions

* go to where the included spice files will be found

    cd $PDK_ROOT/sky130A/libs.tech/ngspice

* run the script to get the critical path spice circuit - 250 stages of the clock

    <repo directory>/sta_top/spice_path.py path.spice

* invoke spice (takes about 2 minutes)

    ngspice path.spice

* run the sim (takes about 2 minutes)

    tran 1n 70n

* show the results

    plot i0 i250

This chart shows the input clock and how it changes after 250 blocks. It was simulated for 200n to capture a clean pair of clock pulses.

![clock_spice.png](pics/clock_spice.png)

