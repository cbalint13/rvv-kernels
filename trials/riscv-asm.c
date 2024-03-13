#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include <math.h>
#include <assert.h>

#include <sys/time.h>


#define INT8_MACS 32
#define INT32_LANES 4

/*
 *  This kernel dynamically shift between RVV modes (vsetvli).
 *
 *  On TH1520 vsetvli internal reconfiguration is VERY EXPENSIVE
 *  and this kernel drags down to ~1/5 of it's peak performance.
 *
 */
int32_t __attribute__((noinline))
dot_vec_dynamic(int32_t* output,
           const uint8_t* data,
           const int8_t* kernel) {

  // LMUL=2, instructions with odd register are illegal instructions
  // LMUL=4, vector registers are incremented by 4, else illegal instructions
  // LMUL=8, only v0, v8, v16, and v24 are valid vector registers

  // inline compute multipliers
  // MUL = 2**((INT8_MACS-1) / (1024 / 8 / sew))
  const uint8_t e8m  = ceil(INT8_MACS / (1024.f / 8 / 8));
  const uint8_t e16m = ceil(INT8_MACS / (1024.f / 8 / 16));
  const uint8_t e32m = ceil(INT32_LANES / (1024.f / 8 / 32));

  asm volatile (
    " li          a4, %[n_elem]               \n"
    " li          a5, %[n_lane]               \n"
    // init
    " li          a7, 0                       \n"
    " vmv.s.x     v0, zero                    \n"
    // load data
    " vsetvli     t4, a4, e8, m%[e8m], d1     \n"
    " vlbu.v      v8, (%[data])               \n"
    // multiply-accumulate
    ".MACC:                                   \n"
    " vsetvli     t5, a4, e8, m%[e8m], d1     \n"
    " vlb.v       v0, (%[kern])               \n"
    " vwmulsu.vv  v16, v0, v8                 \n"
    " vsetvli     t4, a4, e16, m%[e16m], d1   \n"
    " vmv.s.x     v0, zero                    \n"
    " vwredsum.vs v0, v16, v0                 \n"
    " add         %[kern], %[kern], a4        \n"
    " vsetvli     t5, a5, e32, m%[e32m], d1   \n"
    " vslideup.vx v24, v0, a7                 \n"
    " addi        a7, a7, 1                   \n"
    " bne         a7, a5, .MACC               \n"
    // store
    " vsw.v       v24, (%[outb])              \n"
    ::
      [n_elem] "I" (INT8_MACS),
      [n_lane] "I" (INT32_LANES),
      [data] "r" (data),
      [kern] "r" (kernel),
      [outb] "r" (output),
      [e8m]  "I" (e8m),
      [e16m] "I" (e16m),
      [e32m] "I" (e32m)
  );

  return 0;
}
