// SPDX-License-Identifier: Apache2.0
`timescale 1ns / 1ps
`default_nettype none

module test_wokwi ();
  wire [7:0] io_out;
  wire [7:0] io_in;

  tt_um_wokwi_WOKWI_ID dut (
  `ifdef GL_TEST
      .vccd1( 1'b1),
      .vssd1( 1'b0),
  `endif
      .io_in (io_in),
      .io_out(io_out)
  );

  initial begin
    $dumpfile("wokwi_tb_WOKWI_ID.vcd");
    $dumpvars(0, test_wokwi);
  end
endmodule
