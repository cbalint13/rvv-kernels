
## High performance RVV kernel generator to C & LLVM-IR dialects


### Usage

```
$ git clone https://github.com/cbalint13/rvv-kernels
$ cd rvv-kernels
$ docker build --file Dockerfile.ML.fedora --tag th1520-rvv .
$ docker run -it --rm -v "$PWD":/opt/src th1520-rvv bash
[root@b8032fd28a75 src]# ./make.sh cbalint@192.168.1.45

(x) Naive kernel:
  HEX = b0 28 00 00 b0 66 00 00 b0 a4 00 00 b0 e2 00 00
  O[] = 00010416 00026288 00042160 00058032

(x) MACC operations: elems[32] x lanes[4] = 256 Ops

(x) RVV kernel:
  HEX = b0 28 00 00 b0 66 00 00 b0 a4 00 00 b0 e2 00 00
  O[] = 00010416 00026288 00042160 00058032

RVV bench: 25.600 GOPS in 2.215818 secs
RVV speed: 11.553 GOPS/sec
```

### Notes

  * TH1520 implements an older v0.7.1 RVV vector ISA, unsupported by LLVM upstream
  * This generator emmits C / LLVM-IR forms of kernel, thus making it RVV version agnostic
  * TH1520 ```setvli``` ASIC implementation is a slow, see comments: [trials/riscv-asm.c](trials/riscv-asm.c)
  * The ```setvli``` slowness issue force the SVE (scalable vector) concept to avoid frequent ```setvli``` calls


### Changelog

  * **2024-Mar-13** intial realease, only ```int8``` with RVV 0.7.1 version
