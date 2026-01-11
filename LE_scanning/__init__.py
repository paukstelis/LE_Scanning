# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
#import octoprint.filemanager
#import octoprint.filemanager.util
import octoprint.util
from octoprint.filemanager import FileManager
from octoprint.filemanager.storage import LocalFileStorage
import re
import time
import logging
from . import STLGenerator as STLGenerator

class ScanningPlugin(octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.TemplatePlugin
):

    def __init__(self):
        self.probing = False
        self.probed = False
        self.probe_on = False
        self.scan_type = None
        self.direction = 0
        self.increment = 0
        self.pull_off = 0
        self.ref_diam = 0
        self.length = 0
        self.continuous = False
        self.stl = False
        self.name = None
        self.probe_data = []
        self.reference = None
        self.scanfile = None
        self.stlfile = None
        self.output_path = None
        self.loop = None
        self._identifier = "scanning"
        self.stop_flag = False
        self.dooval = 0
        self.forced_probes = []

        self.current_x = None
        self.current_z = None
        self.current_a = None
        self.current_b = None

        self.commands = []

    def initialize(self):
        self.datafolder = self.get_plugin_data_folder()
        self._event_bus.subscribe("LATHEENGRAVER_SEND_POSITION", self.get_position)
        path = self._settings.getBaseFolder("uploads")
        self._logger.info(f"Path is {path}")
        storage = self._file_manager._storage("local")
        if storage.folder_exists("scans"):
            self._logger.info("Scans exists")
        else:
            storage.add_folder("scans")

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    def on_event(self, event, payload):
        if event == "plugin_latheengraver_send_position":
            self.get_position(event, payload)

    def get_position(self, event, payload):
        #self._logger.info(payload)
        self.current_x = payload["x"]
        self.current_z = payload["z"]
        self.current_a = payload["a"]
        self.current_b = payload["b"]

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/scanning.js", "js/plotly-latest.min.js"],
            "css": ["css/scanning.css"],
            "less": ["less/scanning.less"]
        }

   
    def generate_scan(self):
        #set all data to begin scan
        if not self.name:    
            self.scanfile = self.scan_type + "_" + time.strftime("%Y%m%d-%H%M") + "_scan.txt"
            self.stlfile = self.scan_type + "_" + time.strftime("%Y%m%d-%H%M") + "_scan.stl"
        else:
            self.scanfile = self.scan_type + "_" + self.name + "_scan.txt"
            self.stlfile = self.scan_type + "_" + self.name + "_scan.stl"
        self.probe_data = []
        self.reference = None
        storage = self._file_manager._storage("local")
        if storage.folder_exists("scans"):
            self._logger.info("Scans exists")
        else:
            storage.add_folder("scans")
        path = self._settings.getBaseFolder("uploads")
        self.output_path = f"{path}/scans/{self.scanfile}"

    def finish_scan(self):
        self.probing = False
        with open(self.output_path,"w") as newfile:
            newfile.write(f";{self.scan_type}\n")
            newfile.write(f";D={self.ref_diam}\n")
            for line in self.probe_data:
                if line == "NEXTSEGMENT":
                    newfile.write("NEXTSEGMENT\n")
                else:
                    newfile.write(f"{line[0]:.3f},{line[1]:.3f},{line[2]:.3f}\n")
        if self.stl:
            path = self._settings.getBaseFolder("uploads")
            tosavepath =  f"{path}/scans/{self.stlfile}"
            # Only use points up to the first NEXTSEGMENT
            if "NEXTSEGMENT" in self.probe_data:
                first_segment = []
                for point in self.probe_data:
                    if point == "NEXTSEGMENT":
                        break
                    first_segment.append(point)
            else:
                first_segment = self.probe_data
            stlgen = STLGenerator.STLGenerator(first_segment, self.ref_diam)
            stlgen.generate_mesh()
            stlgen.save_stl(tosavepath)
        
        self.probe_data = []

    def start_scan(self):
        self.probing = True
        self.reference = None

        #handle direction here
        dir = ""
        retract_dir = ""
        move_dir = "" #the movement direction between probes, should be nothing for X positive,
        self.commands = []
        #Make sure in G94 mode
        self.commands.append("G94")
        #Set A to zero as the first command
        self.commands.append("G92 A0")
        self.commands.append("G92 X0 Z0")
        #TODO Z scan Retract direction depends on front or back side scan and this is not yet taken into account
        if self.scan_type == "X":
            scan_dir = "Z"
            if self.direction:
                dir = "-"
            dir = '-'
            if self.direction:
                move_dir = "-"
                
        if self.scan_type == "Z":
            scan_dir = "X"
            dir = "-"
            if not self.direction:
                dir=""
                retract_dir = "-"
            dir = "-"
            if not self.direction:
                dir=""
                retract_dir = "-"
            if self.direction:
                move_dir = "-"
                
        i = 0
        probes = round(self.length/self.increment)
        move_increment = self.length/probes
        probe_commands = []  #main list
        single_probe_commands = []  #Each X/Z scan

        while i <= probes:
            single_probe_commands.extend([f"G91 G21 G38.3 {scan_dir}{dir}100 F150",f"G91 G21 G0 {scan_dir}{retract_dir}{self.pull_off} F500"])
            #don't want to advanced again if we have made last probe
            if i != probes:
                single_probe_commands.extend([f"G91 G21 G0 {self.scan_type}{move_dir}{move_increment:0.3f} F500"])                                 
            i+=1

        if self.dooval:
            arot = 360 / self.dooval
            # Collect all segment angles
            probe_angles = [i * arot for i in range(int(self.dooval))]
            # Add forced probe angles
            probe_angles.extend(self.forced_probes)
            # Sort and deduplicate
            probe_angles = sorted(set(probe_angles))
            self._logger.info(f"Probe angles: {probe_angles}")
            #Rotate A
            for idx, angle in enumerate(probe_angles):
                probe_commands.append(f"G90 G0 A{angle:.2f}")  # Move to absolute angle
                probe_commands.extend(single_probe_commands)   # Probe at this angle
                probe_commands.append("NEXTSEGMENT")
             
        else:
            probe_commands = single_probe_commands

        self.commands.extend(probe_commands)                            
        self.commands.append("SCANDONE")
        self.commands.append("G0 A0")
        self._logger.info(self.commands)
        self.send_next_probe()
        #prompt to begin running commands somehow?
        #self._printer.commands(commands)

        #write to scan file here?

    def send_next_probe(self):
        sent_probe = False
        if self.probing:
            while not sent_probe and len(self.commands) > 0:
                if "G38.3" in self.commands[0]:
                    sent_probe = True
                    self._printer.commands(self.commands[0])
                    self.commands.pop(0)
                    break
                if "NEXTSEGMENT" in self.commands[0]:
                    self.probe_data.append("NEXTSEGMENT")

                    time.sleep(0.5)
                    #Reset position HERE
                    #Move back to first probe position, need to be careful here!
                    #this still doesn't handle front/back side scans for Z
                    reset_commands = []
                    if self.scan_type == "Z":
                        if self.current_x < 0:
                            #less than 0 point, so retract back
                            reset_commands.append(f"G90 G0 X0")
                            reset_commands.append(f"G90 G0 Z0")
                        else:
                            reset_commands.append(f"G90 G0 Z0")
                    if self.scan_type == "X":
                        reset_commands.append(f"G90 G0 Z0")
                        reset_commands.append(f"G90 G0 X0")
                    self.commands[1:1] = reset_commands

                self._printer.commands(self.commands[0])
                try:
                    self.commands.pop(0)
                except:
                    #may have to put scan done stuff inhere?
                    self._logger.info("Command list complete")

    def cancel_probe(self):
        self.probing = False
        #soft reset
        self.commands = []
        self._printer.commands(["M999"])
        self.probe_data = []

    def get_api_commands(self):
        return dict(
            start_scan=[],
            stop_scan=[]
        )
    
    def is_api_protected(self):
        return True
    
    def on_api_command(self, command, data):
        
        if command == "start_scan":
            #self._logger.info(data)
            self.forced_probes = []
            self.probe_data = []
            self.scan_type = str(data["scan_type"])
            self.ref_diam = float(data["ref_diam"])
            self.pull_off = float(data["pull_off"])
            self.continuous = bool(data["continuous"])
            self.direction = int(data["scan_direction"])
            self.length = float(data["scan_length"])
            self.increment = float(data["scan_increment"])
            self.stl = bool(data["stl"])
            self.name = str(data["name"])
            self.dooval = int(data["dooval"])
            self.forced_probes = [float(val) for val in data.get("forced_probes", [])]
            if self.name == "None":
                self.name = None

            self.generate_scan()
            if not self._printer.is_operational() or self._printer.is_printing():
                self._logger.info("Cannot do probing")
                return
            if self.length < 10:
                self._plugin_manager.send_plugin_dmessage("latheengraver", dict(type="simple_notify",
                                                                    title="Length error",
                                                                    text="Scan lengths must be greater than 10mm",
                                                                    hide=True,
                                                                    delay=10000,
                                                                    notify_type="error"))
                return
            
            self.probing = True

            self.start_scan()

        if command == "stop_scan":
            if self.probing:
                self._logger.info("Stopping scan")
                self.cancel_probe()
            else:
                self._logger.info("Not probing, nothing to stop")

    def hook_gcode_received(self, comm_instance, line, *args, **kwargs):
        if 'PRB' in line:
            self.parse_probe(line)
        return line
    
    def hook_gcode_sending(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if cmd.upper() == 'SCANDONE':
            self.probing = False
            self.finish_scan()
            return (None, )
        if cmd.upper() == 'NEXTSEGMENT':
            self._logger.info("Next segment received")
            self.probe_data.append("NEXTSEGMENT")
            return (None, )

    def update_probe_data(self):
        data = dict(type="graph", probe=self.probe_data)
        self._plugin_manager.send_plugin_message('scanning',data)

    def process_pin_state(self, msg):
        pattern = r"Pn:[^P]*P"
        return bool(re.search(pattern, msg))
    
    def parse_probe(self, line):
        #[PRB:-1.000,0.000,-10.705,0.000,0.000:1]
        #0 = X, 1 = Z, 2 = A
        match = re.search(r".*:([-]*\d*\.*\d*),\d\.000,([-]*\d*\.*\d*),([-]*\d*\.*\d*).*", line)
        self._logger.info("Parse probe data")
        self._logger.info(line)
        x = float(f"{match.groups(1)[0]}")
        z = float(f"{match.groups(1)[1]}")
        a = float(f"{match.groups(1)[2]}")
        if not self.reference:
            self.reference = (x,z,a)
            self.probe_data.append((0,0,0))
        else:
            self.probe_data.append((x-self.reference[0],z-self.reference[1],a-self.reference[2]))
            self._logger.debug(self.probe_data)
        self.update_probe_data()
        self.send_next_probe()

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "scanning": {
                "displayName": "Scanning Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "paukstelis",
                "repo": "LE_Scanning",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/paukstelis/LE_Scanning/archive/{target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Scanning"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = ScanningPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.hook_gcode_received,
        "octoprint.comm.protocol.gcode.sending": __plugin_implementation__.hook_gcode_sending,
    }
