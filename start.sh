#!/bin/sh

echo "Starting cyber-lab"

NETWORK_NAME="HireCarUK-wifi-$1"
AP_CONTAINER="HireCarUK-router-$1"
CLIENT_CONTAINER="HireCarUK-client-$1"
POS_CONTAINER="HireCarUK-till-03-$1"


echo $NETWORK_NAME
echo $AP_CONTIANER
echo $CLIENT_CONTAINER
echo $POS_CONTAINER


VAL="$(($1 + 0))"
NET_IP="192.168.$VAL.0/24"

BASE_PORT="$(($1 * 3 + 4300))"
AP_PORT="$(($BASE_PORT + 0))"
CLIENT_PORT="$(($BASE_PORT + 1))"
POS_PORT="$(($BASE_PORT + 2))"

echo $BASE_PORT
echo $AP_PORT
echo $CLIENT_PORT
echo $POS_PORT

start_container(){
	NAME=$1
	PORT=$2
	if [ "$(docker service ls -q -f name=$NAME)" ]; then
		CONTAINER_ID="$(docker service ls -q -f name=$NAME)"
		# cleanup
                echo "Removing running instance of $NAME with container ID $CONTAINER_ID"
                docker service rm $CONTAINER_ID
                echo "Removed $NAME"
	fi
	# run the container
        echo "Starting $NAME"
        docker service create --detach \
		--publish "$PORT:4200" \
		--name $NAME \
		--hostname $NAME \
		--network "$NETWORK_NAME" \
		-e SIAB_SUDO=true \
		-e SIAB_SSL=false \
		10.0.0.10:5000/basic-shell

        echo "Running $NAME"
}


start_network(){
	NAME=$1
	IP=$2
	if [ "$(docker network ls | grep $NAME)" ]; then
		echo "Removing exsisting $NAME network ..."
		docker network rm $NAME
	fi
	echo "Creating $NAME network ..."
        docker network create  \
	           -d overlay \
		   --attachable \
		   --subnet $IP \
                   $NAME
}

start_network $NETWORK_NAME $NET_IP
start_container $AP_CONTAINER $AP_PORT
start_container $POS_CONTAINER $POS_PORT
start_container $CLIENT_CONTAINER $CLIENT_PORT
