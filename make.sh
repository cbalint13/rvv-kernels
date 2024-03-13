#!/bin/sh


INT8_MACS=32
INT32_LANES=4

# User params
if [ -n "$1" ]
then
  INT8_MACS=$1
fi

if [ -n "$2" ]
then
  INT32_LANES=$2
fi

# Cleanup
rm -rf objs
mkdir -p objs
rm -rf dot_int8_kernel.c rvv-bench.h

##
## GENERATE
##

# Generate kernel (C)->(LLVM-IR)
./rvv-dot-kernel-gen.py --codegen c --elems $INT8_MACS --lanes $INT32_LANES --output dot_int8_kernel.c
clang -c dot_int8_kernel.c -o dot_int8_kernel.ir --target=riscv64-linux-gnu -S -emit-llvm -O3

# Generate kernel (LLVM-IR)
#./rvv-dot-kernel-gen.py --codegen llvm --elems $INT8_MACS --lanes $INT8_LANES --output dot_int8_kernel.ir

# Remove .srcloc section from IR
sed -i -e '/^\!5/d' dot_int8_kernel.ir
sed -i -e 's|, !srcloc !5||' dot_int8_kernel.ir

##
## COMPILE
##

llc -mtriple=riscv64-unknown-elf -mcpu=generic-rv64 -mattr=+64bit,+a,+c,+d,+f,+m -filetype=obj dot_int8_kernel.ir -o objs/gen-kernel.o

echo "#define INT8_MACS $INT8_MACS" > rvv-bench.h
echo "#define INT32_LANES $INT32_LANES" >> rvv-bench.h

CFLAGS="-Wall -O3 -g -mabi=lp64d -march=rv64gc"
riscv64-linux-gnu-gcc -c rvv-bench.c -o objs/rvv-bench.o $CFLAGS
riscv64-linux-gnu-gcc objs/rvv-bench.o objs/gen-kernel.o -o rvv-bench $CFLAGS
# fixme
#clang --target=riscv64-unknown-elf -mcpu=generic-rv64 -march=+64bit,+a,+c,+d,+f,+m -mabi=lp64d objs/rvv-bench.o objs/gen-kernel.o -o rvv-bench
#clang --target=riscv64-linux-gnu -mcpu=generic-rv64 -mabi=lp64d -march=+64bit,+a,+c,+d,+f,+m objs/rvv-bench.o objs/gen-kernel.o -o rvv-bench
#clang --target=riscv64-unknown-elf -mcpu=generic-rv64 -mabi=lp64d -march=+64bit,+a,+c,+d,+f,+m objs/rvv-bench.o objs/gen-kernel.o -o rvv-bench

if [ $? -ne 0 ]; then
  exit 0
fi

###
### BENCHMARK (remote)
###

if [ -n "$3" ]
then
  set -x
  scp rvv-bench $3:/tmp/
  ssh $3 "/tmp/rvv-bench"
fi
