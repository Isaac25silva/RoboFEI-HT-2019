# coding: utf-8

# ****************************************************************************
# * @file: Orchestrator.py
# * @project: ROBOFEI-HT - FEI 😛
# * @author: Vinicius Nicassio Ferreira
# * @version: V0.0.1
# * @created: 23/10/2017
# * @e-mail: vinicius.nicassio@gmail.com
# * @brief: Class Orchestrator
# ****************************************************************************

# ---- Imports ----

# The standard libraries used in the vision system.

# The standard libraries used in the visual memory system.

# Used class developed by RoboFEI-HT.
from BasicProcesses import * # Standard and abstract class.
from CameraCapture import * # Class responsible for performing the observation of domain.

## Class Orchestrator
# Class responsible for managing the vision process.
class Orchestrator(BasicProcesses):
    
    # ---- Variables ----
    
    ## camera
    # Object responsible for reading the camera.
    camera = None
    
    ## Constructor Class
    def __init__(self, a):
        super(Orchestrator, self).__init__(a, "Vision", "Parameters")
        
        # Instantiating camera object
        try:
            self.camera = CameraCapture(a)
        except VisionException as e:
            sys.exit(1)
        
    ## run
    # .
    def run(self):
        while True:
            try:
                time.sleep(1)
            except VisionException as e:
                break
            except KeyboardInterrupt:
                os.system("clear")
                print "\33[1;31mDetect KeyboardInterrupt\33[0m\n"
                break
    
    ## end
    # .
    def end(self):
        self.camera.finalize()
        #self._end( )