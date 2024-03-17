#include <stdint.h>
int32_t __attribute__((noinline))
dot_int8_kernel(int32_t* output,
           const uint8_t* data,
           const int8_t* kernel) {
  asm volatile (
    /// init
    "li          a4, 32                           \n"
    /// load data
    "//vsetvli     t4, a4, e8, m2, d1             \n"
    ".word 0b000101110111111011010111             \n"
    "vle8.v      v4, (%[data])                    \n"
    /// mul lane 0
    "vle8.v       v8, (%[kern])                   \n"
    "vwmulsu.vv  v16, v8, v4                      \n"
    "add         %[kern], %[kern], a4             \n"
    /// mul lane 1
    "vle8.v       v8, (%[kern])                   \n"
    "vwmulsu.vv  v20, v8, v4                      \n"
    "add         %[kern], %[kern], a4             \n"
    /// mul lane 2
    "vle8.v       v8, (%[kern])                   \n"
    "vwmulsu.vv  v24, v8, v4                      \n"
    "add         %[kern], %[kern], a4             \n"
    /// mul lane 3
    "vle8.v       v8, (%[kern])                   \n"
    "vwmulsu.vv  v28, v8, v4                      \n"
    /// reduce
    "//vsetvli     t4, a4, e16, m4, d1            \n"
    ".word 0b011001110111111011010111             \n"
    "vwredsum.vs v8, v16, v0                      \n"
    "vwredsum.vs v12, v20, v0                     \n"
    "vwredsum.vs v16, v24, v0                     \n"
    "vwredsum.vs v20, v28, v0                     \n"
    /// store
    "//vmv.x.s    t4, v8                          \n"
    ".word 0b0000110010100000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    "addi         %[outw], %[outw], 4             \n"
    "//vmv.x.s    t4, v12                         \n"
    ".word 0b0000110010110000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    "addi         %[outw], %[outw], 4             \n"
    "//vmv.x.s    t4, v16                         \n"
    ".word 0b0000110011000000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    "addi         %[outw], %[outw], 4             \n"
    "//vmv.x.s    t4, v20                         \n"
    ".word 0b0000110011010000000010111011010111   \n"
    "sw          t4, 0(%[outw])                   \n"
    ::
      [data] "r" (data),
      [kern] "r" (kernel),
      [outw] "r" (output)
  );
  return 0;
}
