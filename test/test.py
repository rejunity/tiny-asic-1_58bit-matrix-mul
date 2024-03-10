# SPDX-FileCopyrightText: © 2023 Uri Shaked <uri@tinytapeout.com>
# SPDX-License-Identifier: MIT

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

def s8_to_i32(s8):
    s8 = int(s8)
    return s8 if s8 < 0x80 else s8 - 0x100
assert(s8_to_i32(0x00) == 0)
assert(s8_to_i32(0x01) == 1)
assert(s8_to_i32(0x7f) == 127)
assert(s8_to_i32(0x80) == -128)
assert(s8_to_i32(0xff) == -1)

def pack_weights(weights):
    packed = 0
    for i in weights:
        w = 0b11 if i  < 0 else 1
        w =    0 if i == 0 else w
        packed = (packed << 2) | w
    return packed
assert pack_weights([ 0, 0,  0, 0]) == 0
assert pack_weights([ 1, 0, -1, 0]) == 0b01_00_11_00
assert pack_weights([-1, 1, -1, 1]) == 0b11_01_11_01
assert pack_weights([-1, 1, -1, 1]*4) == 0b11011101_11011101_11011101_11011101

def random_matrix(lo, hi, dims):
    if isinstance(dims, (int)):
        return random_matrix(lo, hi, [dims])
    if len(dims) == 1:
        return [random.randint(lo, hi) for _ in range(dims[0])]
    return [[random.randint(lo, hi) for _ in range(dims[1])] for _ in range(dims[0])]
assert(random_matrix(0, 0, 4) == [0, 0, 0, 0])
assert(random_matrix(0, 0, (2, 2)) == [[0, 0], [0, 0]])

def flatten(matrix):
    return [x for row in matrix for x in row]
assert(flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4])

def transpose(matrix):
    return [list(x) for x in zip(*matrix)]
assert(transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]])

def mul(vec, scale):
    return [x * scale for x in vec]
    
def dot(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a * b
    elif isinstance(a, (int, float)):
        return sum(mul(b, a))
    elif isinstance(b, (int, float)):
        return sum(mul(a, b))
    return sum([x*y for x,y in zip(a,b)])

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
    
    await ClockCycles(dut.clk, 5)
    dut.ena.value = 0
    await ClockCycles(dut.clk, 1)
    dut.ena.value = 1

    # Validate
    dut._log.info("Validate")
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == ( 1 * 127 * 6) >> 8
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == (-1 * 127 * 6) >> 8
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == ( 1 * 127 * 6) >> 8
    await ClockCycles(dut.clk, 1)
    assert s8_to_i32(dut.uo_out.value) == ( 0 * 127 * 6) >> 8

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
        assert s8_to_i32(dut.uo_out.value) == dot(w, inputs) >> 8

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
        assert s8_to_i32(dut.uo_out.value) == dot(w, inputs) >> 8

@cocotb.test()
async def test_4(dut):
    random.seed(3)
    N = 128
    weights = random_matrix(-1, 1, (N, 4))
    packed_weights = pack_weights(flatten(weights))
    # inputs = [127] * N
    inputs = range(N)

    print (weights)
    print (inputs)

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

    for w in transpose(weights):
        print (dot(w, inputs), dot(w, inputs) >> 8, s8_to_i32(dot(w, inputs) & 255))

    for w in transpose(weights):
        await ClockCycles(dut.clk, 1)
        print (dut.uo_out.value, int(dut.uo_out.value), s8_to_i32(dut.uo_out.value))
        # print (w.shape, np.array(inputs).shape, sum(w * inputs), sum(w * inputs) >> 8)
        # assert s8_to_i32(dut.uo_out.value) == (w @ np.array(inputs)) >> 8
        assert s8_to_i32(dut.uo_out.value) == dot(w, inputs) >> 8
