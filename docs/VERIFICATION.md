# Verification

We are not trying to verify every single design. That is up to the person who makes it. What we want is to ensure that every design is accessible, even if some designs are broken.

We can split the verification effort into functional testing (simulation), static tests (formal verification), timing tests (STA) and physical tests (LVS & DRC).

See the sections below for details on each type of verification.

## Setup

You will need the GitHub tokens setup as described in [INFO](INFO.md#instructions-to-build-gds).

The default of 250 projects takes a very long time to simulate, so I advise overriding the configuration:

    # fetch the test projects
    ./configure.py --test --clone-all
    # rebuild config with only 20 projects
    ./configure.py --test --update-caravel --limit 20

You will also need iVerilog & cocotb. The easist way to install these are to download and install the [oss-cad-suite](https://github.com/YosysHQ/oss-cad-suite-build).

## Simulations

* Simulation of some test projects at RTL and GL level. 
* Simulation of the whole chip with scan controller, external controller, logic analyser.
* Check wait state setting.
* Check clock divider setting.

### Scan controller

This test only instantiates user_project_wrapper (which contains all the small projects). It doesn't simulate the rest of the ASIC.

    cd verilog/dv/scan_controller
    make test_scan_controller

The Gate Level simulation requires scan_controller and user_project_wrapper to be re-hardened to get the correct gate level netlists: 

* Edit openlane/scan_controller/config.tcl and change NUM_DESIGNS=250 to NUM_DESIGNS=20.
* Then from the top level directory:


    make scan_controller
    make user_project_wrapper


* Then run the GL test


    cd verilog/dv/scan_controller
    make test_scan_controller_gl


#### single

Just check one inverter module. Mainly for easy understanding of the traces.

    make test_single

#### custom wait state

Just check one inverter module. Set a custom wait state value.

    make test_wait_state

#### clock divider

Test one inverter module with an automatically generated clock on input 0. Sets the clock rate to 1/2 of the scan refresh rate.

    make test_clock_div

## Top level tests setup

For all the top level tests, you will also need a [RISCV compiler to build the firmware](https://static.dev.sifive.com/dev-tools/riscv64-unknown-elf-gcc-8.3.0-2020.04.1-x86_64-linux-ubuntu14.tar.gz). 

You will also need to install the 'management core' for the Caravel ASIC submission wrapper. This is done automatically by following the [PDK install instructions](INFO.md#build-the-gds).

### Top level test: internal control

Uses the scan controller, instantiated inside the whole chip.

    cd verilog/dv/scan_controller_int
    make coco_test

### Top level test: external control

Uses external signals to control the scan chain. Simulates the whole chip.

    cd verilog/dv/scan_controller_ext
    make coco_test

### Top level test: logic analyser control

Uses the RISCV co-processor to drive the scanchain with firmware. Simulates the whole chip.

    cd verilog/dv/scan_controller_la
    make coco_test

## Formal Verification

* Formal verification that each small project's scan chain is correct.
* Formal verification that the correct signals are passed through for the 3 different scan chain control modes.

### Scan chain

Each GL netlist for each small project is proven to be equivalent to the reference scan chain implementation.
The verification is done on the GL netlist, so an RTL version of the cells used needed to be created.
See [here for more info](tinytapeout_scan/README.md).

### Scan controller MUX

In case the internal scan controller doesn't work, we also have ability to control the chain from external pins or the Caravel Logic Analyser.
We implement a simple MUX to achieve this and [formally prove it is correct](verilog/rtl/scan_controller/properties.v).

## Timing constraints

Due to limitations in OpenLane - a top level timing analyis is not possible. This would allow us to detect setup and hold violations in the scan chain. 

Instead, we design the chain and the timing constraints for each project and the scan controller with this in mind.

* [Each small project has a negedge flop flop at the end of the shift register to reclock the data](https://github.com/mattvenn/wokwi-verilog-gds-test/blob/17f106db36f022536d013b960316bcc7f02c572c/template/scan_wrapper.v#L67). This gives more hold margin.
* [Each small project has SDC timing constraints](https://github.com/mattvenn/wokwi-verilog-gds-test/blob/main/src/base.sdc)
* [Scan controller](https://github.com/mattvenn/tinytapeout-mpw7/blob/aacae16304f4a4878943a49fd479d8a284736e32/verilog/rtl/scan_controller/scan_controller.v#L334) uses a shift register clocked with the end of the chain to ensure correct data is captured.
* [Scan controller has its own SDC timing constraints](openlane/scan_controller/base.sdc)
* Scan controller can be configured to wait for a programmable time at latching data into the design and capturing it from the design.
* External pins (by default) control the scan chain.

## Physical tests

* LVS
* DRC
* CVC

### LVS

Each project is built with OpenLane, which will check LVS for each small project.
Then when we combine all the projects together we run a top level LVS & DRC for routing, power supply and macro placement.

The extracted netlist from the GDS is what is used in the formal scan chain proof.

### DRC

DRC is checked by OpenLane for each small project, and then again at the top level when we combine all the projects.

### CVC

Mitch Bailey' CVC checker is a device level static verification system for quickly and easily detecting common circuit errors in CDL (Circuit Definition Language) netlists. We ran the test on the final design and found no errors.

* See [the paper here](https://woset-workshop.github.io/PDFs/2020/a05-slides.pdf).
* Github repo for the tool: https://github.com/d-m-bailey/cvc
