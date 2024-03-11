# SPDX-FileCopyrightText: © 2023 Uri Shaked <uri@tinytapeout.com>
# SPDX-License-Identifier: MIT

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from utils import *

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
    # dut.ui_in.value = 0b00_01_11_01
    dut.ui_in.value = 0b01_11_01_00
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1

    # Compute
    dut._log.info("Compute")
    # dut.ui_in.value = 0b00_01_11_01
    dut.ui_in.value = 0b01_11_01_00
    dut.uio_in.value = 127
    
    await ClockCycles(dut.clk, 6)
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == OUT( 1 * 127 * 6)
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == OUT(-1 * 127 * 6)
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == OUT( 1 * 127 * 6)
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == OUT( 0 * 127 * 6)

@cocotb.test()
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

@cocotb.test()
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

@cocotb.test()
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


@cocotb.test()
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

async def gemm(dut, weights, inputs, compute_block_width = 1, compute_block_height = 4):
    # print ("W $", shape(weights))
    # print ("X $", shape(inputs))

    N = len(weights) // compute_block_height
    M = len(inputs[0]) // compute_block_width
    assert len(weights[0]) == len(inputs)
    K = len(weights[0])

    # zigzag_weights_unpacked = zigzag_h(weights, compute_block_height)
    zigzag_weights = pack_weights_as_u8_array(zigzag_h(weights, compute_block_height))
    zigzag_inputs  = zigzag_w(inputs, compute_block_width)
    
    assert len(zigzag_weights) == N * K
    assert len(zigzag_inputs) == K * M

    result = []
    for m in range(M):
        for n in range(N):
            # Set inputs & compute
            weights_for_compute = zigzag_weights[n*K:(n+1)*K]
            inputs_for_compute = zigzag_inputs[m*K:(m+1)*K]
            for x, w in zip(inputs_for_compute, weights_for_compute):
                dut.uio_in.value = x
                dut.ui_in.value  = w
                await ClockCycles(dut.clk, 1)    

            # Move accumulators to output queue
            dut.ena.value = 0
            dut.ui_in.value = 0
            dut.uio_in.value = 0
            await ClockCycles(dut.clk, 1)
            dut.ena.value = 1

            for _ in range(compute_block_width * compute_block_height):
                await ClockCycles(dut.clk, 1)
                result.append(s8_to_i32(dut.uo_out.value))

    assert len(result) == N * M * compute_block_height * compute_block_width

    # transpose result & shape as 2d array 
    N *= compute_block_height
    M *= compute_block_width
    result = [result[i+j] for j in range(N) for i in range(0, len(result), N)]
    result = [result[i:i+M] for i in range(0, len(result), M)]
    assert shape(result) == (N, M)
    return result

@cocotb.test()
async def test_gemm(dut):
    random.seed(3)
    W = 1
    H = 4

    N = 4
    K = 128
    M = 3
    weights  = random_matrix(  -1,   1, (N*H, K))
    inputs   = random_matrix(-127, 127, (K, M*W))
    expected = matrix_mul(weights, inputs)
    # print ("W = ", weights, shape(weights))
    # print ("X = ", inputs, shape(inputs))
    # print ("O =", expected, shape(expected))

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
    dut_result = await gemm(dut, weights, inputs, W, H)

    # Validate
    dut._log.info("Validate")
    # expected = flatten(transpose(expected))
    assert shape(expected) == shape(dut_result)
    print ("O =", expected, "shape =", shape(expected))
    print ("O'=", [OUT(v) for v in flatten(expected)])
    print ("R =", flatten(dut_result), "shape =", shape(dut_result))

    for v, r in zip(flatten(expected), flatten(dut_result)):
        assert OUT(v) == r
