---
title: |
  ![](ttlogo.png){width=15cm}  
    Tiny Tapeout 02 Datasheet
subtitle: Project Repository [https://github.com/TinyTapeout/tinytapeout-02](https://github.com/TinyTapeout/tinytapeout-02)
documentclass: scrartcl
date: \today{}
geometry: margin=2cm
fontsize: 14pt
mainfont: Latin Modern Sans
header-includes:
- \hypersetup{colorlinks=false,
          allbordercolors={0 0 0},
          pdfborderstyle={/S/U/W 1}}
---

\pagebreak

# Render of whole chip

![Full GDS](tinytapeout.png)

\pagebreak

# Projects 
## 0 : Test Inverter Project



* Author: Matt Venn
* Description: Inverts every line. This project is also used to fill any empty design spaces.
* [GitHub repository](https://github.com/TinyTapeout/tt03-test-invert)
* [Wokwi](https://wokwi.com/projects/357464855584307201) project
* [Extra docs]()
* Clock: 0 Hz
* External hardware: 

### How it works

Uses 8 inverters to invert every line.


### How to test

Setting the input switch to on should turn the corresponding LED off.


### IO

| # | Input        | Output       |
|---|--------------|--------------|
| 0 | a  | segment a |
| 1 | b  | segment b |
| 2 | c  | segment c |
| 3 | d  | segment d |
| 4 | e  | segment e |
| 5 | f  | segment f |
| 6 | g  | segment g |
| 7 | dot  | dot |

\pagebreak
## 2 : 7 Segment Life



* Author: icegoat9
* Description: Simple 7-segment cellular automaton
* [GitHub repository](https://github.com/icegoat9/tinytapeout03-7seglife)
* [Wokwi](https://wokwi.com/projects/357752736742764545) project
* [Extra docs](https://github.com/icegoat9/tinytapeout03-7seglife/blob/main/README.md)
* Clock: 0 Hz
* External hardware: None. Could add debounced momentary pushbuttons in parallel with dip switches 1,2,3 to make loading in new patterns and stepping through a run easier.

### How it works

See the [Wokwi gate layout and simulation](https://wokwi.com/projects/357752736742764545). At a high level...

* Seven flip-flops hold the cellular automaton's internal state, which is also displayed in the seven-segment display.
* Combinatorial logic generates the next state for each segment based on its neighbors, according to the ruleset...
  * Living segments with exactly one living neighbor (another segment that touches it end to end) survive, and all others die.
  * Dead segments with exactly two living neighbors come to life.
* When either the system clock or a user toggling the clock input go high, this new state is latched into the automaton's state.
* There's minor additional support logic to let the user manually shift in an initial condition and handle clock dividing.


### How to test

For full details and a few 'exercises for the reader', see the [github README](https://github.com/icegoat9/tinytapeout03-7seglife) doc link. But at a high level, assuming the IC is mounted on the standard tinytapeout PCB which provides dip switches, clock, and a seven-segment display for output...

* Set all dip switches off and the clock slide switch to the 'manual' clock side.
* Power on the system. An arbitrary state may appear on the 7-segment display.
* Set dip switch 4 on ('run mode').
* Toggle dip switch 1 on and off to advance the automaton to the next state, you should see the 7-segment display update.

If you want to watch it run automatically (which may quickly settle on an empty state or a static pattern, depending on start state)...

* Set the PCB clock divider to the maximum clock division (255). With a system clock of 6.25kHz, the clock input should now be ~24.5Hz.
* Set dip switches 5 and 7 on to add a reasonable additional clock divider (see docs for more details on a higher or lower divider).
* Set dip switch 4 on.
* Switch the clock slide switch to the 'system clock' side. The display should advance at roughly 1.5Hz if I've done math correctly.

If you want to load an initial state...

* Set dip switch 4 off ('load mode').
* Toggle dip switches 2 and/or 3 on and off seven times total, to shift in 0 and 1 values to the automaton internal state.
* Set dip switch 4 on and run manually or automatically as above.


### IO

| # | Input        | Output       |
|---|--------------|--------------|
| 0 | clock  | 7segmentA |
| 1 | load0  | 7segmentB |
| 2 | load1  | 7segmentC |
| 3 | runmode  | 7segmentD |
| 4 | clockdiv8  | 7segmentE |
| 5 | clockdiv4  | 7segmentF |
| 6 | clockdiv2  | 7segmentG |
| 7 | unused  | 7segmentDP |

\pagebreak
## 3 : Another Piece of Pi



* Author: Meinhard Kissich, EAS Group, Graz University of Technology
* Description: This design takes up the idea of James Ross [1], who submitted a circuit to Tiny Tapeout 02 that stores and outputs the first 1024 decimal digits of the number Pi (including the decimal point) to a 7-segment display. In contrast to his approach, a densely packed decimal encoding is used to store the data. With this approach, 1400 digits can be stored and output within the design area of 150um x 170um. However, at 1400 decimals and utilization of 38.99%, the limitation seems to be routing. Like James, I'm also interested to hear about better strategies to fit more information into the design with synthesizable Verilog code. [1] https://github.com/jar/tt02_freespeech
* [GitHub repository](https://github.com/meiniKi/tt03-another-piece-of-pi)
* HDL project
* [Extra docs]()
* Clock: 0 Hz
* External hardware: 7-segment display

### How it works

The circuit stores each triplet of decimals in a 10-bit vector encoded as densely packed decimals. An index vector selects the current digits to be output to the 7-segment display. It consists of an upper part `index[11:2]` that selects the triplet and a lower part `index[1:0]` that specifies the digit within the triplet. First, the upper part decides on the triplet, which is then decoded into three decimals. Afterwards, the lower part selects one of the three decimals to be decoded into 7-segment display logic and applied to the outputs. The index is incremented at each primary clock edge. However, when the lower part equals three, i.e., `index[1:0]==1'b10`, two is added, as the triplet consists of three (not four) digits.

- `index == 'b0000000000|00`: triplet[0], digit 0 within triplet  
- `index == 'b0000000000|01`: triplet[0], digit 1 within triplet  
- `index == 'b0000000000|10`: triplet[0], digit 2 within triplet  
- `index == 'b0000000001|00`: triplet[1], digit 0 within triplet  
- `index == 'b0000000001|01`: triplet[1], digit 1 within triplet  
- `index == 'b0000000001|10`: triplet[1], digit 2 within triplet

There is one exception to the rule above: the decimal point. Another multiplexer at the input of the 7-segment decoder can either forward a digit from the decoded tripled or a constant -- the decimal point. Once the lower part of the index counter, i.e., `index[1:0]` reaches `2'b10` for the first time, the multiplexer selects the decimal point and pauses incrementing the index for one clock cycle.

- `index == 'b0000000000|00`: triplet[0], digit 0 within triplet  
- `index == 'b0000000000|01`: triplet[0], decimal point
- `index == 'b0000000000|01`: triplet[0], digit 1 within triplet  
- `index == 'b0000000000|10`: triplet[0], digit 2 within triplet  
- `index == 'b0000000001|00`: triplet[1], digit 0 within triplet  


### How to test

For simulation, please use the provided testbench and Makefile. It is important to run the `genmux.py` Python script first, as it generates the test vectors required by the Verilog testbench. For testing the physical chip, release the reset and compare the digits of Pi against a reference.


### IO

| # | Input        | Output       |
|---|--------------|--------------|
| 0 | clk  | segment a |
| 1 | reset  | segment b |
| 2 | none  | segment c |
| 3 | none  | segment d |
| 4 | none  | segment e |
| 5 | none  | segment f |
| 6 | none  | segment g |
| 7 | none  | decimal LED |

\pagebreak
## 4 : Wormy



* Author: nqbit
* Description: MC Wormy Pants squirms like a worm and grows just as fast.
* [GitHub repository](https://github.com/nqbit/wormy)
* HDL project
* [Extra docs](https://github.com/nqbit/wormy)
* Clock: 300 Hz
* External hardware: 

### How it works

Wormy is a very simple, addictive last person video game. This last person,
open-world game takes you down the path of an earthworm. Wormy's world is
made up of a 4x4 grid represented by 3x16-bit arrays: Direction[0],
Direction[1], and Occupied. The Direction[x] maps keep track of which way a
segment of worm moves, if it is on, and Occupied keeps track of if the grid
location is occupied.

Example Occupied Grid:

```
   _________
  | X X X X |
  |       X |
  |       X |
  |_________|
```

In addition to direction and occupied there are also pointers to the head
and the tail. The same grid would look something like the following:

Example Occupied Grid with head(H) and tail(T) highlighted:

```
   _________
  | T X X X |
  |       X |
  |       H |
  |_________|
```

BOOM! Wormy shouldn't run into itself. If its head hits any part of its
body, that causes a collision. There is a collision if the location of the
Wormy's head is occupied by another segment of the Wormy. To determine
this, we keep track of the worm location, and specifically the current and
future locations of the worm head (H) and tail (T). If the future location
of H will occupy a location that will already be occupied, this causes a
collision.

This is made a bit trickier with growth (see below), because if the future
state of H is set to occupy the current state of T - there is only a
collision if growth is set to occur in the next cycle, so be careful if you
plan to have Wormy chase its tail! SPLAT!

NOM NOM! Wormy eats the tasty earth around it and grows. Every so often
Wormy, after having eaten all of its lunch, grows a whole segment. During a
growth cycle, the state of T simply persists (remains occupied and heading
in the same direction as it is).

Last Person Input - see user_input.v
To move Wormy along, the last player needs to push buttons to help Wormy
find more tasty earth: up, right, down or left.

Buttons are nasty little bugs in general. When pushed the button generates
an analog signal that might not look exactly like a single rising edge.

It might look something like this:

```
                                          xxxxxxxxxxxxxxxxx
                                        xx
                                        x
                                        x
                         x              x
                         x             x
                         x             x
                         x            x
                         x    xx x    x
                         x    xxxx    x
                         x    x xx    x
                         x    x  x   x
                         x    x  x   x
                        xx    x  x   x
                        xxx   x  x   x
                        x xx  x   x  x
                       x   x x    x  x
                       x   x x    xx x
                      x     xx     x x
    xxxxxxxxxxxxxxxxxxx             x
```

In order to help protect our logic from this scary looking signal that
might introduce metastability (<- WHAT?), we can filter it with a couple
flippy-floppies and keep the metastability at bay. ARGH.

Once we have a clear pushed or not-pushed, we can suggest that Wormy move
in a specific direction. If the last player tries button mashing, Wormy
won't listen. Once a second Wormy checks what the last button press was and
tries really hard to go that way (see BOOM!).

Earthworms don't have eyes - see multiplexer.v
The game's display is made up of a 4x4 grid of LEDs controlled by a
multiplexer. Why multiplexing? With a multiplexed LED setup, we can control
more display units (LEDs), with a limited number of outputs (8 on this
TinyTapeout project).

To get multiplexing working the network of outputs is mapped to each
display unit. This allows us to manipulate assigned outputs to control the
state of each display unit, one at a time. We then cycle through each
display unit quickly enough to display a persistent image to the last
player.

Wires (A1-4, B1-4) map to each location on the game arena (4x4 grid):

```
  A1|   |   |   |
  __________________
  A2|   |   |   |
  __________________
  A3|   |   |   |
  __________________
  A4|   |   |   |
  __________________
    |B1 |B2 |B3 |B4
```

When B's voltage is OFF the LED's state changes to ON if A is also ON.
  - ON LED state: A(ON) — >| — B(OFF)
  - OFF LED state: A(ON) — >| — B(ON)

Example: The 3 filled squares below each represent a Wormy segment in the
ON state as controlled by the multiplexer. Notice how each is lighter than
the last. This is because the multiplexer cycles through each LED to update
the state, creating one persistent image even though the LEDS are not on
over the entire period of time.

```
  A1|   | O |   |
  __________________
  A2|   | o |   |
  __________________
  A3|   | . |   |
  __________________
  A4|   |   |   |
  __________________
    |B1 |B2 |B3 |B4
```

Another Example: If you enter a dark cave and point a flashlight straight
ahead at one point on the wall you have a very small visual field that is
contained within the beam of light. However, you can expand your visual
field in the cave by waving the flashlight back and forth across the wall.
Despite the fact that the beam is moving over individual points on the
wall, the entire wall can be seen at once. This is similar to the concept
used in the Wormy display, since the multiplexer changes the state of the
worm occupied locations to ON one at a time, but in a cycle. The result is
a solid image, made up of LEDs cycling through ON states to produce a
persistent image of Wormy (that beautiful Lumbricina).


### How to test

After reset, you should see a single pixel moving along the display and
it should grow every now and then.


### IO

| # | Input        | Output       |
|---|--------------|--------------|
| 0 | clock  | A0 - Multiplexer channel A to be tied to a an array of 16 multiplexed LEDs |
| 1 | reset  | A1 |
| 2 | button0  | A2 |
| 3 | button1  | A3 |
| 4 | button2  | B0 - Multiplexer channel B to be tied to a an array of 16 multiplexed LEDs |
| 5 | button3  | B1 |
| 6 | none  | B2 |
| 7 | none  | B3 |

\pagebreak
## 5 : Knight Rider Sensor Lights

![picture](projects/005/KITT.jpg)

* Author: Kolos Koblasz
* Description: The logic assertes output bits one by one, like KITT's sensor lights in Knight Rider.
* [GitHub repository](https://github.com/KolosKoblasz/tt03-knight_rider)
* HDL project
* [Extra docs]()
* Clock: 6000 Hz
* External hardware: Conect LEDs with ~1K-10K Ohm serial resistors to output pins and connect push button switches to Input[2] and Input[3] which drive the inputs with logic zeros when idle and with logic 1 when pressed. Rising edge on these inputs selects the next settings.

### How it works

Uses several counters, shiftregisters to create a moving light.
Input[2] and Input[3] can control speed and brightness respectively.


### How to test

After reset it starts moving the switched on LED.
By creating rising edges on Input[2] and Input[3] the two config spaces can be discovered. Input[0] is clk Input[1] is reset (1=reset on, 0=Reset off).
Simulated with 6KHz clock signal.


### IO

| # | Input        | Output       |
|---|--------------|--------------|
| 0 | clock  | LED 0 |
| 1 | reset  | LED 1 |
| 2 | speed control  | LED 2 |
| 3 | brightness control  | LED 3 |
| 4 | none  | LED 4 |
| 5 | none  | LED 5 |
| 6 | none  | LED 6 |
| 7 | none  | LED 7 |

\pagebreak
# Technical info

## Scan chain

All 250 designs are joined together in a long chain similiar to JTAG. We provide the inputs and outputs of that chain (see pinout below) externally, to the Caravel logic analyser, and to an internal scan chain driver.

The default is to use an external driver, this is in case anything goes wrong with the Caravel logic analyser or the internal driver.

The scan chain is identical for each little project, and you can [read it here](https://github.com/mattvenn/wokwi-verilog-gds-test/blob/main/template/scan_wrapper.v).

![block diagram](pics/block_diagram.png)

### Updating inputs and outputs of a specified design

A good way to see how this works is to read the FSM in the [scan controller](verilog/rtl/scan_controller/scan_controller.v).
You can also run one of the simple tests and check the waveforms. See how in the [scan chain verification](verification.md) doc.

* Signal names are from the perspective of the scan chain driver.
* The desired project shall be called DUT (design under test)

Assuming you want to update DUT at position 2 (0 indexed) with inputs = 0x02 and then fetch the output.
This design connects an inverter between each input and output.

* Set scan_select low so that the data is clocked into the scan flops (rather than from the design)
* For the next 8 clocks, set scan_data_out to 0, 0, 0, 0, 0, 0, 1, 0
* Toggle scan_clk_out 16 times to deliver the data to the DUT
* Toggle scan_latch_en to deliver the data from the scan chain to the DUT
* Set scan_select high to set the scan flop's input to be from the DUT
* Toggle the scan_clk_out to capture the DUT's data into the scan chain
* Toggle the scan_clk_out another 8 x number of remaining designs to receive the data at scan_data_in

![update cycle](pics/update_cycle.png)

*Notes on understanding the trace*

* There are large wait times between the latch and scan signals to ensure no hold violations across the whole chain. For the internal scan controller, these can be configured (see section on wait states below).
* The input looks wrong (0x03) because the input is incremented by the test bench as soon as the scan controller captures the data. The input is actually 0x02.
* The output in the trace looks wrong (0xFE) because it's updated after a full refresh, the output is 0xFD.

## Clocking

Assuming:

* 100MHz input clock
* 8 ins & 8 outs
* 2 clock cycles to push one bit through the scan chain (scan clock is half input clock rate)
* 250 designs
* scan controller can do a read/write cycle in one refresh

So the max refresh rate is 100MHz / (8 * 2 * 250) = 25000Hz.

## Clock divider

A rising edge on the set_clk_div input will capture what is set on the input pins and use this as a divider for an internal slow clock that can be provided to the first input bit.

The slow clock is only enabled if the set_clk_div is set, and the resulting clock is connected to input0 and also output on the slow_clk pin.

The slow clock is synced with the scan rate. A divider of 0 mean it toggles the input0 every scan. Divider of 1 toggles it every 2 cycles.
So the resultant slow clock frequency is scan_rate / (2 * (N+1)).

See the test_clock_div test in the [scan chain verification](verification.md).

## Wait states

This dictates how many wait cycle we insert in various state
of the load process. We have a sane default, but also allow
override externally.

To override, set the wait amount on the inputs, set the driver_sel inputs both high, and then reset the chip.

See the test_wait_state test in the [scan chain verification](verification.md).

## Pinout

    PIN     NAME                DESCRIPTION
    20:12   active_select       9 bit input to set which design is active
    28:21   inputs              8 inputs
    36:29   outputs             8 outputs
    37      ready               goes high for one cycle everytime the scanchain is refreshed
    10      slow_clk            slow clock from internal clock divider
    11      set_clk_div         enable clock divider
    9:8     driver_sel          which scan chain driver: 00 = external, 01 = logic analyzer, 1x = internal

    21      ext_scan_clk_out    for external driver, clk input
    22      ext_scan_data_out   data input
    23      ext_scan_select     scan select
    24      ext_scan_latch_en   latch
    29      ext_scan_clk_in     clk output from end of chain
    30      ext_scan_data_in    data output from end of chain

## Instructions to build GDS

To run the tool locally or have a fork's GitHub action work, you need the GH_USERNAME and GH_TOKEN set in your environment.

GH_USERNAME should be set to your GitHub username.

To generate your GH_TOKEN go to https://github.com/settings/tokens/new . Set the checkboxes for repo and workflow.

To run locally, make a file like this:

    export GH_USERNAME=<username>
    export GH_TOKEN=<token>

And then source it before running the tool.

### Fetch all the projects

This goes through all the projects in project_urls.py, and fetches the latest artifact zip from GitHub. It takes the verilog, the GL verilog, and the GDS and copies 
them to the correct place.

    ./configure.py --clone-all --fetch-gds

### Configure Caravel

Caravel needs the list of macros, how power is connected, instantiation of all the projects etc. This command builds these configs and also makes the README.md index.

    ./configure.py --update-caravel

### Build the GDS

To build the GDS and run the simulations, you will need to install the Sky130 PDK and OpenLane tool.
It takes about 5 minutes and needs about 3GB of disk space.

    export PDK_ROOT=<some dir>/pdk
    export OPENLANE_ROOT=<some dir>/openlane
    cd <the root of this repo>
    make setup 

Then to create the GDS:

    make user_project_wrapper

## Changing macro block size

After working out what size you want:

* adjust configure.py in `CaravelConfig.create_macro_config()`.
* adjust the PDN spacing to match in openlane/user_project_wrapper/config.tcl:
    * ```set ::env(FP_PDN_HPITCH)```
    * ```set ::env(FP_PDN_HOFFSET)```


\pagebreak
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

\pagebreak
# Sponsored by

[![efabless](efabless.png)](https://efabless.com/)

# Team

Tiny Tapeout would not be possible without a lot of people helping. We would especially like to thank:

* Uri Shaked for [wokwi](https://wokwi.com/) development and lots more
* [Sylvain Munaut](https://twitter.com/tnt) for help with scan chain improvements
* [Mike Thompson](https://www.linkedin.com/in/michael-thompson-0a581a/) for verification expertise
* [Jix](https://twitter.com/jix_) for formal verification support
* [Proppy](https://twitter.com/proppy) for help with GitHub actions
* [Maximo Balestrini](https://twitter.com/maxiborga) for all the amazing renders and the interactive GDS viewer
* James Rosenthal for coming up with digital design examples
* All the people who took part in [TinyTapeout 01](/runs/tt01) and volunteered time to improve docs and test the flow
* The team at [YosysHQ](https://www.yosyshq.com/) and all the other open source EDA tool makers
* [Efabless](https://efabless.com/) for running the shuttles and providing OpenLane and sponsorship
* [Tim Ansell and Google](https://www.youtube.com/watch?v=EczW2IWdnOM) for supporting the open source silicon movement
* [Zero to ASIC course](https://zerotoasiccourse.com/) community for all your support
