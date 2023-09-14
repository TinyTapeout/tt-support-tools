# Chip Errata

This section lists the known issues with the chip and suggests workarounds where possible.

## Undefined pin states

The state of the bidirectional pins and output pins is not defined when no design is selected. This means that the bidirectional pins may be configured as outputs, with either high or low output values, or as inputs. Take care to avoid shorting the bidirectional pins to other outputs or to VDD or GND when no design is selected. As a workaround, you can connect these pins to external devices or other pins through a resistor.
