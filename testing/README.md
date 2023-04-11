### Wokwi/TinyTapeout testing system ###


A system has been devised to allow for simplified verification and testing of wokwi projects.

In this initial iteration, the process basically involves creating a 'truth table' type description of desired inputs and expected outputs, which allows for testing of both combinatorial and sequential/clocked circuits.

The system is designed to allow for simple extensions to this base functionality: the testing framework itself will be described below to assist in expanding it to encompass additional tests and validation of wokwi or other TT projects.


## Truth-table system ##

In its simplest incarnation, the truth-table defines a set of inputs provided to the circuit and describes the expected outputs.

The table itself is written as markdown, consisting of

 * a header
 * a separator
 * the table rows
using markdown formatting.  Eg

| inputs    |  outputs  |
|-----------|-----------|
| 1111 0000 | xxxx 1100 |

etc


Inputs are in the left-side column, expected outputs on the right, specified
as MSB (i.e. bit 7 to 0, from left to right).
  
Any bits specified as 'x' or '-' are treated as "don't change" for
inputs and "don't care" for outputs. 


The header is ignored, as are whitespaces, so you may format as appropriate.
Each row must have a least 8 non-whitespace bit specifications per column.  E.g.
for a 2 bit adder, a table might consist of



|       Cin   B    A  |  Cout    S  |
|---------------------|-------------|
| -----  0    0    0  |-- 0 ---- 0  |
| -----  0    0    1  |-- 0 ---- 1  |
| -----  0    1    0  |-- 0 ---- 1  |
| -----  0    1    1  |-- 1 ---- 0  |
| -----  1    0    0  |-- 0 ---- 1  |
| -----  1    0    1  |-- 1 ---- 0  |
| -----  1    1    0  |-- 1 ---- 0  |
| -----  1    1    1  |-- 1 ---- 1  |





A ‘t’ or ‘T’ bit will be toggled from whatever it was before.

An empty output column will apply the input, but not perform any test (i.e. behave the same as 8 ‘x’/’-’).



### Clocked designs ####

In addition to maintaining state for toggling the clock, one or more ‘c’ bits in an input column will cause the system to:

	1) Set any bits specified, including toggling an “t” bits, without changing the ‘c’ bits (setup);
	2) It will then toggle all ‘c’ bits, inverting them, but not changing anything else from previous step; and finally
	3) It will toggle the ‘c’ bits again, returning them to their original state.
	
This means setup and hold times are respected and signals may be clocked in with a single row in the table, rather than having 3.  






Any entry with a bit set to 'c' will:
* setup any specified bits (0 or 1) and toggle any bits as required
* then toggle (i.e. invert) the clock bit(s), without changing anything else
* then re-toggle the same clock bit(s), returning them to their original state


|IN:  CBA  RC  |    output    | comment   |
|--------------|--------------|-----------|
| 000 000  00  | -- ----- -   | init      |
| --- ---  1c  | -- ----- -   | reset     |
| --- ---  0c  | -- ----- -   |           |
| --- 111  -c  | -- 11100 -   |           |
| --- 110  -c  | -- 11111 -   | success   |
| --- 000  tc  | -- ----- -   | reset     |
| --- ---  tc  | -- 11100 -   | locked    |
| --- 111  -c  | -- 11100 -   | bad combo |
| --- 100  -c  | -- 11100 -   | bad combo |
| --- 101  -c  | -- 11100 -   | bad combo |
| --- 100  -c  | -- 11100 -   | bad combo |
| --- 110  -c  | -- 11111 -   | success   |
| --- 000  -c  | -- 11111 -   | still open|
| --- ---  1c  | -- 11100 -   | reset     |



=============================
Note that using ‘c’ is optional.  A row like


|IN:  CBA  RC  |    output    | comment   |
|--------------|--------------|-----------|
| --- 110  -c  | -- 11111 -   | success   |


Could be done manually, with


|IN:  CBA  RC  |    output    | comment   |
|--------------|--------------|-----------|
| --- 110  --  | -- ----- -   | set combo |
| --- ---  -1  | -- ----- -   | clock     |
| --- ---  -0  | -- 11111 -   | success   |


###  Test framework function ###

The tt-tools system, in addition to downloading verilog and JSON for wokwi projects, now attempts to download a file name truthtable.md.

If this file is found, it assumes that te truthtable test must be run.  To do this, the system now:

	1) copies any directories found under testing/lib to the src/ directory, assuming these are python support packages; and
	2) for each file in testing/src-tpl it will read in the file, replace any instance of WOKWI_ID with the appropriate id, and then write out a corresponding file into the actual src/ directory.

From this point, all that should be required is to run a make from within the src directory to launch cocotb with the test necessary to put the table through its paces.


2023-04-06 Pat Deegan


