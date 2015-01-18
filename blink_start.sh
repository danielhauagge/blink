#!/usr/bin/env bash

#
# 
#

N_SLAVES=2
MAX_IMAGES=100
QUERY="sopa"
COLLECTION="sopa"

echo "Create blink slave instances"
fab add_instance:count=$N_SLAVES

echo "Install code on slaves"
fab upgrade:collection=$COLLECTION,max_images=$MAX_IMAGES

echo "Start master thread on local machine"
python order.py --collection $COLLECTION --query $QUERY --max-images $MAX_IMAGES

while [[ $(python get_n_downloaded.py --collection $COLLECTION) -le $MAX_IMAGES ]]; do
	printf "Waiting for all images to be downloaded, currently %4d/%d\n" $(python get_n_downloaded.py --collection $COLLECTION) $MAX_IMAGES
	sleep 1
done

# echo "Shutting down all slaves"
# fab stop

echo "Terminating all slaves"
fab terminate
