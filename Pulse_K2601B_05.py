# -*- coding: utf-8 -*-
"""
Created on Wed Jun  5 10:23:43 2024

@author: mwu
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import sys
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt # for python-style plottting, like 'ax1.plot(x,y)'
import pyvisa          # PyVISA module, for GPIB comms
# from Agilent_86142B_river_GPIB_python import *
import time
import os
import re
from time import sleep
import glob
from IOControl import create_dir



addr5 = 'GPIB0::27::INSTR' #K2602B for PD
addr15 = 'GPIB0::26::INSTR' #K2601B_Pulse


rm = pyvisa.ResourceManager()
smu_pd = rm.open_resource(addr5) # K2602B_CHB for PD 
smu = rm.open_resource(addr15) # K2602B_CHB for PD 



# # function initializeTSPLINK()
# smu.write('tsplink.reset()')
# if smu.write('tsplink.reset()') != 2:
#     print("TSPLINK Error: not Found 2nd Node.")
#     sys.exit(0)
# else:
#     print("TSPLINK is sucessfully linked")


#  function configPulserShorter500us(startI,stopI,nPulse,rangeI,rangeV,protectVsrc,protectVsns,biasCurrent,measAperture,nPulse,pulseWidth)
def configPulserShorter500us(startI,stopI,nPulse,rangeI,rangeV,protectVsrc,protectVsns,biasCurrent,measAperture,pulseWidth):

    smu.write('smua.reset()')
    # -- Enable the fast current pulser
    smu.write('smua.pulser.enable = smua.ENABLE')
    
    # -- Set ranges
    smu.write('smua.pulser.rangei = {}'.format(rangeI)) 
    smu.write('smua.pulser.rangev = {}'.format(rangeV)) 
    smu.write('smua.pulser.protect.sourcev = {}'.format(protectVsrc)) 
    smu.write('smua.pulser.protect.sensev = {}'.format(protectVsns)) 
    smu.write('smua.source.leveli = {}'.format(biasCurrent)) 
    smu.write('smua.pulser.measure.aperture = {}'.format(measAperture)) 
    smu.write('smua.measure.count = 1')
    
    # -- Configure Trigger Model to perform a linear staircase current pulse sweep
    smu.write('smua.trigger.count = {}'.format(nPulse))
    smu.write('smua.trigger.source.lineari({}, {}, {})'.format(startI, stopI, nPulse))
    smu.write('smua.trigger.source.action = smua.ENABLE')
    smu.write('smua.trigger.source.pulsewidth = {}'.format(pulseWidth)) 
    smu.write('smua.trigger.source.stimulus = pulsePeriodTimer.EVENT_ID') # Error
    smu.write('smua.trigger.measure.stimulus = tsplink.trigger[1].EVENT_ID')
    smu.write('smua.trigger.measure.action = smua.ASYNC')
    smu.write('smua.trigger.measure.iv(smua.nvbuffer1, smua.nvbuffer2)') # -- I in nvbuffer1
    
    return

# function setupPhotoDiode2602B(biasPD1, measRngPD1, nplcPD1, nPulse, pulsePeriod, remoteSense)
def setupPhotoDiode2602B(biasPD1, measRngPD1, nplcPD1, nPulse, pulsePeriod, remoteSense):

    smu_pd.write('smua.reset()')
    smu_pd.write('smua.source.func = smua.OUTPUT_DCVOLTS')
    
    if remoteSense == True:
        smu_pd.write('smua.sense = smua.SENSE_REMOTE')
    else:
        smu_pd.write('smua.sense = smua.SENSE_LOCAL')
        
    smu_pd.write('smua.source.autorangev = smua.AUTORANGE_OFF')
    smu_pd.write('smua.source.rangev = {}'.format(biasPD1))
    smu_pd.write('smua.source.levelv = {}'.format(biasPD1))
    smu_pd.write('smua.source.limiti = {}'.format(measRngPD1))
    
    # -- Disabling Auto-Ranging and Auto-Zero ensures accurate and consistent timing
    smu_pd.write('smua.measure.autozero = smua.AUTOZERO_OFF')
    smu_pd.write('smua.measure.autorangei = smua.AUTORANGE_OFF')
    smu_pd.write('smua.measure.rangei = {}'.format(measRngPD1))
    smu_pd.write('smua.measure.nplc = {}'.format(nplcPD1))
    smu_pd.write('smua.measure.delay = 0')
    
    # -- Prepare the Reading Buffers
    smu_pd.write('smua.nvbuffer1.clear()')
    smu_pd.write('smua.nvbuffer1.collecttimestamps = 1')
    smu_pd.write('smua.nvbuffer2.clear()')
    smu_pd.write('smua.nvbuffer2.collecttimestamps = 1')
    
    smu_pd.write('trigger.timer[1].reset()')
    smu_pd.write('trigger.timer[1].delay = {} + 100e-3'.format(nPulse * pulsePeriod))
    smu_pd.write('trigger.timer[1].count = 1')
    smu_pd.write('trigger.timer[1].passthrough = false')
    smu_pd.write('trigger.timer[1].stimulus  = trigger.generator[1].EVENT_ID')
    
    # -- Configure the Trigger Model
    smu_pd.write('smua.trigger.source.linearv({}, {}, {})'.format(biasPD1, biasPD1, 1))
    smu_pd.write('smua.trigger.source.action = smua.ENABLE')
    smu_pd.write('smua.trigger.source.limiti = {}'.format(measRngPD1))
    smu_pd.write('smua.trigger.measure.action = smua.ASYNC')
    smu_pd.write('smua.trigger.measure.iv(smua.nvbuffer1, smua.nvbuffer2)')
    smu_pd.write('smua.trigger.endpulse.action	= smua.SOURCE_IDLE')
    smu_pd.write('smua.trigger.endsweep.action	= smua.SOURCE_IDLE')
    smu_pd.write('smua.trigger.count = 1')
    smu_pd.write('smua.trigger.arm.stimulus = 0')
    smu_pd.write('smua.trigger.source.stimulus	= trigger.generator[1].EVENT_ID')
    smu_pd.write('smua.trigger.measure.stimulus = tsplink.trigger[1].EVENT_ID')
    smu_pd.write('smua.trigger.endpulse.stimulus = trigger.timer[1].EVENT_ID')
    
    return

#  function configDcLonger500us(startI,stopI,nPulse,rangeI,rangeV,biasCurrent,measAperture,nPulse,pulseWidth)
def configDcLonger500us(startI,stopI,nPulse,rangeI,rangeV,biasCurrent,measAperture,pulseWidth):
# def configDcLonger500us(startI,stopI,nPulse,rangeI,rangeV,biasCurrent,measAperture,nPulse,pulseWidth):

    rangeV = 6
    linefreq = 60 # in Hz
        # -- Enable the fast current pulser
    smu.write('smua.pulser.enable = smua.DISABLE')
    
    smu.write('smua.source.func = smua.OUTPUT_DCAMPS')
    smu.write('smua.sense = smua.SENSE_REMOTE')
    smu.write('smua.source.autorangei = smua.AUTORANGE_OFF')
    smu.write('smua.source.rangei = {}'.format(rangeI)) 
    smu.write('smua.source.leveli = {}'.format(biasCurrent)) 
    smu.write('smua.source.limitv = 6')
    
    # -- Disabling Auto-Ranging and Auto-Zero ensures accurate and consistent timing
    smu.write('smua.measure.autozero = smua.AUTOZERO_ONCE')
    smu.write('smua.measure.autorangev = smua.AUTORANGE_OFF')
    smu.write('smua.measure.rangev = {}'.format(rangeV))
    smu.write('smua.measure.nplc = {}'.format(measAperture * linefreq)) 
    	
    # -- A timer will be used to control the measure delay so set the built-in delay to 0
    smu_pd.write('smua.measure.delay = 0')
    smu_pd.write('pulseWidthTimer = trigger.timer[4]')
    smu_pd.write('pulseWidthTimer.reset()')
    smu_pd.write('pulseWidthTimer.delay = {}'.format(pulseWidth)) 
    smu_pd.write('pulseWidthTimer.count = 1')
    smu_pd.write('pulseWidthTimer.passthrough = false')
    smu_pd.write('pulseWidthTimer.stimulus = trigger.timer[2].EVENT_ID')
    	
    # 	-- Configure SMU Trigger Model for Sweep
    smu.write('smua.trigger.source.lineari({}, {}, {})'.format(startI, stopI, nPulse))
    smu.write('smua.trigger.source.limitv= {}'.format(rangeV))
    smu.write('smua.trigger.measure.action = smua.ASYNC')
    smu.write('smua.trigger.measure.iv(smua.nvbuffer1, smua.nvbuffer2)')
    smu.write('smua.trigger.endpulse.action = smua.SOURCE_IDLE')
    smu.write('smua.trigger.endsweep.action	= smua.SOURCE_IDLE')
    smu.write('smua.trigger.count = {}'.format(nPulse)) 
    smu.write('smua.trigger.arm.stimulus = 0')
    smu.write('smua.trigger.source.stimulus = pulsePeriodTimer.EVENT_ID')
    smu.write('smua.trigger.measure.stimulus = tsplink.trigger[1].EVENT_ID')
    smu_pd.write('smua.trigger.endpulse.stimulus = pulseWidthTimer.EVENT_ID')
    smu.write('smua.trigger.source.action = smua.ENABLE')
    
    return




# function measurementLIV_CaseII_2601BPULSE_2602B(startI,stopI,nPulse,pulsePeriod,pulseWidth,measAperture,measDelay,rangeV,rangeI,protectVsrc,protectVsns,biasCurrent, biasPD1,measRngPD1,nplcPD1,optoFactor,printData)
def measurementLIV_CaseII_2601BPULSE_2602B(startI,stopI,nPulse,pulsePeriod,pulseWidth,measAperture,measDelay,rangeV,rangeI,protectVsrc,protectVsns,biasCurrent, biasPD1,measRngPD1,nplcPD1,optoFactor):

    
#     Prerequisites:  None
    
# 	Pass Parameters:
# 	    * startI        : Current level of the first pulse in amps
# 	    * stopI         : Current level of the last pulse in amps
# 	    * nPulse        : Number of pulses in the sweep 
# 	    * pulsePeriod   : Time between start of consecutive pulses in seconds
# 	    * pulseWidth    : Width of current pulses in seconds
# 	    * measAperture  : Effective integration time in seconds
# 	    * measDelay     : Time from pulse start to measure start in seconds
# 	    * rangeV        : Voltage measure range in volts
# 	    * rangeI        : Current source and measure range in amps
# 	    * protectVsrc   : Protection Voltage on Source side
# 	    * protectVsns   : Protection Voltage on Sense side
# 	    * biasCurrent   : Idle current level in amps (base level for pulses)
# 		* biasPD1 		: Bias voltage for PD with 2602B 
# 		* measRngPD1	: Measure Range for PD 
# 		* nplcPD1		: NPLC for PD measurement  
# 	    * optoFactor    : Proportaional Constant to calculate optical power based on the PD current 

#      Returned values:  None

    ####Guess node[1] for smu, node[2] for smu_pd
    	# -- Reset the pulser to default conditions
    smu.write('smua.reset()')
    # -- Configure the reading buffers
    smu.write('smua.nvbuffer1.clear()')
    smu.write('smua.nvbuffer2.clear()')
    smu.write('smua.nvbuffer1.collecttimestamps= 1')
    smu.write('smua.nvbuffer2.collecttimestamps= 1')
    
    # -- Use Trigger Timer 1 to control pulse period
    smu.write('pulsePeriodTimer = trigger.timer[1]')
    smu.write('pulsePeriodTimer.reset()')
    smu.write('pulsePeriodTimer.delay = {}'.format(pulsePeriod)) 
    smu.write('pulsePeriodTimer.count = {}'.format(nPulse)) 
    smu.write('pulsePeriodTimer.passthrough = true')
    smu.write('pulsePeriodTimer.stimulus = smua.trigger.ARMED_EVENT_ID')
    
    # -- Use Trigger Timer 2 to control measurement synchronization
    smu_pd.write('measSyncTimer = trigger.timer[2]')
    smu_pd.write('measSyncTimer.reset()')
    smu_pd.write('measSyncTimer.delay = {}'.format(measDelay))  
    smu_pd.write('measSyncTimer.count = 1')
    smu_pd.write('measSyncTimer.passthrough = false')
    smu_pd.write('measSyncTimer.stimulus = pulsePeriodTimer.EVENT_ID') # 	measSyncTimer.stimulus = pulsePeriodTimer.EVENT_ID

    
    smu.write('tsplink.trigger[1].clear()')
    smu.write('tsplink.trigger[1].mode = tsplink.TRIG_FALLING')
    smu.write('tsplink.trigger[1].pulsewidth = 3e-6')
    smu_pd.write('tsplink.trigger[1].clear()')
    smu_pd.write('tsplink.trigger[1].mode = tsplink.TRIG_FALLING')
    smu_pd.write('tsplink.trigger[1].pulsewidth = 3e-6')
    smu.write('tsplink.trigger[1].stimulus = measSyncTimer.EVENT_ID') #     node[1].tsplink.trigger[1].stimulus = measSyncTimer.EVENT_ID 


    if pulseWidth > 500e-6:
        if measAperture < 20e-6:
            measAperture = 20e-6
        elif measDelay < 100e-6:
            measDelay  = 100e-6
        configDcLonger500us(startI,stopI,nPulse,rangeI,rangeV,biasCurrent,measAperture,pulseWidth)
    else:
        configPulserShorter500us(startI,stopI,nPulse,rangeI,rangeV,protectVsrc,protectVsns,biasCurrent,measAperture,pulseWidth)	
    
        
        
    setupPhotoDiode2602B(biasPD1, measRngPD1, nplcPD1, nPulse, pulsePeriod, False)
    	
    # -- Turn on the output
    smu.write('smua.source.output = smua.OUTPUT_ON')
    smu.write('smua.source.output = smua.OUTPUT_ON')
    	
    # 	-- Initiate the Trigger Model and wait for the sweep to complete
    smu.write('smua.trigger.initiate()')
    smu.write('trigger.generator[1].assert()')
    smu.write('smua.trigger.initiate()')
    smu.write('waitcomplete()')
    	
    # -- Turn off the output and disable the current pulser
    smu.write('smua.source.output = smua.OUTPUT_OFF')
    smu.write('smua.source.output = smua.OUTPUT_OFF')
    smu.write('smua.pulser.enable = smua.DISABLE')
        
    # # -- Output the data in tab-separated format
    # if printData > 0:
    #     print("\nTime (s)\t Current(A)\t Voltage(V)\t PD1_I(A)\t PD1_P(W)")
    #     for i = 1, smua.nvbuffer1.n do:
    #         print( smua.nvbuffer1.timestamps[i],smua.nvbuffer1[i],smua.nvbuffer2[i],node[2].smua.nvbuffer1[i],math.abs(node[2].smua.nvbuffer1[i]*optoFactor))
    
    
    return


# function measurementLIV()
startI        = 0
stopI         = 0.1
nPulse        = 100
pulsePeriod  = 5e-3
pulseWidth   = 50e-6
measAperture = 20e-6	
measDelay    = 10e-6
rangeV        = 10
rangeI        = 1
protectVsrc	= 10
protectVsns	= 10
biasCurrent   = 0.1e-3

biasPD1 		= 0
measRngPD1	= 0.001
nplcPD1		= 0.001 #-- minimum nplc 0.001 = 0.001 x 16.67ms = 17us  
optoFactor	= 72000





# configPulserShorter500us(startI,stopI,nPulse,rangeI,rangeV,protectVsrc,protectVsns,biasCurrent,measAperture,pulseWidth)

# setupPhotoDiode2602B(biasPD1, measRngPD1, nplcPD1, nPulse, pulsePeriod, False)

measurementLIV_CaseII_2601BPULSE_2602B(startI,stopI,nPulse,pulsePeriod,pulseWidth,measAperture,measDelay,rangeV,rangeI,protectVsrc,protectVsns,biasCurrent, biasPD1,measRngPD1,nplcPD1,optoFactor)

