// SPDX-License-Identifier: Apache2.0
`timescale 1ns / 1ps
`default_nettype none

module test_wokwi ();
    reg  clk; 			// clock
    reg  rst_n;			// not reset
    reg  ena;			// enable - goes high when design is selected
    reg  [7:0] ui_in;		// dedicated inputs
    reg  [7:0] uio_in;		// IOs: input path
    
    wire [7:0] uo_out;		// dedicated outputs
    wire [7:0] uio_out;		// IOs: Output path
    wire [7:0] uio_oe;		// IOs: Enable path (active high: 0=input, 1=output)

  tt_um_wokwi_WOKWI_ID dut (
  `ifdef GL_TEST
      .vccd1( 1'b1),
      .vssd1( 1'b0),
  `endif
      .ui_in      (ui_in),    
      .uo_out     (uo_out),   
      .uio_in     (uio_in),   
      .uio_out    (uio_out),  
      .uio_oe     (uio_oe),   
      .ena        (ena),      
      .clk        (clk),     
      .rst_n      (rst_n)    
  );

  initial begin
    $dumpfile("wokwi_tb_WOKWI_ID.vcd");
    $dumpvars(0, test_wokwi);
  end
endmodule
