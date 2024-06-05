#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/time.h>

#include "rvv-bench.h"

#include <limits.h>
#include <stdint.h>

extern void dot_int8_kernel(int32_t* output, const uint8_t* data, const int8_t* kernel);
extern void dot_fp16_kernel(__fp16* output, const __fp16* data, const __fp16* kernel);
extern void dot_fp32_kernel(float* output, const float* data, const float* kernel);

/* naive dotprod kernel */
#if DATA_TYPE == INT8
uint64_t dot_sim(int32_t* output, const uint8_t* data, const int8_t* kernel) {
#elif DATA_TYPE == FP16
uint64_t dot_sim(__fp16* output, const __fp16* data, const __fp16* kernel) {
#elif DATA_TYPE == FP32
uint64_t dot_sim(float* output, const float* data, const float* kernel) {
#else
  #error Invalid data type DATA_TYPE
#endif

  uint64_t n_ops = 0;

  for (unsigned i = 0; i < NUM_LANES; ++i) {
    output[i] = 0;
    for (unsigned j = 0; j < NUM_ELEMS; ++j) {
      n_ops += 2;
      output[i] += data[j] * kernel[i * NUM_ELEMS + j];
    }
  }

  return n_ops;
}


/* debug result data */
#if DATA_TYPE == INT8
void data_dump(int32_t* output, uint64_t size) {
#elif DATA_TYPE == FP16
void data_dump(__fp16* output, uint64_t size) {
#elif DATA_TYPE == FP32
void data_dump(float* output, uint64_t size) {
#else
  #error Invalid data type DATA_TYPE
#endif

  printf("  HEX =");
  for (unsigned i = 0; i < size*4; ++i) {
    uint8_t *buff = (uint8_t *)output;
    printf(" %02x", buff[i]);
  }
  printf("\n");

  printf("  O[] =");
  for (unsigned i = 0; i < size; ++i) {
#if DATA_TYPE == INT8
    int32_t *buff = (int32_t *)output;
    printf(" %08i", buff[i]);
#elif DATA_TYPE == FP16
    __fp16 *buff = (__fp16 *)output;
    printf(" %f", buff[i]);
#elif DATA_TYPE == FP32
    float *buff = (float *)output;
    printf(" %f", buff[i]);
#else
  #error Invalid data type DATA_TYPE
#endif
  }
  printf("\n");

}

int main(int argc, char **argv) {

#if DATA_TYPE == INT8
  uint8_t data[NUM_ELEMS];
  int8_t kernel[NUM_ELEMS*NUM_LANES];
  int32_t output0[NUM_LANES];
  int32_t output1[NUM_LANES];
#elif DATA_TYPE == FP16
  __fp16 data[NUM_ELEMS];
  __fp16 kernel[NUM_ELEMS*NUM_LANES];
  __fp16 output0[NUM_LANES];
  __fp16 output1[NUM_LANES];
#elif DATA_TYPE == FP32
  float data[NUM_ELEMS];
  float kernel[NUM_ELEMS*NUM_LANES];
  float output0[NUM_LANES];
  float output1[NUM_LANES];
#else
  #error Invalid data type DATA_TYPE
#endif

  uint64_t n_iters = 1e8;
  uint64_t usec_elapsed;
  struct timeval start, stop;

  if (argc > 1) n_iters = 1;

  // DATA PREPARING

  for (size_t i=0; i<NUM_ELEMS*NUM_LANES; ++i) {
    kernel[i] = i;
    if (i < NUM_ELEMS) data[i] = i;
    if (i < NUM_LANES) output0[i] = 0;
    if (i < NUM_LANES) output1[i] = 0;
  }

  // SIMULATE

  printf("\n");
  printf("(x) Naive kernel:\n");
  uint64_t num_ops = dot_sim(output0, data, kernel);
  data_dump(output0, sizeof(output0)/sizeof(output0[0]));

  printf("\n");
  printf("(x) MACC operations: elems[%i] x lanes[%i] = %llu Ops\n", NUM_ELEMS, NUM_LANES, num_ops);

  // BENCHMARK

  printf("\n");
  {
    assert(NUM_ELEMS && NUM_LANES);
    assert(NUM_ELEMS * sizeof(data[0]) * 16 <= 1024); // max 64
    assert(NUM_LANES * sizeof(output1[0]) * 32 <= 1024); // max 32
    assert(NUM_ELEMS * NUM_LANES * sizeof(data[0]) <= 128);

    // benchmark
    gettimeofday(&start,NULL);
    for (uint64_t k=0; k<n_iters; k++) {
#if DATA_TYPE == INT8
      dot_int8_kernel(output1, data, kernel);
#elif DATA_TYPE == FP16
      dot_fp16_kernel(output1, data, kernel);
#elif DATA_TYPE == FP32
      dot_fp32_kernel(output1, data, kernel);
#else
  #error Invalid data type DATA_TYPE
#endif
    }
    gettimeofday(&stop,NULL);

    printf("(x) RVV kernel:\n");
    data_dump(output1, sizeof(output1)/sizeof(output1[0]));
  }

  // VALIDATE

  for (size_t i=0; i<NUM_LANES; ++i) {
#if DATA_TYPE == INT8
    assert(output0[i] == output1[i]);
#else
    assert(fabsf(output0[i] - output1[i]) < 8);
#endif
  }

  // STATISTICS

  printf("\n");
  usec_elapsed = (stop.tv_sec - start.tv_sec) * 1e6;
  usec_elapsed += stop.tv_usec - start.tv_usec;
  printf("RVV bench: %.3f GOPS in %.6f secs\n", (num_ops * n_iters) / 1e9, (double)(usec_elapsed / 1e6));

  double ops = ((num_ops * n_iters) / 1e9) / (double)(usec_elapsed / 1e6);
  printf("RVV speed: %.3f GOPS/sec [elems=%i lanes=%i]\n", ops, NUM_ELEMS, NUM_LANES);

  return 0;
}
