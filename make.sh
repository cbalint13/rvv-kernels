#!/bin/sh


rm -rf dot_int8_kernel.c objs
mkdir -p objs

# Generate kernel (C)->(IR)
./rvv-dot-kernel-gen.py --codegen c --output dot_int8_kernel.c
clang -c dot_int8_kernel.c -o dot_int8_kernel.ir --target=riscv64-linux-gnu -S -emit-llvm -O3

# Generate kernel (IR)
#./rvv-dot-kernel-gen.py --codegen llvm --elems 32 --lanes 4 --output dot_int8_kernel.ir

# Remove .srcloc section from IR
sed -i -e '/^\!5/d' dot_int8_kernel.ir
sed -i -e 's|, !srcloc !5||' dot_int8_kernel.ir

##
## COMPILE
##
llc -mtriple=riscv64-unknown-elf -mcpu=generic-rv64 -mattr=+64bit,+a,+c,+d,+f,+m -filetype=obj dot_int8_kernel.ir -o objs/gen-kernel.o

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

# remote exec
if [ $# -gt 0 ]
then
  scp rvv-bench $1:/tmp/
  ssh $1 "/tmp/rvv-bench"
fi
