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
TMF8806 ZeroMQ client and calibration / cross talk measurement example

This example shows how to use the ZeroMQ client to control
the TMF8806 and log the measurement data in a custom format.

To run this example you must have a TMF8806 Raspberry Pi EVM
connected. Or you can use a TMF8806 shield board with them matching
ZeroMQ server. You must have the zmq_client Python Package installed.
"""

import zmq
from zmq_client.tmf8x0x_zeromq_client import ZeroMqClient
from zmq_client.tmf8x0x_zeromq_client import ResultContainer
from zmq_client.tmf8x0x_zeromq_common import MeasureCommand
from zmq_client.tmf8806_regs import tmf8806MeasureCmd
from pathlib import Path

if __name__ == "__main__":

    CMD_SERVER_ADDR = "tcp://169.254.0.2:5555"
    RESULT_SERVER_ADDR = "tcp://169.254.0.2:5556"
    LOG_FILE = Path(__file__).parent / "example_log_calibration.csv"

    f = open(LOG_FILE, "w")

    def log(line : str, to_console_too : bool = False):        
        f.write(f"{line}\n")
        if to_console_too:
            print(line)

    def execute_single_factory_calibration( zmq_client: ZeroMqClient, measurement_config: tmf8806MeasureCmd ):

        # run factory calibration
        log("#COM;run factory calibration")
        measurement_config.data.command = MeasureCommand.FACTORY_CALIB
        zmq_client.start_measurement(measurement_config)

        log("#COM;start measurements")
        measurement_config.data.command = MeasureCommand.MEASURE
        zmq_client.start_measurement(measurement_config)

        # get a single measurement (one-shot mode)
        rc = ResultContainer(buffer=zmq_client._result_socket.recv(copy=True)).results
        if rc is not None:
            log(f"#XTALK;{rc.result.xtalk}",True)
            for hist in range(0,len(rc.histogramsProx)):
                log(f"#HSHORT{hist};{';'.join(map(str,rc.histogramsProx[hist]))}")

        log("#COM;stop measurements")
        zmq_client.stop_measurement()

    zmq_client = ZeroMqClient()
    zmq_client.connect(cmd_addr=CMD_SERVER_ADDR,result_addr=RESULT_SERVER_ADDR)
    log("sep=;")
    log("#COM;connected to server")

    try:
        # as a precaution false another measurement is running
        zmq_client.stop_measurement()

        # log header 
        log("#COM;comment string")
        log("#XTALK;cross-talk value")
        log("#HSHORT0;short range histogram bin values (TDC0)")
        log("#HSHORT1;short range histogram bin values (TDC1)")
        log("#HSHORT2;short range histogram bin values (TDC2)")
        log("#HSHORT3;short range histogram bin values (TDC3)")
        log("#HSHORT4;short range histogram bin values (TDC4)")
        
        log("#COM;connecting to result socket")
        zmq_client._result_socket.connect(zmq_client._result_addr)
        # only get latest result data all the time
        zmq_client._result_socket.setsockopt(zmq.CONFLATE, 1)
        # disable message filter for result socket, subscribe to ALL messages
        zmq_client._result_socket.setsockopt(zmq.SUBSCRIBE, b'')

        # get stale result data if there is any
        event = zmq_client._result_socket.poll(timeout=0.1)
        if zmq.POLLIN == event:        
            zmq_client._result_socket.recv()

        # configure histogram dumping
        histogram_config = zmq_client.get_histogram_config()
        histogram_config.prox = True
        zmq_client.set_histogram_config(histogram_config)
        log("#COM;configured histogram dumping")

        # settings for all configurations
        config = zmq_client.get_configuration()
        config.data.kIters = 4000          # for factory calibration
        config.data.repetitionPeriodMs = 0 # one-shot

        log("#CONF;2.5m mode;all SPADs",True)
        # which SPADs to use (less SPADs are better for high crosstalk peak, but worse for SNR). 
        # 0=all, 1=40best, 2=20best, 3=attenuated        
        config.data.data.spadSelect = 0
        # when 0 measure up to 2.5m. When 1 measure up to 4m. 
        # 4m mode is only activated if the VCSEL clock is configured for 20MHz.   
        # Fall back to 2.5m mode if VCSEL clock is 40 MHz.
        config.data.algo.distanceMode = 0
        config.data.algo.vcselClkDiv2 = 0
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;2.5m mode;40best SPADs",True)
        config.data.data.spadSelect = 1
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;2.5m mode;20best SPADs",True)
        config.data.data.spadSelect = 2
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        # -----------------------------------------------------------

        # switch to 4m mode
        config.data.data.spadSelect = 0
        config.data.algo.distanceMode = 1
        config.data.algo.vcselClkDiv2 = 1

        log("#CONF;4m mode;all SPADs",True)
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;4m mode;40best SPADs",True)
        config.data.data.spadSelect = 1
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;4m mode;20best SPADs",True)
        config.data.data.spadSelect = 2
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

    finally:
        zmq_client.stop_measurement()
        zmq_client.disconnect()
        log("#COM;disconnect from server")
        f.close()
