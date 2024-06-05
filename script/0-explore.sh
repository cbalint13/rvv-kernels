#!/bin/sh


rm -rf benchmark-*.log

##
## int8
##
for NUM_ELEMS in {1..32}
do
  for NUM_LANES in {1..4}
  do
    echo "Banchmark int8 elems=$NUM_ELEMS lanes=$NUM_LANES"
    ./make.sh $NUM_ELEMS $NUM_LANES int8 v0.7.1 cbalint@192.168.1.45 | grep speed >> benchmark-int8.log
  done
done

./script/1-plotgraph.py --logs benchmark-int8.log --title 'RVV v0.7.1 int8 kernels benchmark (TH1520)'

##
## fp16
##
for NUM_ELEMS in {1..16}
do
  for NUM_LANES in {1..4}
  do
    echo "Banchmark fp16 elems=$NUM_ELEMS lanes=$NUM_LANES"
    ./make.sh $NUM_ELEMS $NUM_LANES fp16 v0.7.1 cbalint@192.168.1.45 | grep speed >> benchmark-fp16.log
  done
done

./script/1-plotgraph.py --logs benchmark-fp16.log --title 'RVV v0.7.1 fp16 kernels benchmark (TH1520)'

##
## fp32
##
for NUM_ELEMS in {1..8}
do
  for NUM_LANES in {1..4}
  do
    echo "Banchmark fp32 elems=$NUM_ELEMS lanes=$NUM_LANES"
    ./make.sh $NUM_ELEMS $NUM_LANES fp32 v0.7.1 cbalint@192.168.1.45 | grep speed >> benchmark-fp32.log
  done
done

./script/1-plotgraph.py --logs benchmark-fp32.log --title 'RVV v0.7.1 fp32 kernels benchmark (TH1520)'
