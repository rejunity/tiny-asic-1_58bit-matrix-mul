import random

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

def zigzag(matrix, col_elements_to_row):
    N = col_elements_to_row
    num_rows = len(matrix)
    num_cols = len(matrix[0])
    return [matrix[i//N+n][j] for i in range(num_rows//N) for j in range(num_cols) for n in range(N)]
assert(zigzag([[1, 2, 3], [4, 5, 6]], 1) == [1, 2, 3, 4, 5, 6])
assert(zigzag([[1, 2, 3], [4, 5, 6]], 2) == [1, 4, 2, 5, 3, 6])

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

def matrix_mul(a, b):
    return [[dot(row, col) for col in zip(*b)] for row in a]
assert(matrix_mul([[1, 2], [3, 4]], [[1, 2], [3, 4]]) == [[7, 10], [15, 22]])

# A = random_matrix(-1, 1, (16, 10))
# B = random_matrix(-127, 127, (10, 32))
# import numpy as np
# assert(np.all(matrix_mul(A, B) == np.array(A) @ np.array(B)))
# print(np.array(matrix_mul(A, B)).shape)

