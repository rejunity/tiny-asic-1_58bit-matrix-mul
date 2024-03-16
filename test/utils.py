import random

def s8_to_i32(s8):
    s8 = int(s8)
    return s8 if s8 < 0x80 else s8 - 0x100
assert s8_to_i32(0x00) == 0
assert s8_to_i32(0x01) == 1
assert s8_to_i32(0x7f) == 127
assert s8_to_i32(0x80) == -128
assert s8_to_i32(0xff) == -1

def pack_weights(weights, weights_per_byte=4):
    packed = 0
    if weights_per_byte == 5:
        for i in weights:
            if i == 0: w =   00
            if i > 0:  w = 0b01
            if i < 0:  w = 0b10
            packed = (packed * 3) + w
    else: # if weights_per_byte == 4:
        for i in weights:
            w = 0b11 if i  < 0 else 1
            w =    0 if i == 0 else w
            packed = (packed << 2) | w
    return packed
assert pack_weights([ 0, 0,  0, 0]) == 0
assert pack_weights([ 1, 0, -1, 0]) == 0b01_00_11_00
assert pack_weights([-1, 1, -1, 1]) == 0b11_01_11_01
assert pack_weights([-1, 1, -1, 1]*4) == 0b11011101_11011101_11011101_11011101
assert pack_weights([ 0, 0,  0, 0,  0], weights_per_byte=5) == 0
assert pack_weights([ 1, 0, -1, 0,  0], weights_per_byte=5) <= 255
assert pack_weights([ 1, 0, -1, 0,  0], weights_per_byte=5) == 1*3**4 + 0*3**3 + 2*3**2 + 0*3**1 + 0*3**0
assert pack_weights([-1, 1, -1, 1, -1], weights_per_byte=5) <= 255
assert pack_weights([-1, 1, -1, 1, -1], weights_per_byte=5) == 2*3**4 + 1*3**3 + 2*3**2 + 1*3**1 + 2*3**0

def pack_weights_as_u8_array(weights, weights_per_byte=4):
    return [pack_weights(weights[i:i+weights_per_byte], weights_per_byte) for i in range(0, len(weights), weights_per_byte)]
assert pack_weights_as_u8_array([-1, 1, -1, 1, -1]*4, weights_per_byte=5) == [2*3**4 + 1*3**3 + 2*3**2 + 1*3**1 + 2*3**0]*4

def unpack_weights(packed, weights_per_byte=4):
    weights = []
    if weights_per_byte == 5:
        while packed > 0:
            for _ in range(weights_per_byte):
                w = packed % 3
                weights.append(w if w != 0b10 else -1)
                packed //= 3
    else: # if weights_per_byte == 4:
        while packed > 0:
            for _ in range(weights_per_byte):
                w = packed & 0b11
                weights.append(w if w != 0b11 else -1)
                packed >>= 2
    return weights[::-1]
assert unpack_weights(pack_weights([ 1, 0, -1, 0])) == [ 1, 0, -1, 0]
assert unpack_weights(pack_weights([-1, 1, -1, 1])) == [-1, 1, -1, 1]
assert unpack_weights(pack_weights([ 1, 0, -1, 0,  0], weights_per_byte=5), weights_per_byte=5) == [ 1, 0, -1, 0,  0]
assert unpack_weights(pack_weights([-1, 1, -1, 1, -1], weights_per_byte=5), weights_per_byte=5) == [-1, 1, -1, 1, -1]

def random_matrix(lo, hi, dims):
    if isinstance(dims, (int)):
        return random_matrix(lo, hi, [dims])
    if len(dims) == 1:
        return [random.randint(lo, hi) for _ in range(dims[0])]
    return [[random.randint(lo, hi) for _ in range(dims[1])] for _ in range(dims[0])]
assert random_matrix(0, 0, 4) == [0, 0, 0, 0]
assert random_matrix(0, 0, (2, 2)) == [[0, 0], [0, 0]]

def const_matrix(val, dims):
    return random_matrix(val, val, dims)
assert const_matrix(1, 4) == [1, 1, 1, 1]
assert const_matrix(3, (2,2)) == [[3, 3], [3, 3]]

def shape(a):
    if isinstance(a, (int, float)):
        return ()
    if isinstance(a[0], (int, float)):
        return (len(a))
    return (len(a), len(a[0]))
assert shape(10) == ()
assert shape(random_matrix(0,1, 10)) == (10)
assert shape(random_matrix(0,1, (3,2))) == (3,2)

def flatten(matrix):
    return [x for row in matrix for x in row]
assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

def zigzag_h(matrix, col_elements_to_row):
    N = col_elements_to_row
    num_rows = len(matrix)
    num_cols = len(matrix[0])
    return [matrix[i*N+n][j] for i in range(num_rows//N) for j in range(num_cols) for n in range(N)]
assert zigzag_h([[1, 2, 3], [4, 5, 6]], 1) == [1, 2, 3, 4, 5, 6]
assert zigzag_h([[1, 2, 3], [4, 5, 6]], 2) == [1, 4, 2, 5, 3, 6]
assert zigzag_h([[1, 2], [4, 5], [6, 7], [8, 9]], 2) == [1, 4, 2, 5, 6, 8, 7, 9]

def zigzag_w(matrix, row_elements_to_col):
    N = row_elements_to_col
    num_rows = len(matrix)
    num_cols = len(matrix[0])
    return [matrix[i][j*N+n] for j in range(num_cols//N) for i in range(num_rows) for n in range(N)]
assert zigzag_w([[1, 2, 3],    [4, 5, 6]], 1) == [1, 4, 2, 5, 3, 6]
assert zigzag_w([[1, 2, 3, 4], [5, 6, 7, 8]], 2) == [1, 2, 5, 6, 3, 4, 7, 8]
assert zigzag_w([[1, 2, 3],    [4, 5, 6]], 3) == [1, 2, 3, 4, 5, 6]

def transpose(matrix):
    return [list(x) for x in zip(*matrix)]
assert transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]]

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

def matrix_mul(a, b):
    return [[dot(row, col) for col in zip(*b)] for row in a]
assert matrix_mul([[1, 2], [3, 4]], [[1, 2], [3, 4]]) == [[7, 10], [15, 22]]
assert matrix_mul([[-1, 1, 1, -1, 0, 1], [0, 1, 1, -1, 1, -1], [0, 0, 1, -1, -1, 1], [0, 1, 1, 0, 0, 1], [-1, -1, 1, -1, 1, 0]],
                   [[127], [127], [127], [127], [127], [127]]) == [[127], [127], [0], [381], [-127]]

# A = random_matrix(-1, 1, (16, 10))
# B = random_matrix(-127, 127, (10, 32))
# import numpy as np
# assert(np.all(matrix_mul(A, B) == np.array(A) @ np.array(B)))
# print(np.array(matrix_mul(A, B)).shape)

def generate_verilog_module_to_unpack_ternary_weights(func_name="unpack_ternary_weights", reverse_weight_order = True):
    print(\
        "module unpack_ternary_weights(input      [7:0] packed_weights,\n"
        "                              output reg [4:0] weights_zero,\n"
        "                              output reg [4:0] weights_sign);\n"
        "    always @(*) begin\n"
        "        case(packed_weights)")

    for i in range(255):
        weights_zero = 0b111_11 # if i != 0 else 1
        weights_sign = 0
        unpacked = unpack_weights(i, 5)
        if len(unpacked) <= 5:
            for w in (reversed(unpacked) if reverse_weight_order else unpacked):
                weights_zero = (weights_zero << 1) | (w == 0)
                weights_sign = (weights_sign << 1) | (w  < 0)
            weights_zero &= 0b111_11

            pretty_printed = ''.join([f"{str(n):>3}" for n in unpack_weights(i, 5)])
            print(f"        8'd{str(i).zfill(3)}: begin"
                f" weights_zero = 5'b{bin(weights_zero)[2:].zfill(5)};"
                f" weights_sign = 5'b{bin(weights_sign)[2:].zfill(5)};"
                f" end // {pretty_printed}")
    print(\
        "        default: {weights_zero, weights_sign} = 10'b0; // Default case\n"
        "        endcase\n"
        "    end\n"
        "endmodule\n")
# generate_verilog_module_to_unpack_ternary_weights()
