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
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

  reg [7:0] rom_data[0:255];

  initial begin
    $readmemh(`ROM_VMEM_PATH, rom_data);
  end

  // The address counter, only used when rst_n is low
  reg  [7:0] addr_counter;
  wire [7:0] selected_addr = rst_n ? ui_in : addr_counter;

  assign uo_out  = rom_data[selected_addr];
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;


  always @(posedge clk or posedge rst_n) begin
    if (rst_n) begin
      addr_counter <= 0;
    end else begin
      addr_counter <= addr_counter + 1;
    end
  end

endmodule  // tt_um_chip_rom
