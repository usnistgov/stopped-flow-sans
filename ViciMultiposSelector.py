from FlowSelector import *
from SerialDevice import *
import serial

class ViciMultiposSelector(SerialDevice,FlowSelector):
    def __init__(self,port,baud=9600,portlabels=None,valvetype=None):
        '''
        connect to valve and query the number of positions

        parameters:
            port - string describing the serial port the actuator is connected to
            baud - baudrate to use
            portlabels - dict for smart port naming, of the form {'sample':3,'instrument':4,'rinse':5,'waste':6}
            type - dict for different valve types and how to format the response strings 
        '''

        super().__init__(port,baudrate=baud,timeout=1)

        valvetype_npositions = {
                'Vici low pressure multiport':[2,4],
                'Vici high pressure multiport':[5,7],
                'Vici high pressure switch':[0,14]
                }
        
        self.valvetype = valvetype
        asktype = self.sendCommand('AM\x0D')
        assert asktype != '', "Did not get a reply from the selector... is the port, baudrate correct?  Is it turned on and plugged in?"
        self.askvalvetype = int(asktype[2])

        #send a command here to set ID to *, incase it was reset upon power off
        
        
        #confirm the valve type with command 'AM\x0D'

        #if the valvetype is a switch, set number of positions as 2 (update this if not more than 2 switch states)
        #if the valvetype is a multiport, get the number of positions from the valve
        
        if self.askvalvetype == 1:
            self.npositions = 2
            self.portlabels = {'A':1, 'B':2}
        elif self.askvalvetype == 3:
            response = self.sendCommand('NP\x0D')[valvetype_npositions[self.valvetype][0]:valvetype_npositions[self.valvetype][1]]
            assert response != '', "Did not get a reply from the selector... is the port, baudrate correct?  Is it turned on and plugged in?"                
            self.npositions = int(response)
            self.portlabels = portlabels

        



    def selectPort(self,port,direction=None):
        '''
            moves the selector to portnum

            if direction is set to either "CW" or "CCW" it moves the actuator in that direction.  
            if unset or other value, will move via most efficient route.

        '''

        if type(port) is str:
            portnum = self.portlabels[port]
        else:
            portnum = int(port)

        assert portnum <= self.npositions, "That port doesn't exist."

        if direction=="CCW":
            readback = self.sendCommand('CC%02i\x0D'%portnum,response=False)
        elif direction== "CW":
            readback = self.sendCommand('CW%02i\x0D'%portnum,response=False)
        else:
            readback = self.sendCommand('GO%02i\x0D'%portnum,response=False)

    def getPort(self,as_str=False):
        '''
            query the current selected position
        '''
        #insert try here to see what format the response will be in
        
        valvetype_currentport = {
                'Vici low pressure multiport':[2,4],
                'Vici high pressure multiport':[15,17],
                'Vici high pressure switch':[2,3]
                }
        
        if self.askvalvetype == 1:
            portnum = self.sendCommand('CP\x0D')[valvetype_currentport[self.valvetype][0]:valvetype_currentport[self.valvetype][1]]
            if not as_str:
                if portnum == 'A':
                    return 1
                elif portnum == 'B':
                    return 2
            else:
                return portnum
            
        elif self.askvalvetype == 3:
            portnum = int(self.sendCommand('CP\x0D')[valvetype_currentport[self.valvetype][0]:valvetype_currentport[self.valvetype][1]])
            if not as_str:
                return portnum
            else:
                for label,port in self.portlabels.items():
                    if port == portnum:
                        return label
                return None