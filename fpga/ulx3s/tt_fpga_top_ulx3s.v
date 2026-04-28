/*
 * Copyright (c) 2026 gojimmypi
 * SPDX-License-Identifier: Apache-2.0
 *
 * file: tt_fpga_top_ulx3s.v
 *
 * This is a ULX3S-specific wrapper for the TT module defined in /project.v
 * It maps the standard TT pin interface to the actual pins on the ULX3S board, 
 * and includes some simple logic to synchronize the UART RX signal and 
 * optionally loop back the UART TX for testing.
 */
`default_nettype none
`timescale 1ns/1ps

module tt_fpga_top (
    input  wire        clk_25mhz,
    input  wire [6:0]  btn,
    output wire [7:0]  led,
    input  wire        gp0,
    output wire        gp1
);

    wire [7:0] ui_in;
    wire [7:0] uio_in;
    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;

    wire rst_n;
    wire ena;

    reg uart_rx_meta;
    reg uart_rx_sync;

    /* The BTN0 "PWR" on the ULX3S is used for reset. 
     * It is active-low, so we can connect it directly to rst_n. */
    assign rst_n = btn[0];

    assign ena   = 1'b1;

    /* Optional UART support - enable by defining UART_ENABLED in your project.v */
    `ifdef UART_ENABLED
        /* See example UART: https://github.com/gojimmypi/ttsky-UART-FSM-TRNG-Lab */

        wire uart_tx_pin;
        wire uart_rx_pin;

        assign uart_rx_pin = gp0;
        assign gp1         = uart_tx_pin;

        always @(posedge clk_25mhz) begin
            uart_rx_meta <= uart_rx_pin;
            uart_rx_sync <= uart_rx_meta;
        end

        // Map UART RX into TT input
        assign ui_in = {4'b0000, uart_rx_sync, 3'b000};

        assign uio_in = 8'h00;
    `endif

    /* instantiate the main user_project from TT module in /project.v */
    __tt_um_placeholder user_project
    (
        .ui_in(ui_in),
        .uo_out(uo_out),
        .uio_in(uio_in),
        .uio_out(uio_out),
        .uio_oe(uio_oe),
        .ena(ena),
        .clk(clk_25mhz),
        .rst_n(rst_n)  // TODO - add a reset button and connect it here instead of hardcoding rst_n=1
    );

    `ifdef FORCE_LOOPBACK
        // Loopback UART TX to RX for testing
        initial $display("FORCE_LOOPBACK ENABLED");
        assign uart_tx_pin = uart_rx_sync;

        // Optionally ensure your project is not submitted in loopback mode
        // MODULE_FORCE_LOOPBACK_MUST_NOT_BE_ENABLED u_stop ();

    `else
        initial $display("FORCE_LOOPBACK DISABLED");
        assign uart_tx_pin = uo_out[4];
    `endif /* FORCE_LOOPBACK */

    // Optional Debug
    assign led = uo_out;
    // assign led = 8'h00;

endmodule

`default_nettype wire
