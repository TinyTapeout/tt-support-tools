# Silicon Validation

TT03 silicon was received in January 2024. The only differences expected between TT02 and TT03 were the designs and an improved scanchain. See the section on the [scan chain](#scan-chain) for more information on the changes. 

In TT02 the top speed was limited to around 20 MHz due to the long scan chain and using 2 buffers for each design. The trace shows input clock in yellow and output at the end of the chain in blue.

![tt02 clock out](pics/tt02_clock_out.png)

The TT03 trace shows a much more symmetric output pulse.

![tt03 clock out](pics/tt03_clock_out.png)

The TT03 scanchain was tested up to 40 MHz. The trace shows input clock in blue and output at the end of the chain in yellow.

![40M](pics/scan40M.png)

## Scan chain frequency for TT03

It's likely the chain could be run faster with an external driver, but because the RISCV CPU inside Caravel is being used to setup the GPIOs, it also needs to work at the chosen frequency. Caravel works up to 50MHz, so 40MHz was chosen as a safe lower value for the new oscillator frequency.

This means that a design's IO will be updated at 8 KHz, and hence a maximum input clock of 4 KHz.
