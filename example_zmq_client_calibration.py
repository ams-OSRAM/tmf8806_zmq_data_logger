# /*****************************************************************************
# * Copyright (c) [2024] ams-OSRAM AG                                          *
# * All rights are reserved.                                                   *
# *                                                                            *
# * FOR FULL LICENSE TEXT SEE LICENSE.TXT                                      *
# ******************************************************************************/
 

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
from zmq_client.tmf8x0x_zeromq_common import MeasureCommand
from zmq_client.tmf8806_regs import tmf8806MeasureCmd
from pathlib import Path

if __name__ == "__main__":

    # change IP address to 127.0.0.1 if you want to use the TMF8806 shield board
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

        log("#COM;stop measurements")
        zmq_client.stop_measurement()
        
        cal = zmq_client.get_calibration(measurement_config)
        calstr = "#CAL"
        for b in list(bytes(cal)):
            calstr += f";{b:02X}"
        log(calstr,to_console_too=True)

        log("#COM;start measurements")
        measurement_config.data.command = MeasureCommand.MEASURE
        zmq_client.start_measurement(measurement_config)

        # get a single measurement (one-shot mode)
        rc = zmq_client.get_data()
        if rc is not None:
            log(f"#XTALK;{rc.result.xtalk}",True)
            for hist in range(0,len(rc.histogramsProx)):
                log(f"#HSHORT{hist};{';'.join(map(str,rc.histogramsProx[hist]))}")

        log("#COM;stop measurements")
        zmq_client.stop_measurement()

    zmq_client = ZeroMqClient()
    zmq_client.connect(cmd_addr=CMD_SERVER_ADDR,result_addr=RESULT_SERVER_ADDR)

    # log header 
    log("sep=;")
    log("#COM;comment string")
    log("#CAL;calibration data")
    log("#XTALK;cross-talk value")
    log("#HSHORT0;short range histogram bin values (TDC0)")
    log("#HSHORT1;short range histogram bin values (TDC1)")
    log("#HSHORT2;short range histogram bin values (TDC2)")
    log("#HSHORT3;short range histogram bin values (TDC3)")
    log("#HSHORT4;short range histogram bin values (TDC4)")

    try:
        # as a precaution false another measurement is running
        zmq_client.stop_measurement()

        # get stale result data if there is any
        if zmq.POLLIN == zmq_client._result_socket.poll(timeout=0.1):        
            zmq_client.get_data()

        # configure histogram dumping
        histogram_config = zmq_client.get_histogram_config()
        histogram_config.prox = True
        zmq_client.set_histogram_config(histogram_config)
        log("#COM;configured histogram dumping")

        # settings for all configurations
        config = zmq_client.get_configuration()
        config.data.kIters = 4000          # for factory calibration
        config.data.repetitionPeriodMs = 0 # one-shot

        log("#CONF;2.5m mode;default mode",True)
        # which SPADs to use (less SPADs are better for high crosstalk peak, but worse for SNR). 
        # 0=all, 1=40best, 2=20best, 3=attenuated        
        config.data.data.spadSelect = 0
        # when 0 measure up to 2.5m. When 1 measure up to 5m. 
        # 5m mode is only activated if the VCSEL clock is configured for 20MHz.   
        # Fall back to 2.5m mode if VCSEL clock is 40 MHz.
        config.data.algo.distanceMode = 0
        config.data.algo.vcselClkDiv2 = 0
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;2.5m mode;large airgap mode",True)
        config.data.data.spadSelect = 1
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;2.5m mode;thick cover glass mode",True)
        config.data.data.spadSelect = 2
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        # -----------------------------------------------------------

        # switch to 5m mode
        config.data.data.spadSelect = 0
        config.data.algo.distanceMode = 1
        config.data.algo.vcselClkDiv2 = 1

        log("#CONF;5m mode;default mode",True)
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;5m mode;large airgap mode",True)
        config.data.data.spadSelect = 1
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

        log("#CONF;5m mode;thick cover glass mode",True)
        config.data.data.spadSelect = 2
        execute_single_factory_calibration(zmq_client=zmq_client,measurement_config=config)

    finally:
        zmq_client.stop_measurement()
        zmq_client.disconnect()
        log("#COM;disconnect from server")
        f.close()
