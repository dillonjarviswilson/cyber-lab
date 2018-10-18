#!/bin/sh

echo "Stopping cyber-lab"

NETWORK_NAME="HireCarUK-wifi-$1"
AP_CONTAINER="HireCarUK-router-$1"
CLIENT_CONTAINER="HireCarUK-client-$1"
POS_CONTAINER="HireCarUK-till-03-$1"

stop_container(){
	NAME=$1
	if [ "$(docker service ls -q -f name=$NAME)" ]; then
		CONTAINER_ID="$(docker service ls -q -f name=$NAME)"
		# cleanup
                echo "Removing running instance of $NAME with container ID $CONTAINER_ID"
                docker service rm $CONTAINER_ID
                echo "Removed $NAME"
	fi
}


stop_network(){
	NAME=$1
	if [ "$(docker network ls | grep $NAME)" ]; then
		echo "Removing $NAME network ..."
		docker network rm $NAME
	fi
}

stop_container $AP_CONTAINER
stop_container $POS_CONTAINER
stop_container $CLIENT_CONTAINER
stop_network $NETWORK_NAME 
