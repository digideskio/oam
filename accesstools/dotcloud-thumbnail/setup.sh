#!/bin/sh -x

DEPLOYMENT=$1
dotcloud create $DEPLOYMENT
dotcloud deploy -t redis $DEPLOYMENT.redis
sleep 90
PASSWORD=`dotcloud info $DEPLOYMENT.redis | grep "redis_password" | sed -e 's/.*: //'`
PORT=`dotcloud info $DEPLOYMENT.redis | grep redis:// | sed -e 's/.*://'`
echo "redis_host='redis.$DEPLOYMENT.dotcloud.com'" > settings.py
echo "redis_port=$PORT" >> settings.py
echo "redis_password='$PASSWORD'" >> settings.py
dotcloud deploy -t python $DEPLOYMENT.www
sleep 90
dotcloud push $DEPLOYMENT.www .
