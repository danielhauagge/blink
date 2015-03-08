#!/usr/bin/env bash

#
# Runs the full image downloading pipeline, from spinning up EC2 instances to starting slaves
# and master process, to finally spinning down the EC2 instances.
#

if [ "$#" -ne 5 ]; then
	printf "Usage:\n\t%s <n_slaves> <max_images> <query> <collection>\n"  `basename $0`
fi

N_SLAVES=$1   #2
MAX_IMAGES=$2 #100
QUERY=$3      #"sopa"
COLLECTION=$4 #"sopa"

echo "Parameters:"
echo "  N_SLAVES = $N_SLAVES"
echo "MAX_IMAGES = $MAX_IMAGES"
echo "     QUERY = $QUERY"
echo "COLLECTION = $COLLECTION"
echo
for (( i = 10; i >= 0; i-- )); do
	printf "Starting in %3d seconds\r" $i
	sleep 1
done

# echo "Create blink slave instances"
# fab add_instance:count=$N_SLAVES

# echo "Install code on slaves"
# fab upgrade:collection=$COLLECTION,max_images=$MAX_IMAGES

# echo "Start master thread on local machine"
# python order.py --collection $COLLECTION --query $QUERY --max-images $MAX_IMAGES

while [[ $(python get_n_downloaded.py --collection $COLLECTION) -le $MAX_IMAGES ]]; do
	printf "Waiting for all images to be downloaded, currently %4d/%d\n" $(python get_n_downloaded.py --collection $COLLECTION) $MAX_IMAGES
	sleep 1
done

# echo "Shutting down all slaves"
# fab stop

echo "Terminating all slaves"
fab terminate
