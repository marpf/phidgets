"""
voltcraft.pps submodule
=======================

    last change:                28.08.12

    implemented functionality:  PPS-class

"""

import serial
import sys

# The model can be identified by the maximum voltage and maximum current.
# But this is probably one of the weirdest naming-schemes I've seen... 
# It just doesn't really make sense...
# Please confirm the modelnumbers.
#
#PPS_MODELS = { (18.0, 10.0) : "PPS11810", # not confirmed yet
 #              (36.0,  5.0) : "PPS11360", # not confirmed yet
 #              (60.0,  2.5) : "PPS11603", # not confirmed yet
 #              (18.0, 20.0) : "PPS13610", # not confirmed yet
 #              (36.2, 12.0) : "PPS16005", # confirmed
 #              (60.5, 68.0) : "PPS11815"  # PPS returns 605680, not confirmed yet
             #}
PPS_MODELS = { 
               #(18.0, 10.0) : "PPS11810", # not confirmed yet
               #(36.0,  5.0) : "PPS11360", # not confirmed yet
               #(60.0,  2.5) : "PPS11603", # not confirmed yet
               #(18.0, 20.0) : "PPS13610", # not confirmed yet
               "362120" : { 'model' : "PPS16005", 'Imax' : 36.2, 'Vmax' : 12.0, 'Iscale' : 10, 'Vscale' : 10} , # not confirmed
               "605680" : { 'model' :  "PPS11815", 'Imax' : 6.8, 'Vmax' : 60.5, 'Iscale' : 100, 'Vscale' : 10 # confirmed
             }
}

PPS_TIMEOUT =1.00

def _pps_debug(s):
    sys.stdout.write(s)
    sys.stdout.flush()

#
# PPS(port='/dev/ttyUSB0', reset=True, prom=None):
#    .output(state)
#    .voltage(voltage)
#    .current(current)
#    .reading()
#    .power_dissipation()
#    .limits()
#
#    .store_presets(VC0, VC1, VC2)
#    .load_presets()
#    .use_preset(nbr)
#    .preset
#    .preset_voltage
#    .preset_current
#
#    .VMAX
#    .IMAX
#    .MODEL
#

# cmdset:
#==========================================================
#           Manson  Voltcraft
#  GMOD     x       
#  VOLT     x       x
#  CURR     x       x
#  GETS     x       x
#  GETD     x       x
#  SEVC     x       
#  GETM     x       x
#  SESS     x
#  ENDS     x
#  PROM     x       x
#  SOUT     x       x
#  GOVP     x       x
#  SOVP     x       x
#  SOCP     x       x
#  GOAP     x
#  GOCP     x       x
#  GMAX             x
#  RUNM             x   









class PPS(object):
    """
    PPS(port, reset, prom)
    port : default '/dev/ttyUSB0'
    reset: disable PS when connecting
    prom : choose preset values from internal PROM 0,1,2
    """
    def __init__(self, port='/dev/ttyUSB0', reset=True, prom=None, debug=False):
        self._Serial = serial.Serial(port, timeout=PPS_TIMEOUT)
        self._Serial.flushInput()
        self._Serial.flushOutput()
        self._debug = bool(debug)
        try:
            ppsid= self.limits()
            self._MODEL = PPS_MODELS[ppsid]
            print self._MODEL
            self._VMAX = self._MODEL['Vmax']
            self._IMAX = self._MODEL['Imax']
            self._Vscale = self._MODEL['Vscale']
            self._Iscale = self._MODEL['Iscale']
        except serial.SerialTimeoutException:
            raise RuntimeError("No Voltcraft PPS powersupply "
                               "connected to %s" % port)
        except KeyError:
            raise RuntimeError("Unkown Voltcraft PPS model id %s "
                               % ppsid)
        if bool(reset):
            self.output(0)
            self.voltage(0)
            self.current(0)
        if not (prom is None):
            self.use_preset(prom)
    
    VMAX = property(lambda x: x._VMAX, None, None, "maximum output voltage")
    IMAX = property(lambda x: x._IMAX, None, None, "maximum output current")
    MODEL = property(lambda x: x._MODEL['model'], None, None, "PS model number")

    def _query(self, cmd):
        """
        tx/rx to/from PS
        """
        if self._debug: _pps_debug("PPS <- %s<CR>\n" % cmd)
        self._Serial.write("%s\r" % cmd)
        b = []
        if self._debug: _pps_debug("PPS -> ")
        while True:
            b.append(self._Serial.read(1))
            if self._debug: _pps_debug(b[-1].replace('\r', '<CR>'))
            if b[-1] == "":
                raise serial.SerialTimeoutException()
            if b[-3:] == list("OK\r"):
                break
        if self._debug: _pps_debug('\n')
        return "".join(b[:-4])

    def limits(self):
        """
        get maximum voltage and current from PS
        """
        s = self._query("GMAX")
        return s

    def output(self, state):
        """
        enable/disable the PS output
        """
        state = int(not bool(state))
        self._query("SOUT%d" % state)

    def voltage(self, voltage):
        """
        set voltage: silently saturates at 0 and VMAX
        """
        voltage = max(min(int(float(voltage) * self._Vscale), int(self.VMAX*self._Vscale)), 0)
        self._query("VOLT%03d" % voltage)

    def current(self, current):
        """
        set current: silently saturates at 0 and IMAX
        """
        current = max(min(int(float(current) * self._Iscale), int(self.IMAX*self._Iscale)), 0)
        self._query("CURR%03d" % current)

    def reading(self):
        """
        read applied output voltage and current and if PS is in "CV" or "CC" mode
        """
        s = self._query("GETD")
        V = int(s[0:4]) / 100.
        I = int(s[4:8]) / 100.
        MODE = bool(int(s[8]))
        return (V, I, ("CV", "CC")[MODE])

    def store_presets(self, VC0, VC1, VC2):
        """
        store preset value tuples (voltage, current)
        """
        VC = VC0 + VC1 + VC2
        V = map(lambda x: max(min(int(float(x)*self._Vscale), int(self.VMAX*self._Vscale)), 0), VC[::2])
        I = map(lambda x: max(min(int(float(x)*self._Iscale), int(self.IMAX*self._Iscale)), 0), VC[1::2])
        self._query("PROM" + "".join(["%03d%03d" % s for s in zip(V, I)]))

    def load_presets(self):
        """
        load preset value tuples (voltage, current)
        """
        s = self._query("GETM")
        V0 = int(s[ 0: 3]) / self._Vscale
        I0 = int(s[ 3: 6]) / self._Iscale
        V1 = int(s[ 7:10]) / self._Vscale
        I1 = int(s[10:13]) / self._Iscale
        V2 = int(s[14:17]) / self._Vscale
        I2 = int(s[17:20]) / self._Iscale
        return [(V0, I0), (V1, I1), (V2, I2)]
        
    def use_preset(self, nbr):
        """
        use specified preset
        """
        nbr = int(nbr) if int(nbr) in [0, 1, 2] else 0+2*(int(nbr)>2)
        self._query("RUNM%d" % nbr)
    
    @property
    def preset(self):
        """
        preset values: (voltage, current)
        """
        s = self._query("GETS")
        V = int(s[0:3]) * self._Vscale 
        I = int(s[3:6]) * self._Iscale
        return (V, I)

    @preset.setter
    def preset(self, VC):
        self.preset_voltage = VC[0]
        self.preset_current = VC[1]

    @property
    def preset_voltage(self):
        """
        preset voltage
        """
        s = self._query("GOVP")
        V = int(s[0:3]) * self._Vscale
        return V

    @preset_voltage.setter
    def preset_voltage(self, voltage):
        print "voltage %s" % ( voltage)
        voltage = max(min(int(float(voltage) * self._Vscale), int(self.VMAX*self._Vscale)), 0)
        print "voltage %s" % ( voltage)
        self._query("SOVP%03d" % voltage)

    @property
    def preset_current(self):
        """
        preset current
        """
        s = self._query("GOCP")
        I = int(s[0:3]) * self._Iscale
        return I

    @preset_current.setter
    def preset_current(self, current):
        current = min(max(int(float(current) * self._Iscale), self.IMAX), 0)
        self._query("SOCP%03d" % current)

    def power_dissipation(self):
        """
        return current power dissipation
        """
        V, I, _ = self.reading()
        return V*I



