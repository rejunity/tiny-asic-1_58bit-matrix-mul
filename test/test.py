# SPDX-FileCopyrightText: © 2023 Uri Shaked <uri@tinytapeout.com>
# SPDX-License-Identifier: MIT

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from utils import *

# PACK_5_WEIGHTS = False
PACK_5_WEIGHTS = True
COMPUTE_SLICES = 3

WEIGHTS_PER_BYTE     = 5 if PACK_5_WEIGHTS else 4
COMPUTE_BLOCK_WIDTH  = 1               *COMPUTE_SLICES
COMPUTE_BLOCK_HEIGHT = WEIGHTS_PER_BYTE*COMPUTE_SLICES


def OUT(v):
    return v >> 8
    # return s8_to_i32(v & 255)

@cocotb.test()
async def test_1(dut):
    dut._log.info("Start")

    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = (1*3**4 + 2*3**3 + 1*3**2 + 0*3**1 + 2*3**0) if PACK_5_WEIGHTS else 0b01_11_01_00
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    dut._log.info("Compute")
    dut.ui_in.value = (1*3**4 + 2*3**3 + 1*3**2 + 0*3**1 + 2*3**0) if PACK_5_WEIGHTS else 0b01_11_01_00
    dut.uio_in.value = 127
    
    K = 12
    await ClockCycles(dut.clk, K + COMPUTE_SLICES)
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")
    for _ in range(COMPUTE_SLICES):
        await ClockCycles(dut.clk, 1)
        print (s8_to_i32(dut.uo_out.value))
        assert s8_to_i32(dut.uo_out.value) == OUT( 1 * 127 * K//COMPUTE_SLICES)

    for _ in range(COMPUTE_SLICES):
        await ClockCycles(dut.clk, 1)
        assert s8_to_i32(dut.uo_out.value) == OUT(-1 * 127 * K//COMPUTE_SLICES)

    for _ in range(COMPUTE_SLICES):
        await ClockCycles(dut.clk, 1)
        assert s8_to_i32(dut.uo_out.value) == OUT( 1 * 127 * K//COMPUTE_SLICES)

    for _ in range(COMPUTE_SLICES):
        await ClockCycles(dut.clk, 1)
        assert s8_to_i32(dut.uo_out.value) == OUT( 0 * 127 * K//COMPUTE_SLICES)

    if PACK_5_WEIGHTS:
        for _ in range(COMPUTE_SLICES):
            await ClockCycles(dut.clk, 1)
            assert s8_to_i32(dut.uo_out.value) == OUT( -1 * 127 * K//COMPUTE_SLICES)

# @cocotb.test()
async def test_2(dut):
    dut._log.info("Start")

    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    weights = [1, 0, -1, 0]
    inputs = [127] * 6

    dut._log.info("Compute")
    dut.ui_in.value = pack_weights(weights)
    for x in inputs:
        dut.uio_in.value = x
        await ClockCycles(dut.clk, 1)
    
    # Move accumulators to output queue
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")

    for w in weights:
        await ClockCycles(dut.clk, 1)
        assert s8_to_i32(dut.uo_out.value) == OUT(dot(w, inputs))

# @cocotb.test()
async def test_3(dut):
    dut._log.info("Start")

    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    weights = [1, 0, -1, 0]
    inputs = range(127)

    dut._log.info("Compute")
    dut.ui_in.value = pack_weights(weights)
    for x in inputs:
        dut.uio_in.value = x
        await ClockCycles(dut.clk, 1)
    
    # Move accumulators to output queue
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")

    for w in weights:
        await ClockCycles(dut.clk, 1)
        assert s8_to_i32(dut.uo_out.value) == OUT(dot(w, inputs))

# @cocotb.test()
async def test_4(dut):
    random.seed(3)
    N = 128
    weights = random_matrix(-1, 1, (N, 4))
    packed_weights = pack_weights(flatten(weights))
    inputs = range(N)

    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    dut._log.info("Compute")
    # for x, w in zip(inputs, packed_weights):
    for x in reversed(inputs):
        dut.uio_in.value = x
        dut.ui_in.value  = packed_weights & 255
        packed_weights >>= 8
        await ClockCycles(dut.clk, 1)
    
    # Move accumulators to output queue
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")

    # for w in transpose(weights):
    #     print (dot(w, inputs), OUT(dot(w, inputs)), s8_to_i32(dot(w, inputs) & 255))

    for w in transpose(weights):
        await ClockCycles(dut.clk, 1)
        # print (dut.uo_out.value, int(dut.uo_out.value), s8_to_i32(dut.uo_out.value))
        assert s8_to_i32(dut.uo_out.value) == OUT(dot(w, inputs))


# @cocotb.test()
async def test_5(dut):
    random.seed(3)
    N = 128
    weights  = random_matrix(-1, 1, (4, N))
    inputs   = random_matrix(-127, 127, (N, 1))
    expected = matrix_mul(weights, inputs)
    packed_weights = pack_weights_as_u8_array(zigzag_h(weights, 4))
    packed_inputs = zigzag_w(inputs, 1)
    
    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    dut._log.info("Compute")
    for x, w in zip(packed_inputs, packed_weights):
        dut.uio_in.value = x
        dut.ui_in.value = w
        await ClockCycles(dut.clk, 1)
    
    # Move accumulators to output queue
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")

    # for w in transpose(weights):
    for v in flatten(expected):
        await ClockCycles(dut.clk, 1)
        # print (dut.uo_out.value, int(dut.uo_out.value), s8_to_i32(dut.uo_out.value))
        assert s8_to_i32(dut.uo_out.value) == OUT(v)

async def gemm(dut, weights, inputs, weights_per_byte = 4, compute_block_width = 1, compute_block_height = 4, compute_slices = 1, verbose=False):

    W = compute_block_width
    H = compute_block_height

    N = len(weights) // H
    M = len(inputs[0]) // W
    assert len(weights[0]) == len(inputs)
    K = len(weights[0]) * compute_slices

    zigzag_weights = pack_weights_as_u8_array(zigzag_h(weights, H), weights_per_byte)
    zigzag_inputs  = zigzag_w(inputs, W)
    
    if verbose:
        print (f"packed W = {zigzag_weights} zigzag W = {zigzag_h(weights, H)}")
        print (f"zigzag X = {zigzag_inputs}")
    
    assert len(zigzag_weights) == N * K
    assert len(zigzag_inputs) == K * M

    result = const_matrix(0, (N*H, M*W))
    for m in range(M):
        for n in range(N):
            # Set inputs & compute
            weights_for_compute = zigzag_weights[n*K:(n+1)*K]
            inputs_for_compute = zigzag_inputs[m*K:(m+1)*K]
            if (verbose):
                print (f"compute R[n={n}, m={m}]")
                print (f"compute W = {weights_for_compute} zigzag W = {zigzag_h(weights, H)[n*K:(n+1)*K]}")
                print (f"compute X = {inputs_for_compute}")

            for x, w in zip(inputs_for_compute, weights_for_compute):
                dut.uio_in.value = x
                dut.ui_in.value  = w
                await ClockCycles(dut.clk, 1)

            # Wait until all slices have finished accunulating
            dut.ui_in.value = 0
            dut.uio_in.value = 0
            await ClockCycles(dut.clk, compute_slices)

            # Move accumulators to output queue
            dut.ena.value = 0
            dut.ui_in.value = 0
            dut.uio_in.value = 0
            await ClockCycles(dut.clk, 1)
            dut.ena.value = 1

            for h in range(H):
                for w in range(W):
                    await ClockCycles(dut.clk, 1)
                    result[n*H+h][m*W+w] = s8_to_i32(dut.uo_out.value)

    assert shape(result) == (N*H, M*W)
    return result

async def reset_run_and_validate_gemm(dut, weights, inputs, expected, verbose=False):
    if verbose:
        print ("W =", weights, "shape =", shape(weights))
        print ("X =", inputs, "shape =", shape(inputs))

    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    dut._log.info("Compute")
    dut_result = await gemm(dut, weights, inputs, \
                            WEIGHTS_PER_BYTE,  \
                            COMPUTE_BLOCK_WIDTH,  \
                            COMPUTE_BLOCK_HEIGHT, \
                            COMPUTE_SLICES,
                            verbose=verbose)

    # Validate
    dut._log.info("Validate")
    # expected = flatten(transpose(expected))
    assert shape(expected) == shape(dut_result)
    if verbose:
        print ("O =", expected, "shape =", shape(expected))
        print ("O'=", [OUT(v) for v in flatten(expected)])
        print ("R =", flatten(dut_result), "shape =", shape(dut_result))
    else:
        print (f"W{shape(weights)} * X{shape(inputs)} = expected{shape(expected)} / got{shape(dut_result)}")

    for v, r in zip(flatten(expected), flatten(dut_result)):
        assert OUT(v) == r

@cocotb.test()
async def test_gemm_positive_weights(dut):
    random.seed(3)

    N = 1  *COMPUTE_BLOCK_HEIGHT
    K = 4
    M = 1  *COMPUTE_BLOCK_WIDTH
    weights  = const_matrix(   1, (N, K))
    inputs   = const_matrix( 127, (K, M))
    expected = matrix_mul(weights, inputs)

    await reset_run_and_validate_gemm(dut, weights, inputs, expected)

@cocotb.test()
async def test_gemm_negative_weights(dut):
    random.seed(3)

    N = 1  *COMPUTE_BLOCK_HEIGHT
    K = 4
    M = 1  *COMPUTE_BLOCK_WIDTH
    weights  = const_matrix(  -1, (N, K))
    inputs   = const_matrix( 127, (K, M))
    expected = matrix_mul(weights, inputs)

    await reset_run_and_validate_gemm(dut, weights, inputs, expected)

@cocotb.test()
async def test_gemm_negative_inputs(dut):
    random.seed(3)

    N = 1  *COMPUTE_BLOCK_HEIGHT
    K = 4
    M = 1  *COMPUTE_BLOCK_WIDTH
    weights  = const_matrix(   1, (N, K))
    inputs   = const_matrix(-127, (K, M))
    expected = matrix_mul(weights, inputs)

    await reset_run_and_validate_gemm(dut, weights, inputs, expected)

@cocotb.test()
async def test_gemm_small(dut):
    random.seed(3)

    N = 1  *COMPUTE_BLOCK_HEIGHT
    K = 16
    M = 1  *COMPUTE_BLOCK_WIDTH
    weights  = random_matrix(  -1,   1, (N, K))
    inputs   = random_matrix(-127, 127, (K, M))
    expected = matrix_mul(weights, inputs)

    await reset_run_and_validate_gemm(dut, weights, inputs, expected)

@cocotb.test()
async def test_gemm_large(dut):
    random.seed(3)

    N = 4  *COMPUTE_BLOCK_HEIGHT
    K = 128
    M = 3  *COMPUTE_BLOCK_WIDTH
    weights  = random_matrix(  -1,   1, (N, K))
    inputs   = random_matrix(-127, 127, (K, M))
    expected = matrix_mul(weights, inputs)

    await reset_run_and_validate_gemm(dut, weights, inputs, expected)