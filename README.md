blink
=====
*blink* is a tool for making Flickr queries and post-processing images and their metadata.  Nodes are coordinates through mongodb.  New queries are made with the order.py script and stored in the database.  Each worker runs the fetch.py script which polls the database and processes the associated image by requesting the actual photo and metadata from Flickr as well as estimating the focal length in pixels and computing SIFT feature points.

This tool is designed to be run on EC2 with an S3 bucket provisioned in a region where there are no additional bandwidth charges.  (e.g. EC2 North Virginia + S3 US Standard)  Transfer from internet to EC2 should not have additional bandwidth charges.  Transfer from S3 to internet does incur additional charges, but if you use the SIFT worker and transfer only the compressed keypoints, you will be transfering much less than if you were to transfer the images.

Installation
====
Base Setup
----
    sudo apt-get install git python-imaging python-boto python-numpy python-scipy python-pip
    sudo pip install pymongo
    git clone git@github.com:kmatzen/blink.git
    cd blink

SIFT Worker
----
    sudo apt-get install cmake libboost-python-dev
    git submodule update --init libsiftfast-1.2
    cd libsiftfast-1.2
    mkdir build
    cd build
    cmake -DCMAKE_BUILD_TYPE=Release ..
    make
    sudo make install
    sudo cp /usr/local/lib/siftfastpy.so /usr/local/lib/python2.7/dist-packages/

DB Server
----
    sudo apt-get install mongodb

    sudo vim /etc/mongodb.conf
    bind_ip = 0.0.0.0
    port = 27017

    sudo service mongodb restart
    mongo
      use <your db name>
      exit

Configuration
----
Edit blink.cfg

    [flickr]
    api_key = # Sign up for a Flickr API key

    [mongodb]
    host = # Server on which mongodb is running
    port = 27017 # port
    database = flickr # database name that you created before
    collection = # where you want to store the data

    [aws]
    aws_key = # Sign up for an account with Amazon
    aws_secret = # and get the key too
    bucket = blink # Images and SIFT results are stored at http://s3.amazonaws.com/<bucket>/<collection>/<photo>
    
Running
====
On each worker:

    ./fetch.py
    
To make a query and add photos to database:

    ./order.py --query "your search query" --tag "a tag for organizing your photos"
