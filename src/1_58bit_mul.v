/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */


// TODOs:
//  * pack ternary 
//  * signal to shift accumulators by 1
//  * multiply by beta
//  * handle both signed & unsigned inputs

`define default_netname none

module tt_um_rejunity_1_58bit (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // will go high when the design is enabled
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
    assign uio_oe  = 0;         // bidirectional IOs set to INPUT
    assign uio_out = 0;         // drive bidirectional IO outputs to 0

    wire reset = ! rst_n;

    // decode ternary weights
    wire [3:0] weights_zero = ~ { |ui_in[1:0], |ui_in[3:2],  |ui_in[5:4], |ui_in[7:6] };
    wire [3:0] weights_sign =   {  ui_in[1  ],  ui_in[3  ],   ui_in[5  ],  ui_in[7  ] };

    // wire [3:0] weights_zero = ~ { |ui_in[7:6], |ui_in[5:4],  |ui_in[3:2], |ui_in[1:0] };
    // wire [3:0] weights_sign =   {  ui_in[7  ],  ui_in[5  ],   ui_in[3  ],  ui_in[1  ] };

    // @TODO: special weight to initiate readout
    wire       initiate_read_out = !ena;
    
    systolic_array systolic_array(
        .clk(clk),
        .reset(reset),

        .in_left_zero(weights_zero),
        .in_left_sign(weights_sign),
        .in_top(uio_in),
        .reset_accumulators(initiate_read_out),
        .copy_accumulator_values_to_out_queue(initiate_read_out),
        .restart_out_queue(initiate_read_out),
        
        .out(uo_out)
    );

endmodule

// module systolic_element (
//     input wire zero,
//     input wire sign,
//     input wire arg
// )

module systolic_array (
    input  wire       clk,
    input  wire       reset,

    input  wire [3:0] in_left_zero,
    input  wire [3:0] in_left_sign,
    input  wire [7:0] in_top,
    input  wire       reset_accumulators,
    input  wire       copy_accumulator_values_to_out_queue,
    input  wire       restart_out_queue,
    //input wire [2:0] apply_shift_to_out,
    //input wire       apply_relu_to_out,

    output wire [7:0] out
);
    localparam SLICES = 2;
    localparam W = 1 * SLICES;
    localparam H = 4 * SLICES;

    reg [H  -1:0] arg_left_zero;
    reg [H  -1:0] arg_left_sign;
    reg [W*8-1:0] arg_top;
    // wire [H  -1:0] arg_left_zero = in_left_zero;
    // wire [H  -1:0] arg_left_sign = in_left_sign;
    // wire [W*8-1:0] arg_top = in_top;

    reg                slice_counter;
    reg  signed [16:0] accumulators      [W*H-1:0];
    wire signed [16:0] accumulators_next [W*H-1:0];
    reg  signed [16:0] out_queue         [W*H-1:0];
    reg          [1:0] out_queue_index;

    integer n;
    always @(posedge clk) begin
        if (reset)
            slice_counter <= 0;
        else if (SLICES > 1)
            slice_counter <= slice_counter + 1;

        if (reset | restart_out_queue)
            out_queue_index <= 0;
        else
            out_queue_index <= out_queue_index + 1;

        if (reset) begin
            arg_left_zero <= 0;
            arg_left_sign <= 0;
            arg_top <= 0;
        end else begin
            // arg_left_zero <= in_left_zero;
            // arg_left_sign <= in_left_sign;
            // arg_top <= in_top;

            arg_left_zero[slice_counter*4 +: 4] <= in_left_zero;
            arg_left_sign[slice_counter*4 +: 4] <= in_left_sign;
            arg_top[slice_counter*8 +: 8] <= in_top;
        end

        for (n = 0; n < W*H; n = n + 1) begin
            if (reset | reset_accumulators)
                accumulators[n] <= 0;
            else
                accumulators[n] <= accumulators_next[n];

            if (copy_accumulator_values_to_out_queue)
                out_queue[n]    <= accumulators_next[n];
        end
    end

    genvar i, j;
    generate
    for (j = 0; j < W; j = j + 1)
        for (i = 0; i < H; i = i + 1) begin : mac
            wire [16:0] value_curr  = accumulators     [i*W+j];
            wire [16:0] value_next  = accumulators_next[i*W+j];
            wire [16:0] value_queue = out_queue        [i*W+j];
            wire pass_through = (j != slice_counter) | arg_left_zero[i];
            wire signed [7:0] addend = $signed(arg_top[j*8 +: 8]);
            assign accumulators_next[i*W+j] =
                 reset            ? 0 :
                 pass_through     ? accumulators[i*1+j] + 0 :
                (arg_left_sign[i] ? accumulators[i*1+j] - addend :
                                    accumulators[i*1+j] + addend);
        end
    endgenerate

    assign out = out_queue[out_queue_index] >> 8;
endmodule
