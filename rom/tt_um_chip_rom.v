/*
 * tt_um_chip_rom.v
 *
 * ROM module for Tiny Tapeout chips. The layout of the ROM is documented at
 * https://github.com/TinyTapeout/tt-chip-rom/blob/main/docs/info.md.
 *
 * Author: Uri Shaked
 */

`default_nettype none

`ifndef ROM_VMEM_PATH
    `define ROM_VMEM_PATH "rom.vmem"
`endif

module tt_um_chip_rom (
	input  wire [7:0] ui_in,	// Dedicated inputs
	output wire [7:0] uo_out,	// Dedicated outputs
	input  wire [7:0] uio_in,	// IOs: Input path
	output wire [7:0] uio_out,// IOs: Output path
	output wire [7:0] uio_oe,	// IOs: Enable path (active high: 0=input, 1=output)
	input  wire       ena,
	input  wire       clk,
	input  wire       rst_n
);

	reg [7:0] rom_data [0:255];

  initial begin
		$readmemh(`ROM_VMEM_PATH, rom_data);
	end
	
	assign uo_out  = rom_data[ui_in];
	assign uio_out = 8'h00;
	assign uio_oe  = 8'h00;

endmodule // tt_um_chip_rom