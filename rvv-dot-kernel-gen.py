#!/usr/bin/python3

import sys
import argparse


def rvv071_dot_int8_kernel(output, n_macs, n_lanes, codegen="llvm"):

    assert n_macs <= 64
    assert n_lanes <= 4
    assert n_macs * n_lanes <= 128
    assert codegen in ["llvm", "c"]

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
        '    "//li          a4, %i"' % n_macs,
        '    " .word 0b0000000%s00000000011100010011"' % f"{n_macs:06b}",
        '    "//li          a5, %i"' % n_lanes,
        '    " .word 0b0000000%s00000000011110010011"' % f"{n_lanes:06b}",
        '    /// load data',
        '    "//vsetvli     t4, a4, e8, m2, d1"',
        '    ".word 0x00177ed7"',
        '    "//vlbu.v      v2, (%[data])"',
        '    ".word 0x02058107"',
    ]

    # multiply lanes
    for lane in range(0, n_lanes):
        code += [
            '    /// mul lane %i' % lane,
            '    "//vlb.v       v4, (%[kern])"',
            '    ".word 0x12060207"',
            '    "//vwmulsu.vv  v%i, v4, v2"' % (8 + 4 * lane),
            '    ".word 0b0011101010010000010010%s1010111"' % f"{8+4*lane:05b}",
        ]
        if lane == n_lanes - 1:
            continue
        code += [
            '    "//add         %[kern], %[kern], a4"',
            '    ".half 0x963a"',
        ]

    # reduce lanes
    code += [
        '    /// reduce',
        '    "//vsetvli     t4, a4, e16, m4, d1"',
        '    ".word 0x00677ed7"',
    ]
    for lane in range(0, n_lanes):
        code += [
            '    "//vwredsum.vs v%i, v%i, v0"' % (4+4*lane, 8+4*lane),
            '    ".word 0b001100011%s00000000%s1010111"'
            % (f"{8+4*lane:05b}", f"{4+4*lane:05b}"),
        ]

    # store lanes
    code += [
        '    /// store',
        '    "//li          a4, 0"',
        '    ".half 0x4701"',
    ]
    for lane in range(0, n_lanes):
        code += [
            '    "//vext.x.v    t4, v%i, a4"' % (4+4*lane),
            '    ".word 0b000011001%s01110010111011010111"' % f"{4+4*lane:05b}",
            '    "//sw          t4, 0(%[outw])"',
            '    ".word 0x01d52023"',
        ]
        if lane == n_lanes - 1:
            continue
        code += [
            '    "//add         %[outw], %[outw], a5"',
            '    ".half 0x953e"',
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
        "--lanes", type=int, choices=range(1, 5), metavar="1..4", default=4
    )
    parser.add_argument(
        "--elems", type=int, choices=range(1, 65), metavar="1..64", default=32
    )

    args = parser.parse_args()

    # generate kernel
    rvv071_dot_int8_kernel(args.output, args.elems, args.lanes, args.codegen)


if __name__ == "__main__":
    main()
