#!/bin/bash

nodes_x=$1
nodes_y=$1
timesteps=$2
E=$3
nu=$4
#dt=$3
echo "Running with $nodes_x nodes, $timesteps timesteps and dt of $dt"
python3 comparison.py $nodes_x $nodes_y $timesteps $E $nu #$dt # >> tmp.txt
rm tmp.txt
python3 plotter.py >> tmp.txt
rm tmp.txt
dir_name=plots_nodes_"$nodes_x"
mkdir $dir_name
mv *png $dir_name


nodes_x=$((nodes_x*2))
nodes_y=$((nodes_y*2))
timesteps=$((timesteps*4))
