/*
 * Copyright (c) 2024 ReJ aka Renaldas Zioma
 * SPDX-License-Identifier: Apache-2.0
 */

// TODOs:
//  * test overlap between computations and readouts
//  * free ena from initiating readouts
//  * special weights 243..255 can be used to   a) initiate readout,
//                                              b) shift accumulators by 1,
//                                              c) set beta&gamma,
//                                              d) choose signed/unsigned inputs,
//                                              e) handle overflow or ReLU
//  * separate signal to shift accumulators by 1
//  * multiply by gamma and add beta
//  * handle both signed & unsigned inputs
//  * handle overflows
//  * ReLU
//  * parametrizalbe systolic_array
//  * 4-bit input support
// DONE:
//  + remove indexed memory access in out_queue and accumulators/accumulators_next
//  + get rid of (slice_count - 1) wait once indexed memory access is removed
//  + remove "reset  ? 0 :" from the accumulator_next

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

    // decode ternary weights - 4 ternary weights per byte
    // wire [3:0] weights_zero = ~ { |ui_in[1:0], |ui_in[3:2],  |ui_in[5:4], |ui_in[7:6] };
    // wire [3:0] weights_sign =   {  ui_in[1  ],  ui_in[3  ],   ui_in[5  ],  ui_in[7  ] };
    // -----------------------------------------------------
    // wire [3:0] weights_zero = ~ { |ui_in[7:6], |ui_in[5:4],  |ui_in[3:2], |ui_in[1:0] };
    // wire [3:0] weights_sign =   {  ui_in[7  ],  ui_in[5  ],   ui_in[3  ],  ui_in[1  ] };

    // unpack ternary weights - 5 ternary weights per byte
    wire [4:0] weights_zero;
    wire [4:0] weights_sign;
    unpack_ternary_weights unpack_ternary_weights(
        .packed_weights(ui_in),
        .weights_zero(weights_zero),
        .weights_sign(weights_sign)
    );

    // @TODO: special weight to initiate readout
    wire       initiate_read_out = !ena;
    
    systolic_array systolic_array (
        .clk(clk),
        .reset(reset),

        .in_left_zero(weights_zero),
        .in_left_sign(weights_sign),
        .in_top(uio_in),

        .restart_inputs(initiate_read_out),
        .reset_accumulators(initiate_read_out),
        .copy_accumulator_values_to_out_queue(initiate_read_out),
        .restart_out_queue(initiate_read_out),
        
        .out(uo_out)
    );

endmodule

module systolic_array #(
    parameter integer SLICES = `COMPUTE_SLICES
) (
    input  wire       clk,
    input  wire       reset,

    input  wire [4:0] in_left_zero,
    input  wire [4:0] in_left_sign,
    input  wire [7:0] in_top,
    input  wire       restart_inputs,
    input  wire       reset_accumulators,
    input  wire       copy_accumulator_values_to_out_queue,
    input  wire       restart_out_queue,
    //input wire      apply_shift_to_accumulators,
    //input wire      apply_relu_to_out,

    output wire [7:0] out
);
    localparam SLICE_BITS = $clog2(SLICES);
    localparam SLICES_MINUS_1 = SLICES - 1;
    localparam W = 1 * SLICES;
    localparam H = 5 * SLICES;

    // Double buffer inputs
    // xxx_curr - arguments that are fed into MAC (multiply-accumulate) units
    // xxx_next - where the inputs are written to
    // once slice_counter reaches 0, xxx_next is flushed into xxx_curr
    reg [H  -1:0] arg_left_zero_curr;
    reg [H  -1:0] arg_left_sign_curr;
    reg [W*8-1:0] arg_top_curr;

    reg [H  -1:0] arg_left_zero_next;
    reg [H  -1:0] arg_left_sign_next;
    reg [W*8-1:0] arg_top_next;

    reg  [SLICE_BITS-1:0] slice_counter;
    reg  signed [16:0] accumulators      [W*H-1:0];
    wire signed [16:0] accumulators_next [W*H-1:0];
    reg  signed [16:0] out_queue         [W*H-1:0];

    integer n;
    always @(posedge clk) begin
        if (reset | restart_inputs | slice_counter == SLICES_MINUS_1)
            slice_counter <= 0;
        else
            slice_counter <= slice_counter + 1;

        if (reset) begin
            arg_left_zero_next <= 0;
            arg_left_sign_next <= 0;
            arg_top_next <= 0;
        end else begin // write current inputs in_xxx into the xxx_next
            arg_left_zero_next[H-1 -: 5] <= in_left_zero;
            arg_left_sign_next[H-1 -: 5] <= in_left_sign;
            arg_top_next    [W*8-1 -: 8] <= in_top;

            if (SLICES > 1) begin // shift xxx_next for the next input
                arg_left_zero_next[H-1-5 : 0] <= arg_left_zero_next[H-1 : 5];
                arg_left_sign_next[H-1-5 : 0] <= arg_left_sign_next[H-1 : 5];
                arg_top_next    [W*8-1-8 : 0] <= arg_top_next    [W*8-1 : 8];
            end
        end

        if (slice_counter == 0) begin // xxx_next is flushed into xxx_curr,
                                      // once slice_counter reaches 0
            arg_left_zero_curr <= arg_left_zero_next;
            arg_left_sign_curr <= arg_left_sign_next;
            if (SLICES > 1)
                arg_top_curr <= {arg_top_next[7:0], arg_top_next[W*8-1: 8]};
            else
                arg_top_curr <= arg_top_next;
        end else begin // shift top systolic array arguments every clock cycle
            if (SLICES > 1)
                arg_top_curr <= {8'd0, arg_top_curr[W*8-1: 8]};
        end
        
        // The following loop must be unrolled, otherwise Verilator
        // will treat <= assignments inside the loop as errors
        // See similar bug report and workaround here:
        //   https://github.com/verilator/verilator/issues/2782
        // Ideally unroll_full Verilator metacommand should be used,
        // however it is supported only from Verilator 5.022 (#3260) [Jiaxun Yang]
        // Instead BLKLOOPINIT errors are suppressed for this loop
        /* verilator lint_off BLKLOOPINIT */
        for (n = 0; n < W*H; n = n + 1) begin
            if (reset | reset_accumulators)
                accumulators[n] <= 0;
            else
                accumulators[n] <= accumulators_next[n];

            if (copy_accumulator_values_to_out_queue) begin
                // To compensate accumulators_next 'being ahead' (shifted by 1 after computation):
                // (e.g. SLICES=4)
                // o[0] <= acc_n[3], o[1] <= acc_n[0], o[2] <= acc_n[1], o[3] <= acc_n[2]
                // o[4] <= acc_n[7], o[5] <= acc_n[4], o[6] <= acc_n[5], o[7] <= acc_n[6]
                if (n%W == 0)
                    out_queue[n] <= accumulators_next[n+W-1];
                else
                    out_queue[n] <= accumulators_next[n-1];

                // Alternatively the following code can be used
                // if additional (slice_counter-1) wait cycles are introduced
                // out_queue[n] <= accumulators_next[n];
            end else if (n > 0)
                out_queue[n-1]  <= out_queue[n];
        end
        /* verilator lint_on BLKLOOPINIT */
    end

    genvar i, j;
    generate
    for (j = 0; j < W; j = j + 1)
        for (i = 0; i < H; i = i + 1) begin : mac
            wire zero = arg_left_zero_curr[i];
            wire sign = arg_left_sign_curr[i];
            wire signed [7:0] addend = $signed(arg_top_curr[7:0]);
            if (j == 0) begin : compute
                assign accumulators_next[i*W+W-1] =
                     zero   ? accumulators[i*W+j] + 0 :
                    (sign   ? accumulators[i*W+j] - addend :
                              accumulators[i*W+j] + addend);
            end else begin : shift
                assign accumulators_next[i*W+j-1] =
                              accumulators[i*W+j];
            end

            // for debugging purposes in wave viewer
            wire [16:0] value_curr  = accumulators     [i*W+j];
            wire [16:0] value_next  = accumulators_next[i*W+j];
            wire [16:0] value_queue = out_queue        [i*W+j];
        end
    endgenerate

    assign out = out_queue[0] >> 8;
    // assign out = out_queue[0][7:0];
endmodule

module unpack_ternary_weights(input      [7:0] packed_weights,
                              output reg [4:0] weights_zero,
                              output reg [4:0] weights_sign);
    always @(*) begin
        case(packed_weights)
        8'd000: begin weights_zero = 5'b11111; weights_sign = 5'b00000; end //   0  0  0  0  0
        8'd001: begin weights_zero = 5'b01111; weights_sign = 5'b00000; end //   0  0  0  0  1
        8'd002: begin weights_zero = 5'b01111; weights_sign = 5'b10000; end //   0  0  0  0 -1
        8'd003: begin weights_zero = 5'b10111; weights_sign = 5'b00000; end //   0  0  0  1  0
        8'd004: begin weights_zero = 5'b00111; weights_sign = 5'b00000; end //   0  0  0  1  1
        8'd005: begin weights_zero = 5'b00111; weights_sign = 5'b10000; end //   0  0  0  1 -1
        8'd006: begin weights_zero = 5'b10111; weights_sign = 5'b01000; end //   0  0  0 -1  0
        8'd007: begin weights_zero = 5'b00111; weights_sign = 5'b01000; end //   0  0  0 -1  1
        8'd008: begin weights_zero = 5'b00111; weights_sign = 5'b11000; end //   0  0  0 -1 -1
        8'd009: begin weights_zero = 5'b11011; weights_sign = 5'b00000; end //   0  0  1  0  0
        8'd010: begin weights_zero = 5'b01011; weights_sign = 5'b00000; end //   0  0  1  0  1
        8'd011: begin weights_zero = 5'b01011; weights_sign = 5'b10000; end //   0  0  1  0 -1
        8'd012: begin weights_zero = 5'b10011; weights_sign = 5'b00000; end //   0  0  1  1  0
        8'd013: begin weights_zero = 5'b00011; weights_sign = 5'b00000; end //   0  0  1  1  1
        8'd014: begin weights_zero = 5'b00011; weights_sign = 5'b10000; end //   0  0  1  1 -1
        8'd015: begin weights_zero = 5'b10011; weights_sign = 5'b01000; end //   0  0  1 -1  0
        8'd016: begin weights_zero = 5'b00011; weights_sign = 5'b01000; end //   0  0  1 -1  1
        8'd017: begin weights_zero = 5'b00011; weights_sign = 5'b11000; end //   0  0  1 -1 -1
        8'd018: begin weights_zero = 5'b11011; weights_sign = 5'b00100; end //   0  0 -1  0  0
        8'd019: begin weights_zero = 5'b01011; weights_sign = 5'b00100; end //   0  0 -1  0  1
        8'd020: begin weights_zero = 5'b01011; weights_sign = 5'b10100; end //   0  0 -1  0 -1
        8'd021: begin weights_zero = 5'b10011; weights_sign = 5'b00100; end //   0  0 -1  1  0
        8'd022: begin weights_zero = 5'b00011; weights_sign = 5'b00100; end //   0  0 -1  1  1
        8'd023: begin weights_zero = 5'b00011; weights_sign = 5'b10100; end //   0  0 -1  1 -1
        8'd024: begin weights_zero = 5'b10011; weights_sign = 5'b01100; end //   0  0 -1 -1  0
        8'd025: begin weights_zero = 5'b00011; weights_sign = 5'b01100; end //   0  0 -1 -1  1
        8'd026: begin weights_zero = 5'b00011; weights_sign = 5'b11100; end //   0  0 -1 -1 -1
        8'd027: begin weights_zero = 5'b11101; weights_sign = 5'b00000; end //   0  1  0  0  0
        8'd028: begin weights_zero = 5'b01101; weights_sign = 5'b00000; end //   0  1  0  0  1
        8'd029: begin weights_zero = 5'b01101; weights_sign = 5'b10000; end //   0  1  0  0 -1
        8'd030: begin weights_zero = 5'b10101; weights_sign = 5'b00000; end //   0  1  0  1  0
        8'd031: begin weights_zero = 5'b00101; weights_sign = 5'b00000; end //   0  1  0  1  1
        8'd032: begin weights_zero = 5'b00101; weights_sign = 5'b10000; end //   0  1  0  1 -1
        8'd033: begin weights_zero = 5'b10101; weights_sign = 5'b01000; end //   0  1  0 -1  0
        8'd034: begin weights_zero = 5'b00101; weights_sign = 5'b01000; end //   0  1  0 -1  1
        8'd035: begin weights_zero = 5'b00101; weights_sign = 5'b11000; end //   0  1  0 -1 -1
        8'd036: begin weights_zero = 5'b11001; weights_sign = 5'b00000; end //   0  1  1  0  0
        8'd037: begin weights_zero = 5'b01001; weights_sign = 5'b00000; end //   0  1  1  0  1
        8'd038: begin weights_zero = 5'b01001; weights_sign = 5'b10000; end //   0  1  1  0 -1
        8'd039: begin weights_zero = 5'b10001; weights_sign = 5'b00000; end //   0  1  1  1  0
        8'd040: begin weights_zero = 5'b00001; weights_sign = 5'b00000; end //   0  1  1  1  1
        8'd041: begin weights_zero = 5'b00001; weights_sign = 5'b10000; end //   0  1  1  1 -1
        8'd042: begin weights_zero = 5'b10001; weights_sign = 5'b01000; end //   0  1  1 -1  0
        8'd043: begin weights_zero = 5'b00001; weights_sign = 5'b01000; end //   0  1  1 -1  1
        8'd044: begin weights_zero = 5'b00001; weights_sign = 5'b11000; end //   0  1  1 -1 -1
        8'd045: begin weights_zero = 5'b11001; weights_sign = 5'b00100; end //   0  1 -1  0  0
        8'd046: begin weights_zero = 5'b01001; weights_sign = 5'b00100; end //   0  1 -1  0  1
        8'd047: begin weights_zero = 5'b01001; weights_sign = 5'b10100; end //   0  1 -1  0 -1
        8'd048: begin weights_zero = 5'b10001; weights_sign = 5'b00100; end //   0  1 -1  1  0
        8'd049: begin weights_zero = 5'b00001; weights_sign = 5'b00100; end //   0  1 -1  1  1
        8'd050: begin weights_zero = 5'b00001; weights_sign = 5'b10100; end //   0  1 -1  1 -1
        8'd051: begin weights_zero = 5'b10001; weights_sign = 5'b01100; end //   0  1 -1 -1  0
        8'd052: begin weights_zero = 5'b00001; weights_sign = 5'b01100; end //   0  1 -1 -1  1
        8'd053: begin weights_zero = 5'b00001; weights_sign = 5'b11100; end //   0  1 -1 -1 -1
        8'd054: begin weights_zero = 5'b11101; weights_sign = 5'b00010; end //   0 -1  0  0  0
        8'd055: begin weights_zero = 5'b01101; weights_sign = 5'b00010; end //   0 -1  0  0  1
        8'd056: begin weights_zero = 5'b01101; weights_sign = 5'b10010; end //   0 -1  0  0 -1
        8'd057: begin weights_zero = 5'b10101; weights_sign = 5'b00010; end //   0 -1  0  1  0
        8'd058: begin weights_zero = 5'b00101; weights_sign = 5'b00010; end //   0 -1  0  1  1
        8'd059: begin weights_zero = 5'b00101; weights_sign = 5'b10010; end //   0 -1  0  1 -1
        8'd060: begin weights_zero = 5'b10101; weights_sign = 5'b01010; end //   0 -1  0 -1  0
        8'd061: begin weights_zero = 5'b00101; weights_sign = 5'b01010; end //   0 -1  0 -1  1
        8'd062: begin weights_zero = 5'b00101; weights_sign = 5'b11010; end //   0 -1  0 -1 -1
        8'd063: begin weights_zero = 5'b11001; weights_sign = 5'b00010; end //   0 -1  1  0  0
        8'd064: begin weights_zero = 5'b01001; weights_sign = 5'b00010; end //   0 -1  1  0  1
        8'd065: begin weights_zero = 5'b01001; weights_sign = 5'b10010; end //   0 -1  1  0 -1
        8'd066: begin weights_zero = 5'b10001; weights_sign = 5'b00010; end //   0 -1  1  1  0
        8'd067: begin weights_zero = 5'b00001; weights_sign = 5'b00010; end //   0 -1  1  1  1
        8'd068: begin weights_zero = 5'b00001; weights_sign = 5'b10010; end //   0 -1  1  1 -1
        8'd069: begin weights_zero = 5'b10001; weights_sign = 5'b01010; end //   0 -1  1 -1  0
        8'd070: begin weights_zero = 5'b00001; weights_sign = 5'b01010; end //   0 -1  1 -1  1
        8'd071: begin weights_zero = 5'b00001; weights_sign = 5'b11010; end //   0 -1  1 -1 -1
        8'd072: begin weights_zero = 5'b11001; weights_sign = 5'b00110; end //   0 -1 -1  0  0
        8'd073: begin weights_zero = 5'b01001; weights_sign = 5'b00110; end //   0 -1 -1  0  1
        8'd074: begin weights_zero = 5'b01001; weights_sign = 5'b10110; end //   0 -1 -1  0 -1
        8'd075: begin weights_zero = 5'b10001; weights_sign = 5'b00110; end //   0 -1 -1  1  0
        8'd076: begin weights_zero = 5'b00001; weights_sign = 5'b00110; end //   0 -1 -1  1  1
        8'd077: begin weights_zero = 5'b00001; weights_sign = 5'b10110; end //   0 -1 -1  1 -1
        8'd078: begin weights_zero = 5'b10001; weights_sign = 5'b01110; end //   0 -1 -1 -1  0
        8'd079: begin weights_zero = 5'b00001; weights_sign = 5'b01110; end //   0 -1 -1 -1  1
        8'd080: begin weights_zero = 5'b00001; weights_sign = 5'b11110; end //   0 -1 -1 -1 -1
        8'd081: begin weights_zero = 5'b11110; weights_sign = 5'b00000; end //   1  0  0  0  0
        8'd082: begin weights_zero = 5'b01110; weights_sign = 5'b00000; end //   1  0  0  0  1
        8'd083: begin weights_zero = 5'b01110; weights_sign = 5'b10000; end //   1  0  0  0 -1
        8'd084: begin weights_zero = 5'b10110; weights_sign = 5'b00000; end //   1  0  0  1  0
        8'd085: begin weights_zero = 5'b00110; weights_sign = 5'b00000; end //   1  0  0  1  1
        8'd086: begin weights_zero = 5'b00110; weights_sign = 5'b10000; end //   1  0  0  1 -1
        8'd087: begin weights_zero = 5'b10110; weights_sign = 5'b01000; end //   1  0  0 -1  0
        8'd088: begin weights_zero = 5'b00110; weights_sign = 5'b01000; end //   1  0  0 -1  1
        8'd089: begin weights_zero = 5'b00110; weights_sign = 5'b11000; end //   1  0  0 -1 -1
        8'd090: begin weights_zero = 5'b11010; weights_sign = 5'b00000; end //   1  0  1  0  0
        8'd091: begin weights_zero = 5'b01010; weights_sign = 5'b00000; end //   1  0  1  0  1
        8'd092: begin weights_zero = 5'b01010; weights_sign = 5'b10000; end //   1  0  1  0 -1
        8'd093: begin weights_zero = 5'b10010; weights_sign = 5'b00000; end //   1  0  1  1  0
        8'd094: begin weights_zero = 5'b00010; weights_sign = 5'b00000; end //   1  0  1  1  1
        8'd095: begin weights_zero = 5'b00010; weights_sign = 5'b10000; end //   1  0  1  1 -1
        8'd096: begin weights_zero = 5'b10010; weights_sign = 5'b01000; end //   1  0  1 -1  0
        8'd097: begin weights_zero = 5'b00010; weights_sign = 5'b01000; end //   1  0  1 -1  1
        8'd098: begin weights_zero = 5'b00010; weights_sign = 5'b11000; end //   1  0  1 -1 -1
        8'd099: begin weights_zero = 5'b11010; weights_sign = 5'b00100; end //   1  0 -1  0  0
        8'd100: begin weights_zero = 5'b01010; weights_sign = 5'b00100; end //   1  0 -1  0  1
        8'd101: begin weights_zero = 5'b01010; weights_sign = 5'b10100; end //   1  0 -1  0 -1
        8'd102: begin weights_zero = 5'b10010; weights_sign = 5'b00100; end //   1  0 -1  1  0
        8'd103: begin weights_zero = 5'b00010; weights_sign = 5'b00100; end //   1  0 -1  1  1
        8'd104: begin weights_zero = 5'b00010; weights_sign = 5'b10100; end //   1  0 -1  1 -1
        8'd105: begin weights_zero = 5'b10010; weights_sign = 5'b01100; end //   1  0 -1 -1  0
        8'd106: begin weights_zero = 5'b00010; weights_sign = 5'b01100; end //   1  0 -1 -1  1
        8'd107: begin weights_zero = 5'b00010; weights_sign = 5'b11100; end //   1  0 -1 -1 -1
        8'd108: begin weights_zero = 5'b11100; weights_sign = 5'b00000; end //   1  1  0  0  0
        8'd109: begin weights_zero = 5'b01100; weights_sign = 5'b00000; end //   1  1  0  0  1
        8'd110: begin weights_zero = 5'b01100; weights_sign = 5'b10000; end //   1  1  0  0 -1
        8'd111: begin weights_zero = 5'b10100; weights_sign = 5'b00000; end //   1  1  0  1  0
        8'd112: begin weights_zero = 5'b00100; weights_sign = 5'b00000; end //   1  1  0  1  1
        8'd113: begin weights_zero = 5'b00100; weights_sign = 5'b10000; end //   1  1  0  1 -1
        8'd114: begin weights_zero = 5'b10100; weights_sign = 5'b01000; end //   1  1  0 -1  0
        8'd115: begin weights_zero = 5'b00100; weights_sign = 5'b01000; end //   1  1  0 -1  1
        8'd116: begin weights_zero = 5'b00100; weights_sign = 5'b11000; end //   1  1  0 -1 -1
        8'd117: begin weights_zero = 5'b11000; weights_sign = 5'b00000; end //   1  1  1  0  0
        8'd118: begin weights_zero = 5'b01000; weights_sign = 5'b00000; end //   1  1  1  0  1
        8'd119: begin weights_zero = 5'b01000; weights_sign = 5'b10000; end //   1  1  1  0 -1
        8'd120: begin weights_zero = 5'b10000; weights_sign = 5'b00000; end //   1  1  1  1  0
        8'd121: begin weights_zero = 5'b00000; weights_sign = 5'b00000; end //   1  1  1  1  1
        8'd122: begin weights_zero = 5'b00000; weights_sign = 5'b10000; end //   1  1  1  1 -1
        8'd123: begin weights_zero = 5'b10000; weights_sign = 5'b01000; end //   1  1  1 -1  0
        8'd124: begin weights_zero = 5'b00000; weights_sign = 5'b01000; end //   1  1  1 -1  1
        8'd125: begin weights_zero = 5'b00000; weights_sign = 5'b11000; end //   1  1  1 -1 -1
        8'd126: begin weights_zero = 5'b11000; weights_sign = 5'b00100; end //   1  1 -1  0  0
        8'd127: begin weights_zero = 5'b01000; weights_sign = 5'b00100; end //   1  1 -1  0  1
        8'd128: begin weights_zero = 5'b01000; weights_sign = 5'b10100; end //   1  1 -1  0 -1
        8'd129: begin weights_zero = 5'b10000; weights_sign = 5'b00100; end //   1  1 -1  1  0
        8'd130: begin weights_zero = 5'b00000; weights_sign = 5'b00100; end //   1  1 -1  1  1
        8'd131: begin weights_zero = 5'b00000; weights_sign = 5'b10100; end //   1  1 -1  1 -1
        8'd132: begin weights_zero = 5'b10000; weights_sign = 5'b01100; end //   1  1 -1 -1  0
        8'd133: begin weights_zero = 5'b00000; weights_sign = 5'b01100; end //   1  1 -1 -1  1
        8'd134: begin weights_zero = 5'b00000; weights_sign = 5'b11100; end //   1  1 -1 -1 -1
        8'd135: begin weights_zero = 5'b11100; weights_sign = 5'b00010; end //   1 -1  0  0  0
        8'd136: begin weights_zero = 5'b01100; weights_sign = 5'b00010; end //   1 -1  0  0  1
        8'd137: begin weights_zero = 5'b01100; weights_sign = 5'b10010; end //   1 -1  0  0 -1
        8'd138: begin weights_zero = 5'b10100; weights_sign = 5'b00010; end //   1 -1  0  1  0
        8'd139: begin weights_zero = 5'b00100; weights_sign = 5'b00010; end //   1 -1  0  1  1
        8'd140: begin weights_zero = 5'b00100; weights_sign = 5'b10010; end //   1 -1  0  1 -1
        8'd141: begin weights_zero = 5'b10100; weights_sign = 5'b01010; end //   1 -1  0 -1  0
        8'd142: begin weights_zero = 5'b00100; weights_sign = 5'b01010; end //   1 -1  0 -1  1
        8'd143: begin weights_zero = 5'b00100; weights_sign = 5'b11010; end //   1 -1  0 -1 -1
        8'd144: begin weights_zero = 5'b11000; weights_sign = 5'b00010; end //   1 -1  1  0  0
        8'd145: begin weights_zero = 5'b01000; weights_sign = 5'b00010; end //   1 -1  1  0  1
        8'd146: begin weights_zero = 5'b01000; weights_sign = 5'b10010; end //   1 -1  1  0 -1
        8'd147: begin weights_zero = 5'b10000; weights_sign = 5'b00010; end //   1 -1  1  1  0
        8'd148: begin weights_zero = 5'b00000; weights_sign = 5'b00010; end //   1 -1  1  1  1
        8'd149: begin weights_zero = 5'b00000; weights_sign = 5'b10010; end //   1 -1  1  1 -1
        8'd150: begin weights_zero = 5'b10000; weights_sign = 5'b01010; end //   1 -1  1 -1  0
        8'd151: begin weights_zero = 5'b00000; weights_sign = 5'b01010; end //   1 -1  1 -1  1
        8'd152: begin weights_zero = 5'b00000; weights_sign = 5'b11010; end //   1 -1  1 -1 -1
        8'd153: begin weights_zero = 5'b11000; weights_sign = 5'b00110; end //   1 -1 -1  0  0
        8'd154: begin weights_zero = 5'b01000; weights_sign = 5'b00110; end //   1 -1 -1  0  1
        8'd155: begin weights_zero = 5'b01000; weights_sign = 5'b10110; end //   1 -1 -1  0 -1
        8'd156: begin weights_zero = 5'b10000; weights_sign = 5'b00110; end //   1 -1 -1  1  0
        8'd157: begin weights_zero = 5'b00000; weights_sign = 5'b00110; end //   1 -1 -1  1  1
        8'd158: begin weights_zero = 5'b00000; weights_sign = 5'b10110; end //   1 -1 -1  1 -1
        8'd159: begin weights_zero = 5'b10000; weights_sign = 5'b01110; end //   1 -1 -1 -1  0
        8'd160: begin weights_zero = 5'b00000; weights_sign = 5'b01110; end //   1 -1 -1 -1  1
        8'd161: begin weights_zero = 5'b00000; weights_sign = 5'b11110; end //   1 -1 -1 -1 -1
        8'd162: begin weights_zero = 5'b11110; weights_sign = 5'b00001; end //  -1  0  0  0  0
        8'd163: begin weights_zero = 5'b01110; weights_sign = 5'b00001; end //  -1  0  0  0  1
        8'd164: begin weights_zero = 5'b01110; weights_sign = 5'b10001; end //  -1  0  0  0 -1
        8'd165: begin weights_zero = 5'b10110; weights_sign = 5'b00001; end //  -1  0  0  1  0
        8'd166: begin weights_zero = 5'b00110; weights_sign = 5'b00001; end //  -1  0  0  1  1
        8'd167: begin weights_zero = 5'b00110; weights_sign = 5'b10001; end //  -1  0  0  1 -1
        8'd168: begin weights_zero = 5'b10110; weights_sign = 5'b01001; end //  -1  0  0 -1  0
        8'd169: begin weights_zero = 5'b00110; weights_sign = 5'b01001; end //  -1  0  0 -1  1
        8'd170: begin weights_zero = 5'b00110; weights_sign = 5'b11001; end //  -1  0  0 -1 -1
        8'd171: begin weights_zero = 5'b11010; weights_sign = 5'b00001; end //  -1  0  1  0  0
        8'd172: begin weights_zero = 5'b01010; weights_sign = 5'b00001; end //  -1  0  1  0  1
        8'd173: begin weights_zero = 5'b01010; weights_sign = 5'b10001; end //  -1  0  1  0 -1
        8'd174: begin weights_zero = 5'b10010; weights_sign = 5'b00001; end //  -1  0  1  1  0
        8'd175: begin weights_zero = 5'b00010; weights_sign = 5'b00001; end //  -1  0  1  1  1
        8'd176: begin weights_zero = 5'b00010; weights_sign = 5'b10001; end //  -1  0  1  1 -1
        8'd177: begin weights_zero = 5'b10010; weights_sign = 5'b01001; end //  -1  0  1 -1  0
        8'd178: begin weights_zero = 5'b00010; weights_sign = 5'b01001; end //  -1  0  1 -1  1
        8'd179: begin weights_zero = 5'b00010; weights_sign = 5'b11001; end //  -1  0  1 -1 -1
        8'd180: begin weights_zero = 5'b11010; weights_sign = 5'b00101; end //  -1  0 -1  0  0
        8'd181: begin weights_zero = 5'b01010; weights_sign = 5'b00101; end //  -1  0 -1  0  1
        8'd182: begin weights_zero = 5'b01010; weights_sign = 5'b10101; end //  -1  0 -1  0 -1
        8'd183: begin weights_zero = 5'b10010; weights_sign = 5'b00101; end //  -1  0 -1  1  0
        8'd184: begin weights_zero = 5'b00010; weights_sign = 5'b00101; end //  -1  0 -1  1  1
        8'd185: begin weights_zero = 5'b00010; weights_sign = 5'b10101; end //  -1  0 -1  1 -1
        8'd186: begin weights_zero = 5'b10010; weights_sign = 5'b01101; end //  -1  0 -1 -1  0
        8'd187: begin weights_zero = 5'b00010; weights_sign = 5'b01101; end //  -1  0 -1 -1  1
        8'd188: begin weights_zero = 5'b00010; weights_sign = 5'b11101; end //  -1  0 -1 -1 -1
        8'd189: begin weights_zero = 5'b11100; weights_sign = 5'b00001; end //  -1  1  0  0  0
        8'd190: begin weights_zero = 5'b01100; weights_sign = 5'b00001; end //  -1  1  0  0  1
        8'd191: begin weights_zero = 5'b01100; weights_sign = 5'b10001; end //  -1  1  0  0 -1
        8'd192: begin weights_zero = 5'b10100; weights_sign = 5'b00001; end //  -1  1  0  1  0
        8'd193: begin weights_zero = 5'b00100; weights_sign = 5'b00001; end //  -1  1  0  1  1
        8'd194: begin weights_zero = 5'b00100; weights_sign = 5'b10001; end //  -1  1  0  1 -1
        8'd195: begin weights_zero = 5'b10100; weights_sign = 5'b01001; end //  -1  1  0 -1  0
        8'd196: begin weights_zero = 5'b00100; weights_sign = 5'b01001; end //  -1  1  0 -1  1
        8'd197: begin weights_zero = 5'b00100; weights_sign = 5'b11001; end //  -1  1  0 -1 -1
        8'd198: begin weights_zero = 5'b11000; weights_sign = 5'b00001; end //  -1  1  1  0  0
        8'd199: begin weights_zero = 5'b01000; weights_sign = 5'b00001; end //  -1  1  1  0  1
        8'd200: begin weights_zero = 5'b01000; weights_sign = 5'b10001; end //  -1  1  1  0 -1
        8'd201: begin weights_zero = 5'b10000; weights_sign = 5'b00001; end //  -1  1  1  1  0
        8'd202: begin weights_zero = 5'b00000; weights_sign = 5'b00001; end //  -1  1  1  1  1
        8'd203: begin weights_zero = 5'b00000; weights_sign = 5'b10001; end //  -1  1  1  1 -1
        8'd204: begin weights_zero = 5'b10000; weights_sign = 5'b01001; end //  -1  1  1 -1  0
        8'd205: begin weights_zero = 5'b00000; weights_sign = 5'b01001; end //  -1  1  1 -1  1
        8'd206: begin weights_zero = 5'b00000; weights_sign = 5'b11001; end //  -1  1  1 -1 -1
        8'd207: begin weights_zero = 5'b11000; weights_sign = 5'b00101; end //  -1  1 -1  0  0
        8'd208: begin weights_zero = 5'b01000; weights_sign = 5'b00101; end //  -1  1 -1  0  1
        8'd209: begin weights_zero = 5'b01000; weights_sign = 5'b10101; end //  -1  1 -1  0 -1
        8'd210: begin weights_zero = 5'b10000; weights_sign = 5'b00101; end //  -1  1 -1  1  0
        8'd211: begin weights_zero = 5'b00000; weights_sign = 5'b00101; end //  -1  1 -1  1  1
        8'd212: begin weights_zero = 5'b00000; weights_sign = 5'b10101; end //  -1  1 -1  1 -1
        8'd213: begin weights_zero = 5'b10000; weights_sign = 5'b01101; end //  -1  1 -1 -1  0
        8'd214: begin weights_zero = 5'b00000; weights_sign = 5'b01101; end //  -1  1 -1 -1  1
        8'd215: begin weights_zero = 5'b00000; weights_sign = 5'b11101; end //  -1  1 -1 -1 -1
        8'd216: begin weights_zero = 5'b11100; weights_sign = 5'b00011; end //  -1 -1  0  0  0
        8'd217: begin weights_zero = 5'b01100; weights_sign = 5'b00011; end //  -1 -1  0  0  1
        8'd218: begin weights_zero = 5'b01100; weights_sign = 5'b10011; end //  -1 -1  0  0 -1
        8'd219: begin weights_zero = 5'b10100; weights_sign = 5'b00011; end //  -1 -1  0  1  0
        8'd220: begin weights_zero = 5'b00100; weights_sign = 5'b00011; end //  -1 -1  0  1  1
        8'd221: begin weights_zero = 5'b00100; weights_sign = 5'b10011; end //  -1 -1  0  1 -1
        8'd222: begin weights_zero = 5'b10100; weights_sign = 5'b01011; end //  -1 -1  0 -1  0
        8'd223: begin weights_zero = 5'b00100; weights_sign = 5'b01011; end //  -1 -1  0 -1  1
        8'd224: begin weights_zero = 5'b00100; weights_sign = 5'b11011; end //  -1 -1  0 -1 -1
        8'd225: begin weights_zero = 5'b11000; weights_sign = 5'b00011; end //  -1 -1  1  0  0
        8'd226: begin weights_zero = 5'b01000; weights_sign = 5'b00011; end //  -1 -1  1  0  1
        8'd227: begin weights_zero = 5'b01000; weights_sign = 5'b10011; end //  -1 -1  1  0 -1
        8'd228: begin weights_zero = 5'b10000; weights_sign = 5'b00011; end //  -1 -1  1  1  0
        8'd229: begin weights_zero = 5'b00000; weights_sign = 5'b00011; end //  -1 -1  1  1  1
        8'd230: begin weights_zero = 5'b00000; weights_sign = 5'b10011; end //  -1 -1  1  1 -1
        8'd231: begin weights_zero = 5'b10000; weights_sign = 5'b01011; end //  -1 -1  1 -1  0
        8'd232: begin weights_zero = 5'b00000; weights_sign = 5'b01011; end //  -1 -1  1 -1  1
        8'd233: begin weights_zero = 5'b00000; weights_sign = 5'b11011; end //  -1 -1  1 -1 -1
        8'd234: begin weights_zero = 5'b11000; weights_sign = 5'b00111; end //  -1 -1 -1  0  0
        8'd235: begin weights_zero = 5'b01000; weights_sign = 5'b00111; end //  -1 -1 -1  0  1
        8'd236: begin weights_zero = 5'b01000; weights_sign = 5'b10111; end //  -1 -1 -1  0 -1
        8'd237: begin weights_zero = 5'b10000; weights_sign = 5'b00111; end //  -1 -1 -1  1  0
        8'd238: begin weights_zero = 5'b00000; weights_sign = 5'b00111; end //  -1 -1 -1  1  1
        8'd239: begin weights_zero = 5'b00000; weights_sign = 5'b10111; end //  -1 -1 -1  1 -1
        8'd240: begin weights_zero = 5'b10000; weights_sign = 5'b01111; end //  -1 -1 -1 -1  0
        8'd241: begin weights_zero = 5'b00000; weights_sign = 5'b01111; end //  -1 -1 -1 -1  1
        8'd242: begin weights_zero = 5'b00000; weights_sign = 5'b11111; end //  -1 -1 -1 -1 -1
        default: {weights_zero, weights_sign} = 10'b0; // Default case
        endcase
    end
endmodule