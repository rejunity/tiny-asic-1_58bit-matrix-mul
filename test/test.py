# SPDX-FileCopyrightText: © 2023 Uri Shaked <uri@tinytapeout.com>
# SPDX-License-Identifier: MIT

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from utils import *

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
