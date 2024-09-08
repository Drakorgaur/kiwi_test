#!/bin/bash

python3 -m uvicorn src.app:app --uds $SOCKET_DIR/$SOCKET_NAME --workers 25 --log-config /etc/uvicorn_logging.json --no-access-log
