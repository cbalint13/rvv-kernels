#!/bin/sh


rm -rf benchmark-*.log

for INT8_MACS in {1..32}
do
  for INT32_LANES in {1..4}
  do
    echo "Banchmark macs=$INT8_MACS lanes=$INT32_LANES"
    ./make.sh $INT8_MACS $INT32_LANES int8 v0.7.1 cbalint@192.168.1.45 | grep speed >> benchmark-int8.log
  done
done
