/*
 * View model for LE_Scanning
 *
 * Author: Paul Paukstelis
 * License: AGPLv3
 */
$(function() {
    function ScanningViewModel(parameters) {
        var self = this;
        self.reference = ko.observable(0);
        self.scan_type = ko.observable(0);
        self.pull_off = ko.observable(0);
        self.scan_direction = ko.observable(0);
        self.scan_length = ko.observable(0);
        self.scan_increment = ko.observable(0);
        self.continuous = ko.observable(false);
        self.stl = ko.observable(false);
        self.xValues = [];
        self.zValues = [];
        self.aValues = [];

        self.start_scan = function() {
            var data = {
                reference: self.reference(),
                scan_type: self.scan_type(),
                pull_off: self.pull_off(),
                scan_direction: self.scan_direction(),
                scan_length: self.scan_length(),
                scan_increment: self.scan_increment(),
                continuous: self.continuous(),
                stl: self.stl(),
            };
            console.log(data);
            OctoPrint.simpleApiCommand("scanning", "start_scan", data)
                .done(function(response) {
                    console.log("Scan started.");
                    $("#plotarea").show();
                })
                .fail(function() {
                    console.error("Failed to start scan");
                });
        
            };
        
            function plotProfile() {
                var trace = {
                    x: self.xValues,
                    y: self.zValues,
                    mode: 'lines',
                    name: 'Scan Profile',
                    line: {
                        color: 'blue',
                        width: 2
                    }
                };
    
                var layout = {
                    title: 'Scan',
                    xaxis: { 
                        title: 'X',
                        scaleanchor: 'y',  // Ensure equal scaling
                        scaleratio: 1
                    },
                    yaxis: { 
                        title: 'Z Axis',
                        scaleanchor: 'x',  // Equal scaling with X axis
                        scaleratio: 1,
                        autorange: 'reversed'  // Invert Z-axis
                    },
                    annotations: self.annotations,  // Include any annotations (tags)
                    showlegend: false
                };
    
                //Make a plot
                Plotly.newPlot('plotarea',[trace], layout);
    
            }
        
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin == 'scanning' && data.type == 'graph') {
                
            }
        }
    }
    OCTOPRINT_VIEWMODELS.push({
        construct: ScanningViewModel,
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        elements: [ "#tab_plugin_scanning" ]
    });
});
