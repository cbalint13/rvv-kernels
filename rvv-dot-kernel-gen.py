#!/usr/bin/python3

import sys
import math
import argparse


def rvv_dot_kernel(output, n_macs, n_lanes, datatype="int8", codegen="llvm", vspec="v0.7.1"):

    assert n_macs <= 32
    assert n_lanes <= 4
    assert n_macs * n_lanes <= 128
    assert codegen in ["llvm", "c"]

    eM = {1:0b00, 2:0b01, 4:0b10, 8:0b11}

    M = [1, 2, 4, 8]
    # compute multipliers
    e8m  = M[max(range(len(M)), key=lambda i: ( M[i]-(n_macs / (1024.0 / 8 / 8)) < M[i-1])*i)]
    e16m = M[max(range(len(M)), key=lambda i: ( M[i]-(n_macs / (1024.0 / 8 / 16)) < M[i-1])*i)]

    # Registers Grouping
    # LMUL=2 (m2), instructions with odd register are illegal instructions
    # LMUL=4 (m4), vector registers are incremented by 4, else illegal instructions
    # LMUL=8 (m8), only v0, v8, v16, and v24 are valid vector registers

    # header
    if codegen == "c":
        head = [
            '#include <stdint.h>',
            'int32_t __attribute__((noinline))',
            'dot_int8_kernel(int32_t* output,',
            '           const uint8_t* data,',
            '           const int8_t* kernel) {',
            '  asm volatile (',
        ]
    elif codegen == "llvm":
        head = [
            'define dso_local signext i32 @dot_int8_kernel(ptr noundef %0, ptr noundef %1, ptr noundef %2) local_unnamed_addr #0 {',
            'tail call void asm sideeffect "',
        ]

    # load data
    code = [
        '    /// init',
        '    "li          a4, %i"' % n_macs,
        '    /// load data'
    ]

    if vspec == "v0.7.1":
        code += [
            '    "//vsetvli     t4, a4, e8, m%i, d1"' % e8m,
            '    ".word 0b00%s01110111111011010111"' % f"{eM[e8m]:02b}",
        ]
    elif vspec == "v1.0":
        code += [
            '    "vsetvli     t4,a4,e8,m%i,tu,mu"' % e8m
        ]
    else:
        assert False, "Unsupported vector extension version: `%s`" % vspec
    code += [
        '    "vle8.v      v4, (%[data])"',
    ]

    # multiply lanes
    for lane in range(0, n_lanes):
        mvec = 16 + e16m * lane
        code += [
            '    /// mul lane %i' % lane,
            '    "vle8.v       v8, (%[kern])"',
            '    "vwmulsu.vv  v%i, v8, v4"' % mvec,
        ]
        if lane == n_lanes - 1:
            continue
        code += [
            '    "add         %[kern], %[kern], a4"',
        ]

    # reduce lanes
    code += [
        '    /// reduce'
    ]
    if vspec == "v0.7.1":
        code += [
            '    "//vsetvli     t4, a4, e16, m%i, d1"' % e16m,
            '    ".word 0b01%s01110111111011010111"' % f"{eM[e16m]:02b}",
        ]
    elif vspec == "v1.0":
        code += [
            '    "vsetvli     t4,a4,e16,m%i,tu,mu"' % e16m,
        ]
    else:
        assert False, "Unsupported vector extension version: `%s`" % vspec

    for lane in range(0, n_lanes):
        mvec = 16 + e16m * lane
        rvec = 8 + e16m * lane
        code += [
            '    "vwredsum.vs v%i, v%i, v0"' % (rvec, mvec),
        ]

    # store lanes
    code += [
        '    /// store',
    ]
    for lane in range(0, n_lanes):
        rvec = 8 + e16m * lane
        if vspec == "v0.7.1":
            code += [
                '    "//vmv.x.s    t4, v%i"' % rvec,
                '    ".word 0b000011001%s00000010111011010111"' % f"{rvec:05b}",
            ]
        elif vspec == "v1.0":
            code += [
                '    "vmv.x.s    t4, v%i"' % rvec,
            ]
        else:
            assert False, "Unsupported vector extension version: `%s`" % vspec
        code += [
            '    "sw          t4, 0(%[outw])"',
        ]
        if lane == n_lanes - 1:
            continue
        code += [
            '    "addi         %[outw], %[outw], 4"',
        ]

    # footer
    if codegen == "c":
        tail = [
            '    ::',
            '      [data] "r" (data),',
            '      [kern] "r" (kernel),',
            '      [outw] "r" (output)',
            '  );',
            '  return 0;',
            '}',
        ]
    elif codegen == "llvm":
        tail = [
            '    ",',
            '    "r,r,r" (ptr %1, ptr %2, ptr %0) #1',
            '    ret i32 0',
            '}',
        ]

    # dump and format the code
    f = open(output, "w")
    for line in head:
        f.write(line + '\n')
    for line in code:
        if line[-1] == '"':
            line = line[:-1].ljust(50)
            if codegen == "c":
                line += '\\n"'
            elif codegen == "llvm":
                line = line.replace('"', "") + '\\0A'
                line = line.replace('%[data]', "$0") + '\\0A'
                line = line.replace('%[kern]', "$1") + '\\0A'
                line = line.replace('%[outw]', "$2") + '\\0A'
        f.write(line + '\n')
    for line in tail:
        f.write(line + '\n')
    f.close()


def main():

    # arguments
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Generate high performance RVV micro-kernels",
    )
    parser.add_argument("--output", help="Output filename", required=True)
    parser.add_argument(
        "--codegen", help="Codegen target", choices=["llvm", "c"], required=True
    )
    parser.add_argument(
        "--vspec", help="Codegen target", choices=["v0.7.1", "v1.0"], required=True
    )
    parser.add_argument(
        "--datatype", help="Data Type", choices=["int8", "fp16", "fp32"], required=True
    )
    parser.add_argument(
        "--lanes", type=int, choices=range(1, 5), metavar="1..4", default=4
    )
    parser.add_argument(
        "--elems", type=int, choices=range(1, 65), metavar="1..64", default=32
    )

    args = parser.parse_args()

    # generate kernel
    rvv_dot_kernel(args.output, args.elems, args.lanes, args.datatype, args.codegen, args.vspec)


if __name__ == "__main__":
    main()
