/*
 * View model for LE_Scanning
 *
 * Author: Paul Paukstelis
 * License: AGPLv3
 */
$(function() {
    function ScanningViewModel(parameters) {
        var self = this;
        self.ref_diam = ko.observable(0);
        self.scan_type = ko.observable(0);
        self.pull_off = ko.observable(0);
        self.scan_direction = ko.observable(0);
        self.scan_length = ko.observable(0);
        self.scan_increment = ko.observable(0);
        self.continuous = ko.observable(false);
        self.stl = ko.observable(false);
        self.name = ko.observable(null);
        self.xValues = [];
        self.zValues = [];
        self.aValues = [];

        self.start_scan = function() {
            //Need to do some sanity checks here:

            var data = {
                ref_diam: self.ref_diam(),
                scan_type: self.scan_type(),
                pull_off: self.pull_off(),
                scan_direction: self.scan_direction(),
                scan_length: self.scan_length(),
                scan_increment: self.scan_increment(),
                continuous: self.continuous(),
                stl: self.stl(),
                name: self.name(),
            };
            //console.log(data);
            OctoPrint.simpleApiCommand("scanning", "start_scan", data)
                .done(function(response) {
                    console.log("Scan started.");
                    $("#plotarea").show();
                    if (self.scan_type() === 'A') {
                        self.createPolarPlot();
                    }
                    else {
                        self.createPlot();
                    }
                })
                .fail(function() {
                    console.error("Failed to start scan");
                });
        
            };
        
        self.createPlot  = function() {
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
                    title: self.scan_type() + '-axis Scan',
                    xaxis: { 
                        title: 'X',
                        scaleanchor: 'y',  // Ensure equal scaling
                        scaleratio: 1
                    },
                    yaxis: { 
                        title: 'Z',
                        scaleanchor: 'x',  // Equal scaling with X axis
                        scaleratio: 1,
                        autorange: 'reversed'  // Invert Z-axis
                    },
                    //annotations: self.annotations,  // Include any annotations (tags)
                    showlegend: false
                };
    
                //Make a plot
                Plotly.newPlot('plotarea',[trace], layout);
    
        };

        self.createPolarPlot  = function() {
            var trace = {
                r: self.xValues,
                theta: self.zValues,
                mode: 'lines',
                name: 'Scan Profile',
                type: 'scatterpolar',
                line: {
                    color: 'blue',
                    width: 2
                }

            };

            var layout = {
                title: 'A-axis Scan',
                polar: {
                    radialaxis: {
                      visible: true,
                      autorange: true,
                    }
                }
            };

            //Make a plot
            Plotly.newPlot('plotarea',[trace], layout);

        };
        
        self.updatePlot = function() {
            Plotly.react('plotarea', [{
                x: self.xValues,
                y: self.zValues,
                yaxis: { autorange: 'reversed' }
            }]);
        };
        
        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin == 'scanning' && data.type == 'graph') {
                console.log(data);
                //self.updatePlot();
                //need to revisit how to update properly, as it seems to not do 'reversed' when using restyle
                if (self.scan_type() === 'A') {
                    self.xValues = data.probe.map(point => (self.ref_diam()/2) + point[0]);
                    self.zValues = data.probe.map(point => point[1]);
                    self.createPolarPlot();
                }
                else {
                    self.xValues = data.probe.map(point => point[0]);
                    self.zValues = data.probe.map(point => point[1]);
                    self.createPlot();
                }

            }
        }
    }
    OCTOPRINT_VIEWMODELS.push({
        construct: ScanningViewModel,
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        elements: [ "#tab_plugin_scanning" ]
    });
});
