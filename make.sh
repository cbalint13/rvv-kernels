#!/bin/sh


INT8_MACS=32
INT32_LANES=4
VSPEC="v0.7.1"
DTYPE="int8"

# User params
if [ -n "$1" ]
then
  INT8_MACS=$1
fi

if [ -n "$2" ]
then
  INT32_LANES=$2
fi

if [ -n "$3" ]
then
  DTYPE=$3
fi

if [ -n "$4" ]
then
  VSPEC=$4
fi


# Cleanup
rm -rf objs
mkdir -p objs
rm -rf rvv-bench
rm -rf rvv-bench.h
rm -rf dot_int8_kernel.*

##
## GENERATE
##

# Generate kernel (C)->(LLVM-IR)
./rvv-dot-kernel-gen.py --vspec $VSPEC --codegen c --elems $INT8_MACS --lanes $INT32_LANES --datatype $DTYPE --output dot_int8_kernel.c
clang -O3 --target=riscv64-linux-gnu -march=rv64gcv -S -emit-llvm -c dot_int8_kernel.c -o dot_int8_kernel.ir

# Generate kernel (LLVM-IR)
#./rvv-dot-kernel-gen.py --vspec $VSPEC --codegen llvm --elems $INT8_MACS --lanes $INT32_LANES --datatype $DTYPE --output dot_int8_kernel.ir

# Remove .srcloc section from IR
sed -i -e '/^\!5/d' dot_int8_kernel.ir
sed -i -e 's|, !srcloc !5||' dot_int8_kernel.ir

##
## COMPILE
##

CFLAGS="-O3 -mcpu=generic-rv64"

llc --mtriple=riscv64-redhat-linux -mcpu=generic-rv64 -mattr=+64bit,+a,+c,+d,+f,+m,+v -filetype=obj dot_int8_kernel.ir -o objs/gen-kernel.o

echo "#define INT8_MACS $INT8_MACS" > rvv-bench.h
echo "#define INT32_LANES $INT32_LANES" >> rvv-bench.h

clang -g $CFLAGS --target=riscv64-redhat-linux -march=rv64gc -mabi=lp64d -S -emit-llvm rvv-bench.c -o objs/rvv-bench.ir
llc $CFLAGS --mtriple=riscv64-redhat-linux -mattr=+64bit,+a,+c,+d,+f,+m -filetype=obj objs/rvv-bench.ir -o objs/rvv-bench.o
ld.lld -g -O3 objs/rvv-bench.o objs/gen-kernel.o -o rvv-bench \
  --dynamic-linker /lib/ld-linux-riscv64-lp64d.so.1 \
  --sysroot=/usr/riscv64-linux-gnu -lc \
  -L/usr/riscv64-linux-gnu/usr/lib/ \
  /usr/riscv64-linux-gnu/usr/lib/crt1.o


if [ $? -ne 0 ]; then
  exit 0
fi

###
### DEBUG
###

#riscv64-linux-gnu-objdump --dwarf=decodedline -d rvv-bench | sed -n '/<dot_int8_kernel>:/,/_start/p'

###
### BENCHMARK (remote)
###

if [ -n "$5" ]
then

  if [ "$5" == "qemu" ]
  then
    qemu-riscv64 -cpu rv64,v=true,vlen=128,vext_spec=v1.0 -L /usr/riscv64-linux-gnu/ rvv-bench 1
  else
    set -x
    scp rvv-bench $5:/tmp/
    ssh $5 "/tmp/rvv-bench"
  fi
fi
