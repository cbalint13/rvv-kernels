#!/usr/bin/python3

import sys
import math
import argparse


def rvv_dot_kernel(output, n_elems, n_lanes, datatype="int8", codegen="llvm", vspec="v0.7.1"):

    e_size = 0
    if datatype == "int8":
        e_size = 1
    elif datatype == "fp16":
        e_size = 2
    elif datatype == "fp32":
        e_size = 4
    else:
        assert False, "Unsupported data type: `%s`" % datatype

    assert n_elems <= 32
    assert n_lanes <= 4
    assert n_elems * n_lanes * e_size <= 128
    assert codegen in ["llvm", "c"]

    # 8bit elements
    n_e8b = n_elems * e_size

    eMb = {1:0b00, 2:0b01, 4:0b10, 8:0b11}

    M = [1, 2, 4, 8]
    # compute multipliers
    eM  = M[max(range(len(M)), key=lambda i: (M[i] - (n_e8b / (1024.0 / 8 / (8*e_size))) < M[i - 1]) * i)]

    #e16m = M[max(range(len(M)), key=lambda i: (M[i] - (n_e8b / (1024.0 / 8 / 16)) < M[i - 1]) * i)]
    #print("DBG n_8b[%i] eM[%i] 8*e_size[%i] e16m[%i]" % (n_e8b, eM, 8*e_size, e16m))

    # Registers Grouping
    # LMUL=2 (m2), instructions with odd register are illegal instructions
    # LMUL=4 (m4), vector registers are incremented by 4, else illegal instructions
    # LMUL=8 (m8), only v0, v8, v16, and v24 are valid vector registers

    # header
    if codegen == "c":
        head = [
            '#include <stdint.h>',
            'void __attribute__((noinline))',
        ]
        if datatype == "int8":
            head += [
                'dot_%s_kernel(int16_t* output,' % datatype,
                '           const uint8_t* data,',
                '           const int8_t* kernel) {',
                '  asm volatile (',
            ]
        elif datatype == "fp16":
            head += [
                'dot_%s_kernel(__fp16* output,' % datatype,
                '           const __fp16* data,',
                '           const __fp16* kernel) {',
                '  asm volatile (',
            ]
        elif datatype == "fp32":
            head += [
                'dot_%s_kernel(float* output,' % datatype,
                '           const float* data,',
                '           const float* kernel) {',
                '  asm volatile (',
            ]
        else:
            assert False, "Unsupported data type: `%s`" % datatype
    elif codegen == "llvm":
        head = [
            'define dso_local void @dot_' + datatype + '_kernel(ptr noundef %0, ptr noundef %1, ptr noundef %2) local_unnamed_addr #0 {',
            'tail call void asm sideeffect "',
        ]

    # load data
    code = [
        '    /// init',
        '    "li          a4, %i"' % n_elems,
        '    "li          a5, %i"' % (n_elems * e_size),
        '    /// load data'
    ]

    if vspec == "v0.7.1":
        code += [
            '    "//vsetvli     t4, a4, e%i, m%i, d1"' % (8*e_size, eM),
            '    ".word 0b%s%s01110111111011010111"' % (f"{eMb[e_size]:02b}", f"{eMb[eM]:02b}")
        ]
    elif vspec == "v1.0":
        code += [
            '    "vsetvli     t4,a4,e%i,m%i,ta,ma"' % (8*e_size, eM)
        ]
    else:
        assert False, "Unsupported vector extension version: `%s`" % vspec

    code += [
        '    "vle%i.v     v4, (%%[data])"' % (8*e_size)
    ]

    # multiply lanes
    for lane in range(0, n_lanes):

        if datatype == "int8":
            mvec = 16 + eM*2 * lane
            code += [
                '    /// mul lane %i' % lane,
                '    "vle%i.v       v8, (%%[kern])"' % (8*e_size),
                '    "vwmulsu.vv  v%i, v8, v4"' % mvec,
            ]
        elif (datatype == "fp16") or (datatype == "fp32"):
            mvec = 16 + eM * lane
            code += [
                '    /// mul lane %i' % lane,
                '    "vle%i.v       v8, (%%[kern])"' % (8*e_size),
                '    "vfmul.vv  v%i, v8, v4"' % mvec,
            ]
        else:
            assert False, "Unsupported data type: `%s`" % datatype

        if lane == n_lanes - 1:
            continue

        code += [
            '    "add         %[kern], %[kern], a5"',
        ]

    # reduce lanes
    code += [
        '    /// reduce'
    ]
    if datatype == "int8":
      if vspec == "v0.7.1":
          code += [
              '    "//vsetvli     t4, a4, e16, m%i, d1"' % (eM*2),
              '    ".word 0b01%s01110111111011010111"' % f"{eMb[eM*2]:02b}",
          ]
      elif vspec == "v1.0":
          code += [
              '    "vsetvli     t4,a4,e16,m%i,ta,ma"' % (eM*2),
          ]
      else:
          assert False, "Unsupported vector extension version: `%s`" % vspec

    for lane in range(0, n_lanes):
        if datatype == "int8":
            mvec = 16 + eM*2 * lane
            rvec = 8 + eM*2 * lane
            code += [
                '    "vwredsum.vs v%i, v%i, v0"' % (rvec, mvec),
            ]
        elif (datatype == "fp16") or (datatype == "fp32"):
            mvec = 16 + eM * lane
            rvec = 8 + eM * lane
            code += [
                '    "vfredsum.vs v%i, v%i, v0"' % (rvec, mvec),
            ]
        else:
            assert False, "Unsupported data type: `%s`" % datatype

    # store lanes
    code += [
        '    /// store',
    ]
    for lane in range(0, n_lanes):
        if datatype == "int8":
            rvec = 8 + eM*2 * lane
        elif (datatype == "fp16") or (datatype == "fp32"):
            rvec = 8 + eM * lane
        else:
            assert False, "Unsupported data type: `%s`" % datatype
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
        if (datatype == "int8") or (datatype == "fp16"):
            code += [
                '    "sh          t4, 0(%[outw])"',
          ]
        elif datatype == "fp32":
            code += [
                '    "sw          t4, 0(%[outw])"',
            ]
        else:
            assert False, "Unsupported data type: `%s`" % datatype

        # stop condition
        if lane == n_lanes - 1:
            continue

        if (datatype == "int8") or (datatype == "fp16"):
            code += [
                '    "addi         %[outw], %[outw], 2"',
            ]
        elif datatype == "fp32":
            code += [
                '    "addi         %[outw], %[outw], 4"',
            ]
        else:
            assert False, "Unsupported data type: `%s`" % datatype

    # footer
    if codegen == "c":
        tail = [
            '    ::',
            '      [data] "r" (data),',
            '      [kern] "r" (kernel),',
            '      [outw] "r" (output)',
            '  );',
            '  return;',
            '}',
        ]
    elif codegen == "llvm":
        tail = [
            '    ",',
            '    "r,r,r" (ptr %1, ptr %2, ptr %0) #1',
            '    ret void',
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
