blink
=====

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
    git submodule update libsiftfast-1.2
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
