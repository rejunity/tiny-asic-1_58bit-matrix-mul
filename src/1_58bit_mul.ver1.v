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
    reg  signed [16:0] accumulators      [3:0];
    wire signed [16:0] accumulators_next [3:0];
    reg  signed [16:0] out_queue         [3:0];
    reg          [1:0] out_queue_index;

    integer n;
    // // clocked accumulators[]
    // always @(posedge clk)
    //     for (n = 0; n < 4; n = n + 1)
    //         if (reset | reset_accumulators)
    //             accumulators[n] <= 0;
    //         else
    //             accumulators[n] <= accumulators_next[n];

    // // clocked out_queue[]
    // always @(posedge clk)
    //     for (n = 0; n < 4; n = n + 1)
    //         // if (reset)
    //         //     out_queue[n] <= 0;
    //         // else
    //             if (copy_accumulator_values_to_out_queue)
    //                 out_queue[n]    <= accumulators[n]; //accumulators_next[n];
            
    // // clocked out_queue_index[]
    // always @(posedge clk)
    //     if (reset | restart_out_queue)
    //         out_queue_index <= 0;
    //     else
    //         out_queue_index <= out_queue_index + 1;

    always @(posedge clk)
        for (n = 0; n < 4; n = n + 1) begin
            if (reset | reset_accumulators)
                accumulators[n] <= 0;
            else
                accumulators[n] <= accumulators_next[n];

            if (reset | restart_out_queue)
                out_queue_index <= 0;
            else
                out_queue_index <= out_queue_index + 1;

            if (copy_accumulator_values_to_out_queue)
                out_queue[n]    <= accumulators_next[n];
        end

    genvar i, j;
    generate
    for (j = 0; j < 1; j = j + 1)
        for (i = 0; i < 4; i = i + 1) begin : mac
            wire [16:0] value_curr  = accumulators     [i*1+j];
            wire [16:0] value_next  = accumulators_next[i*1+j];
            wire [16:0] value_queue = out_queue        [i*1+j];
            assign accumulators_next[i*1+j] =
                 reset ? 0 :
                 in_left_zero[i] ? accumulators[i*1+j] + 0 :
                (in_left_sign[i] ? accumulators[i*1+j] - $signed(in_top) :
                                   accumulators[i*1+j] + $signed(in_top));
        end
    endgenerate

    assign out = out_queue[out_queue_index] >> 8;
endmodule
