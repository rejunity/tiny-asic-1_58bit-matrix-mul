<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works
Matrix multiplication is implemented using a systolic array architecture.

## How to test
Every cycle feed packed weight data to Input pins and input data to Bidirectional pins.
Strobe Enable pin to start receiving results of the matrix multiplication on the Output pins.

## External hardware
MCU is necessary to feed weights and input data into the accelerator and fetch the results.
