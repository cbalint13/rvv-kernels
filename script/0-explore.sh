#!/bin/sh


#VERS="v0.7.1"
VERS="v1.0"

rm -rf benchmark-$VERS-*.log

##
## int8
##
for NUM_ELEMS in {1..32}
do
  for NUM_LANES in {1..4}
  do
    echo "Benchmark int8 elems=$NUM_ELEMS lanes=$NUM_LANES vers=$VERS"
    ./make.sh $NUM_ELEMS $NUM_LANES int8 $VERS cbalint@192.168.1.20 | grep speed >> benchmark-$VERS-int8.log
  done
done

./script/1-plotgraph.py --logs benchmark-$VERS-int8.log --title "RVV $VERS int8 kernels benchmark"

##
## fp16
##
for NUM_ELEMS in {1..16}
do
  for NUM_LANES in {1..4}
  do
    echo "Benchmark fp16 elems=$NUM_ELEMS lanes=$NUM_LANES vers=$VERS"
    ./make.sh $NUM_ELEMS $NUM_LANES fp16 $VERS cbalint@192.168.1.20 | grep speed >> benchmark-$VERS-fp16.log
  done
done

./script/1-plotgraph.py --logs benchmark-$VERS-fp16.log --title "RVV $VERS fp16 kernels benchmark"

##
## fp32
##
for NUM_ELEMS in {1..8}
do
  for NUM_LANES in {1..4}
  do
    echo "Benchmark fp32 elems=$NUM_ELEMS lanes=$NUM_LANES vers=$VERS"
    ./make.sh $NUM_ELEMS $NUM_LANES fp32 $VERS cbalint@192.168.1.20 | grep speed >> benchmark-$VERS-fp32.log
  done
done

./script/1-plotgraph.py --logs benchmark-$VERS-fp32.log --title "RVV $VERS fp32 kernels benchmark"
