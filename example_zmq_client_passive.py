# /*****************************************************************************
# * Copyright (c) [2024] ams-OSRAM AG                                          *
# * All rights are reserved.                                                   *
# *                                                                            *
# * FOR FULL LICENSE TEXT SEE LICENSE.TXT                                      *
# ******************************************************************************/
 

"""
TMF8806 ZeroMQ client and data logger example.

This example shows how to use the ZeroMQ client as a passive
data logger. The device is controlled by the TMF8806 GUI and
client log the measurement data only.

To run these examples you must have a TMF8806 Raspberry Pi EVM connected. 
Or you can use a TMF8806 shield board with the matching ZeroMQ server. 
You must have the zmq_client Python Package installed.

It's recommended to use a Python virtual environment.

Example (Powershell):
    > python -m venv .venv-test
    > ./.venv-test/Scripts/Activate.ps1
    > pip install zmq_client-1.1.9.tar.gz
    > python example_zmq_client.py
"""

from pathlib import Path
from time import sleep

from zmq_client.tmf8x0x_zeromq_client import ZeroMqClient

CMD_SERVER_ADDR = "tcp://169.254.0.2:5555"
RESULT_SERVER_ADDR = "tcp://169.254.0.2:5556"

LOG_FILE = Path(__file__).parent / "example_log_passive.csv"

client = ZeroMqClient()
client.connect(cmd_addr=CMD_SERVER_ADDR,
               result_addr=RESULT_SERVER_ADDR)
print("Connected to server")

try:
    client.start_logging(LOG_FILE)
    print(f"Start data logging -> {LOG_FILE.absolute()}")
    sleep(5.0)
    client.stop_logging()

finally:
    client.disconnect()
    print("Disconnect from server.")
