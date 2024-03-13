#include <stdint.h>
int32_t __attribute__((noinline))
dot_int8_kernel(int32_t* output,
           const uint8_t* data,
           const int8_t* kernel) {
  asm volatile (
    /// init
    "//li          a4, 32                         \n"
    " .word 0b000000010000000000000011100010011   \n"
    "//li          a5, 4                          \n"
    " .word 0b000000000010000000000011110010011   \n"
    /// load data
    "//vsetvli     t4, a4, e8, m2, d1             \n"
    ".word 0x00177ed7                             \n"
    "//vlbu.v      v2, (%[data])                  \n"
    ".word 0x02058107                             \n"
    /// mul lane 0
    "//vlb.v       v4, (%[kern])                  \n"
    ".word 0x12060207                             \n"
    "//vwmulsu.vv  v8, v4, v2                     \n"
    ".word 0b0011101010010000010010010001010111   \n"
    "//add         %[kern], %[kern], a4           \n"
    ".half 0x963a                                 \n"
    /// mul lane 1
    "//vlb.v       v4, (%[kern])                  \n"
    ".word 0x12060207                             \n"
    "//vwmulsu.vv  v12, v4, v2                    \n"
    ".word 0b0011101010010000010010011001010111   \n"
    "//add         %[kern], %[kern], a4           \n"
    ".half 0x963a                                 \n"
    /// mul lane 2
    "//vlb.v       v4, (%[kern])                  \n"
    ".word 0x12060207                             \n"
    "//vwmulsu.vv  v16, v4, v2                    \n"
    ".word 0b0011101010010000010010100001010111   \n"
    "//add         %[kern], %[kern], a4           \n"
    ".half 0x963a                                 \n"
    /// mul lane 3
    "//vlb.v       v4, (%[kern])                  \n"
    ".word 0x12060207                             \n"
    "//vwmulsu.vv  v20, v4, v2                    \n"
    ".word 0b0011101010010000010010101001010111   \n"
    /// reduce
    "//vsetvli     t4, a4, e16, m4, d1            \n"
    ".word 0x00677ed7                             \n"
    "//vwredsum.vs v4, v8, v0                     \n"
    ".word 0b0011000110100000000000001001010111   \n"
    "//vwredsum.vs v4, v8, v0                     \n"
    ".word 0b0011000110110000000000010001010111   \n"
    "//vwredsum.vs v4, v8, v0                     \n"
    ".word 0b0011000111000000000000011001010111   \n"
    "//vwredsum.vs v4, v8, v0                     \n"
    ".word 0b0011000111010000000000100001010111   \n"
    /// store
    "//li          a4, 0                          \n"
    ".half 0x4701                                 \n"
    "//vext.x.v    t4, v4, a4                     \n"
    ".word 0b0000110010010001110010111011010111   \n"
    "//sw          t4, 0(%[outw])                 \n"
    ".word 0x01d52023                             \n"
    "//add         %[outw], %[outw], a5           \n"
    ".half 0x953e                                 \n"
    "//vext.x.v    t4, v4, a4                     \n"
    ".word 0b0000110010100001110010111011010111   \n"
    "//sw          t4, 0(%[outw])                 \n"
    ".word 0x01d52023                             \n"
    "//add         %[outw], %[outw], a5           \n"
    ".half 0x953e                                 \n"
    "//vext.x.v    t4, v4, a4                     \n"
    ".word 0b0000110010110001110010111011010111   \n"
    "//sw          t4, 0(%[outw])                 \n"
    ".word 0x01d52023                             \n"
    "//add         %[outw], %[outw], a5           \n"
    ".half 0x953e                                 \n"
    "//vext.x.v    t4, v4, a4                     \n"
    ".word 0b0000110011000001110010111011010111   \n"
    "//sw          t4, 0(%[outw])                 \n"
    ".word 0x01d52023                             \n"
    ::
      [data] "r" (data),
      [kern] "r" (kernel),
      [outw] "r" (output)
  );
  return 0;
}
