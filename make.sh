#!/bin/sh


NUM_ELEMS=32
NUM_LANES=4
VSPEC="v0.7.1"
DTYPE="int8"

# User params
if [ -n "$1" ]
then
  NUM_ELEMS=$1
fi

if [ -n "$2" ]
then
  NUM_LANES=$2
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
rm -rf dot_*_kernel.c
rm -rf dot_*_kernel.ir

##
## GENERATE
##

# Generate kernel (C)->(LLVM-IR)
./rvv-dot-kernel-gen.py --vspec $VSPEC --codegen c --elems $NUM_ELEMS --lanes $NUM_LANES --datatype $DTYPE --output dot_${DTYPE}_kernel.c
#clang -O3 --target=riscv64-linux-gnu -march=rv64gcv -S -emit-llvm -c dot_${DTYPE}_kernel.c -o dot_${DTYPE}_kernel.ir
# Generate kernel (LLVM-IR)
./rvv-dot-kernel-gen.py --vspec $VSPEC --codegen llvm --elems $NUM_ELEMS --lanes $NUM_LANES --datatype $DTYPE --output dot_${DTYPE}_kernel.ir

# Remove .srcloc section from IR
sed -i -e '/^\!5/d' dot_${DTYPE}_kernel.ir
sed -i -e 's|, !srcloc !5||' dot_${DTYPE}_kernel.ir
sed -i -e 's|, !5||' dot_${DTYPE}_kernel.ir

##
## COMPILE
##

CFLAGS="-O3 -mcpu=generic-rv64"

llc --mtriple=riscv64-redhat-linux -mcpu=generic-rv64 -mattr=+64bit,+a,+c,+d,+f,+m,+v -filetype=obj dot_${DTYPE}_kernel.ir -o objs/gen-kernel.o

echo "#define INT8 0" > rvv-bench.h
echo "#define FP16 1" >> rvv-bench.h
echo "#define FP32 2" >> rvv-bench.h
echo "#define DATA_TYPE ${DTYPE^^}" >> rvv-bench.h
echo "#define NUM_ELEMS $NUM_ELEMS" >> rvv-bench.h
echo "#define NUM_LANES $NUM_LANES" >> rvv-bench.h


clang -g $CFLAGS --target=riscv64-redhat-linux -march=rv64gc -mabi=lp64d -S -emit-llvm rvv-bench.c -o objs/rvv-bench.ir
llc $CFLAGS --mtriple=riscv64-redhat-linux -mattr=+64bit,+a,+c,+d,+f,+m -filetype=obj objs/rvv-bench.ir -o objs/rvv-bench.o
ld.lld -g -O3 objs/rvv-bench.o objs/gen-kernel.o -o rvv-bench \
  --dynamic-linker /lib/ld-linux-riscv64-lp64d.so.1 \
  --sysroot=/usr/riscv64-linux-gnu -lc \
  -L/usr/riscv64-linux-gnu/usr/lib/ \
  /usr/riscv64-linux-gnu/usr/lib/crt1.o \
  /usr/lib/gcc/riscv64-linux-gnu/14/libgcc.a

if [ $? -ne 0 ]; then
  exit 0
fi

###
### DEBUG
###

#riscv64-linux-gnu-objdump --dwarf=decodedline -d rvv-bench #| sed -n '/<dot_${DTYPE}_kernel>:/,/_start/p'

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
