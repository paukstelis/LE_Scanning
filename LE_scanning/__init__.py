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
#import os
#import math
import asyncio
import logging
from . import STLGenerator as STLGenerator

class ScanningPlugin(octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
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

    def initialize(self):
        self.datafolder = self.get_plugin_data_folder()
        path = self._settings.getBaseFolder("uploads")
        self._logger.info(f"Path is {path}")
        self.loop = asyncio.get_event_loop()

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/scanning.js", "js/plotly-latest.min.js"],
            "css": ["css/scanning.css"],
            "less": ["less/scanning.less"]
        }

    def get_api_commands(self):
        return dict(
            write_gcode=[],
            editmeta=[]
        )
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
            stlgen = STLGenerator.STLGenerator(self.probe_data, self.ref_diam)
            stlgen.generate_mesh()
            stlgen.save_stl(tosavepath)

    def start_scan(self):
        self.probing = True
        self.reference = None
        #handle direction here
        dir = ""
        retract_dir = ""
        #handle directions here
        #self.direction == 0 is positive, 1 is negative
        dir = "" #this is equivalent to PROBE direction
        retract_dir = "" #only necessary for Z
        move_dir = "" #the movement direction between probes, should be nothing for X positive,
        commands = []
        #Set A to zero as the first command
        commands.append("G92 A0")
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
                
        if self.scan_type == "A":
            i = 0
            probes = round(360/self.increment)
            while i <= probes:
                commands.extend(["G91 G21 G38.2 Z-50 F200", f"G91 G21 G1 Z{self.pull_off} A{dir}{self.increment} F500"])
                i+=1
        else:
            i = 0
            probes = round(self.length/self.increment)
            probe_commands = []
            while i <= probes:
                probe_commands.extend([f"G91 G21 F150 G38.3 {scan_dir}{dir}100 ",
                                 f"G91 G21 G1 {scan_dir}{retract_dir}{self.pull_off} F500",
                                 f"G91 G21 G1 {self.scan_type}{move_dir}{self.increment} F500"])                                 
                i+=1
            if self.dooval:
                probe_commands.append("NEXTSEGMENT")
                arot = 360 / self.dooval
                #Move back to first probe position
                if self.scan_type == "X":
                    moveto = self.reference
                elif self.scan_type == "Z":
                    moveto = (self.reference[1], self.reference[0])
                #this still doesn't handle front/back side scans for Z
                probe_commands.append[f"G90 G0 {scan_dir}{moveto[1]+10}"]
                probe_commands.append[f"G90 G0 {move_dir[0]}"]
                #Rotate A
                probe_commands.append(f"G91 G21 G0 A{arot}")
                probe_commands = probe_commands * self.dooval

        commands.extend(probe_commands)                            
        commands.append("SCANDONE")

        #prompt to begin running commands somehow?
        self._printer.commands(commands)
        #write to scan file here?

    def start_continuous_scan(self):
        dir = ""
        if self.direction:
            dir = "-"
        if self.scan_type == "X":
            scan_dir = "Z"
            self.cont_task = self.loop.create_task(self.do_continuous(scan_dir, dir))
        if self.scan_type == "Z":
            scan_dir = "X"
            self.cont_task = self.loop.create_task(self.do_continuous(scan_dir, dir))
        if self.scan_type == "A":
            self.cont_task = asyncio.create_task(self.do_continuous_a())

    async def do_continous_a(self):
        i = 360.0
        #intial probe
        self.probed = False
        self._printer.commands(["G91 G21 G38.2 Z-100 F200","?"])
        #probe loop
        while self.probing:            
            if self.probe_on:
                self._printer.commands(["G91 G21 G38.5 Z10 F200","?"])
            if self.probed and not self.probe_on:
                self.probed = False
                self._printer.commands(["G91 G1 A0.25 F500","G91 G38.2 Z-5 F200","?"])
                i-=0.25
            if i <= 0:
                self.probing = False
                self._printer.commands(["G91 Z10 F500","?"])
            await asyncio.sleep_ms(50)
        #cancel this task
        try:
            self.cont_task.cancel()
        except:
            self._logger.info("Task error")

    async def do_continuous(self, scan_dir, dir):
        length = float(self.length)
        self.probed = False
        self.first_probe = True
        self._printer.commands([f"G91 G21 G38.2 {scan_dir}-100 F200"])
        self.probe_on = True
        #probe loop
        while self.probing:
            if self.probed:
                self.first_probe = False
                self._printer.commands([f"G91 G21 G38.5 {self.scan_type}{dir}10 {scan_dir}10 F50"])
            if not self.probed:
                self._printer.commands([f"G91 G21 G1 {self.scan_type}{dir}0.25 F500","?",f"G91 G38.2 {scan_dir}-5 F50","?"])
                length-=0.25
            if length <= 0:
                self.probing = False
                self._printer.commands([f"G91 G21 G1 {scan_dir}10 F500","?"])
            await asyncio.sleep_ms(50)
        #cancel this task
        try:
            self.cont_task.cancel()
            self.finish_scan()
        except:
            print("Task error")
        

    def get_api_commands(self):
        return dict(
            start_scan=[]
        )
    
    def on_api_command(self, command, data):
        
        if command == "start_scan":
            self._logger.info(data)
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
            if self.continuous:
                self.start_continuous_scan()
            else:
                self.start_scan()

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
    
        if self.scan_type == 'A':
            z = float(f"{match.groups(1)[1]}")
            a = float(f"{match.groups(1)[2]}")
            if not self.reference:
                self.reference = (z,a)
                self.probe_data.append((0,0))
            else:
                self.probe_data.append((z-self.reference[0],a-self.reference[1]))
                self._logger.info(self.probe_data)
            self.update_probe_data()
        #X or Z scan
        else:
            x = float(f"{match.groups(1)[0]}")
            z = float(f"{match.groups(1)[1]}")
            a = float(f"{match.groups(1)[2]}")
            if not self.reference:
                self.reference = (x,z)
                self.probe_data.append((0,0))
            else:
                self.probe_data.append((x-self.reference[0],z-self.reference[1],a))
                self._logger.info(self.probe_data)
            self.update_probe_data()

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
