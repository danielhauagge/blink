blink
=====
*blink* is a tool for making Flickr queries and post-processing images and their metadata.  Nodes are coordinated through mongodb.  New queries are made with the order.py script and stored in the database.  Each worker runs the fetch.py script which polls the database and processes the associated image by requesting the actual photo and metadata from Flickr as well as estimating the focal length in pixels and computing SIFT feature points.

----

This tool is designed to be run on EC2 with an S3 bucket provisioned in a region where there are no additional bandwidth charges.  (e.g. EC2 North Virginia + S3 US Standard)  Transfer from internet to EC2 should not have additional bandwidth charges.  Transfer from S3 to internet does incur additional charges.

----

blink makes use of the following Flickr API calls:
* [flickr.photos.search](http://www.flickr.com/services/api/flickr.photos.search.html)
* [flickr.photos.getSizes](http://www.flickr.com/services/api/flickr.photos.getSizes.html)
* [flickr.photos.getExif](http://www.flickr.com/services/api/flickr.photos.getExif.html)

Keep this in mind when configuring the number of workers you run at one time:

[Flickr API](http://www.flickr.com/services/developer/api/)

"Limits: Since the Flickr API is quite easy to use, it's also quite easy to abuse, which threatens all services relying on the Flickr API. To help prevent this, we limit the access to the API per key. If your application stays under 3600 queries per hour across the whole key (which means the aggregate of all the users of your integration), you'll be fine. If we detect abuse on your key, we will need to expire the key, or turn it off, in order to preserve the Flickr API functionality for others (including us!). We also track usage on other factors as well to ensure no API user abuses the system."

It's probably pretty each to go over 1 query per second.  You can always create multple cfg files with different API keys and tell fetch.py to use it with --config.

Installation
====
Base Setup
----
```shell
sudo apt-get install git python-imaging python-boto python-numpy python-scipy python-pip
sudo apt-get install libmagickwand-dev
sudo pip install Wand
sudo pip install pymongo
git clone git@github.com:kmatzen/blink.git
cd blink
```

SIFT Worker
----
```shell
sudo apt-get install cmake libboost-python-dev
git submodule update --init libsiftfast-1.2
cd libsiftfast-1.2
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make
sudo make install
sudo cp /usr/local/lib/siftfastpy.so /usr/local/lib/python2.7/dist-packages/
```

DB Server
----
```shell
sudo apt-get install mongodb
```

/etc/mongodb.conf
```
bind_ip = 0.0.0.0
port = 27017
```

```shell
sudo service mongodb restart
mongo
  use <your db name>
  exit
```

Configuration
----
blink.cfg

```yaml
[flickr]
api_key = # Sign up for a Flickr API key
rate_limit = True # Limit Flickr API queries per second to 1

[mongodb]
host = foo.com # Server on which mongodb is running
port = 27017
database = flickr # database name that you created before
collection = # where you want to store the data

[aws]
aws_key = # Sign up for an account with Amazon
aws_secret = # and get the key too
bucket = blink # Images and SIFT results are stored at http://s3.amazonaws.com/<bucket>/<collection>/<photo>
ami = # <optional for Fabric>
spot_price = # <optional for Fabric>
key_name = # <optional for Fabric>
instance_type = # <optional for Fabric>
availability_zone_group = # <optional for Fabric>
security_group = # <optional for Fabric>

[workers]
tasks = PhotoTask,ExifTask,FocalTask,SiftTask # which tasks to run

[admin]
email = # your email address in case the fetch script raises a fatal exception
```

Running
====
On each worker:

```shell
./fetch.py
```

To make a query and add photos to database:

```shell
./order.py --query "your search query" --tag "a tag for organizing your photos"
```
