# *****************************************************************************
# * Copyright by ams OSRAM AG                                                 *
# * All rights are reserved.                                                  *
# *                                                                           *
# * IMPORTANT - PLEASE READ CAREFULLY BEFORE COPYING, INSTALLING OR USING     *
# * THE SOFTWARE.                                                             *
# *                                                                           *
# * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS       *
# * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT         *
# * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS         *
# * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT  *
# * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,     *
# * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT          *
# * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES LOSS OF USE,      *
# * DATA, OR PROFITS OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY      *
# * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT       *
# * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE     *
# * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.      *
# *****************************************************************************

"""
TMF8806 ZeroMQ client and data logger example.

This example shows how to use the ZeroMQ client to control
the TMF8806  Raspberry Pi EVM and log the measurement data.

To run these examples you must have a TMF8806 Raspberry Pi EVM connected. 
Or you can use a TMF8806 shield board with the matching ZeroMQ server. 
You must have the zmq_client Python Package installed.

It's recommended to use a Python virtual environment.

Example (Powershell):
    > python -m venv .venv-test
    > ./.venv-test/Scripts/Activate.ps1
    > pip install zmq_client-1.1.3.tar.gz
    > python example_zmq_client.py
"""

from pathlib import Path
from time import sleep

from zmq_client.tmf8x0x_zeromq_client import ZeroMqClient
from zmq_client.tmf8x0x_zeromq_common import MeasureCommand

CMD_SERVER_ADDR = "tcp://169.254.0.2:5555"
RESULT_SERVER_ADDR = "tcp://169.254.0.2:5556"

LOG_FILE = Path(__file__).parent / "example_log_active.csv"

client = ZeroMqClient()
client.connect(cmd_addr=CMD_SERVER_ADDR,
               result_addr=RESULT_SERVER_ADDR)
print("Connected to server")
try:
    # As a precaution false another measurement is running
    client.stop_measurement()

    # configure measurement
    meas_cfg = client.get_configuration()
    meas_cfg.data.kIters = 4000
    meas_cfg.data.data.spadSelect = 1

    # configure histogram dumping
    histogram_config = client.get_histogram_config()
    histogram_config.summed = True
    client.set_histogram_config(histogram_config)
    print("Configured histogram dumping")

    # Run factory calibration
    print("Start factory calibration")
    meas_cfg.data.command = MeasureCommand.FACTORY_CALIB
    client.start_measurement(meas_cfg)
    print("Finished factory calibration")

    client.start_logging(LOG_FILE)
    print(f"Start data logging -> {LOG_FILE.absolute()}")
    meas_cfg.data.command = MeasureCommand.MEASURE
    if client.start_measurement(meas_cfg):
        print("Started calibrated measurement")
    else:
        print("Started uncalibrated measurement")

    sleep(5.0)
    client.stop_measurement()
    client.stop_logging()
    print("Stopped measurement")

finally:
    client.stop_measurement()
    client.disconnect()
    print("Disconnect from server.")
