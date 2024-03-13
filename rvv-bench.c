#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/time.h>

#include "rvv-bench.h"

extern int32_t dot_int8_kernel(int32_t* output, const uint8_t* data, const int8_t* kernel);


/* naive dotprod kernel */
uint64_t dot_sim(int32_t* output,
                const uint8_t* data,
                const int8_t* kernel) {

  uint64_t n_ops = 0;

  for (unsigned i = 0; i < INT32_LANES; ++i) {
    output[i] = 0;
    for (unsigned j = 0; j < INT8_MACS; ++j) {
      n_ops += 2;
      output[i] += data[j] * kernel[i * INT8_MACS + j];
    }
  }

  return n_ops;
}


/* debug result data */
void data_dump(int32_t* output, uint64_t size) {

  printf("  HEX =");
  for (unsigned i = 0; i < size*4; ++i) {
    uint8_t *buff = (uint8_t *)output;
    printf(" %02x", buff[i]);
  }
  printf("\n");

  printf("  O[] =");
  for (unsigned i = 0; i < size; ++i) {
    int32_t *buff = (int32_t *)output;
    printf(" %08i", buff[i]);
  }
  printf("\n");

}

int main() {

  uint8_t data[INT8_MACS];
  int8_t kernel[INT8_MACS*INT32_LANES];
  int32_t output[INT32_LANES];

  uint64_t usec_elapsed;
  struct timeval start, stop;

  // PREPARE DATA

  for (size_t i=0; i<INT8_MACS*INT32_LANES; ++i) {
    kernel[i] = i;
    if (i < INT8_MACS) data[i] = i;
    if (i < INT32_LANES) output[i] = 0;
  }

  // SIMULATE

  printf("\n");
  printf("(x) Naive kernel:\n");
  uint64_t num_ops = dot_sim(output, data, kernel);
  data_dump(output, sizeof(output)/sizeof(uint32_t));

  printf("\n");
  printf("(x) MACC operations: elems[%i] x lanes[%i] = %lu Ops\n", INT8_MACS, INT32_LANES, num_ops);

  // clear buffer
  for (size_t i=0; i<INT32_LANES; ++i) {
    output[i] = 0;
  }

  // BENCHMARK

  printf("\n");
  const uint64_t n_iters = 1e8;
  {
    assert(INT8_MACS && INT32_LANES);
    assert(INT8_MACS * 16 <= 1024); // max 64
    assert(INT32_LANES * 32 <= 1024); // max 32
    assert(INT8_MACS * INT32_LANES <= 128);

    // benchmark
    gettimeofday(&start,NULL);
    for (uint64_t k=0; k<n_iters; k++) {
      dot_int8_kernel(output, data, kernel);
    }
    gettimeofday(&stop,NULL);

     printf("(x) RVV kernel:\n");
    data_dump(output, sizeof(output)/sizeof(uint32_t));
  }

  // STATISTICS
  printf("\n");
  usec_elapsed = (stop.tv_sec - start.tv_sec) * 1e6;
  usec_elapsed += stop.tv_usec - start.tv_usec;
  printf("RVV bench: %.3f GOPS in %.6f secs\n", (num_ops * n_iters) / 1e9, (double)(usec_elapsed / 1e6));

  double ops = ((num_ops * n_iters) / 1e9) / (double)(usec_elapsed / 1e6);
  printf("RVV speed: %.3f GOPS/sec [elems=%i lanes=%i]\n", ops, INT8_MACS, INT32_LANES);

  return 0;
}
