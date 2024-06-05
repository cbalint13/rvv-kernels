#include <stdint.h>
void __attribute__((noinline))
dot_fp16_kernel(__fp16* output,
           const __fp16* data,
           const __fp16* kernel) {
  asm volatile (
    /// init
    "li          a4, 16                           \n"
    "li          a5, 32                           \n"
    /// load data
    "//vsetvli     t4, a4, e16, m4, d1            \n"
    ".word 0b011001110111111011010111             \n"
    "vle16.v     v4, (%[data])                    \n"
    /// mul lane 0
    "vle16.v       v8, (%[kern])                  \n"
    "vfmul.vv  v16, v8, v4                        \n"
    "add         %[kern], %[kern], a5             \n"
    /// mul lane 1
    "vle16.v       v8, (%[kern])                  \n"
    "vfmul.vv  v20, v8, v4                        \n"
    "add         %[kern], %[kern], a5             \n"
    /// mul lane 2
    "vle16.v       v8, (%[kern])                  \n"
    "vfmul.vv  v24, v8, v4                        \n"
    "add         %[kern], %[kern], a5             \n"
    /// mul lane 3
    "vle16.v       v8, (%[kern])                  \n"
    "vfmul.vv  v28, v8, v4                        \n"
    /// reduce
    "vfredsum.vs v8, v16, v0                      \n"
    "vfredsum.vs v12, v20, v0                     \n"
    "vfredsum.vs v16, v24, v0                     \n"
    "vfredsum.vs v20, v28, v0                     \n"
    /// store
    "//vmv.x.s    t4, v8                          \n"
    ".word 0b0000110010100000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    "addi         %[outw], %[outw], 2             \n"
    "//vmv.x.s    t4, v12                         \n"
    ".word 0b0000110010110000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    "addi         %[outw], %[outw], 2             \n"
    "//vmv.x.s    t4, v16                         \n"
    ".word 0b0000110011000000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    "addi         %[outw], %[outw], 2             \n"
    "//vmv.x.s    t4, v20                         \n"
    ".word 0b0000110011010000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    ::
      [data] "r" (data),
      [kern] "r" (kernel),
      [outw] "r" (output)
  );
  return;
}
