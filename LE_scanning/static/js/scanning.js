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
        self.dooval = ko.observable(0);
        self.scanning = ko.observable(false);
        self.xValues = [];
        self.zValues = [];
        self.aValues = [];
        const colors = [
                        "#0082c8", // blue
                        "#e6194b", // red
                        "#3cb44b", // green
                        "#ffe119", // yellow
                        "#f58231", // orange
                        "#911eb4", // purple
                        "#46f0f0", // cyan
                        "#f032e6", // magenta
                        "#d2f53c", // lime
                        "#fabebe", // pink
                        "#008080", // teal
                        "#e6beff", // lavender
                        "#aa6e28", // brown
                        "#fffac8", // beige
                        "#800000", // maroon
                        "#aaffc3", // mint
                        "#808000", // olive
                        "#ffd8b1", // apricot
                        "#000080", // navy
                        "#808080"  // gray
                        ];

        self.start_scan = function() {
            //Need to do some sanity checks here:
            var error = false;
            if (Number(self.scan_increment()) > Number(self.scan_length())) {
                error = "Scan increment greater than length!";
                console.log(self.scan_increment());
                console.log(self.scan_length());
            }
            if (self.stl() && (self.ref_diam() < 5 )) {
                error = "Reference diameter must be greater than 5mm";
            }

            if (Number(self.pull_off()) < 0) {
                error = "Pull-off value must be greater than 0";
            }

            if (Number(self.dooval()) > 1 && Number(self.dooval()) < 4) {
                error = "Ovality must be at least 4";
            }

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
                dooval: self.dooval(),
            };
            
            if (self.dooval() && error === false) {
                alert("Ovality scans require a known A-axis zero point. Mark the first scan point on your work piece!")
            }

            if (error === false) {
                OctoPrint.simpleApiCommand("scanning", "start_scan", data)
                    .done(function(response) {
                        console.log("Scan started.");
                        $("#plotarea").show();
                        self.createPlot();
                        self.scanning(true);
                    })
                    .fail(function() {
                        console.error("Failed to start scan");
                    });
            }
            else { alert(error); }
        
            };
        
        self.stop_scan = function() {
            OctoPrint.simpleApiCommand("scanning", "stop_scan")
                .done(function(response) {
                    console.log("Scan stopped.");
                    self.scanning(false);
                })
                .fail(function() {
                    console.error("Failed to stop scan");
                });
        };

        self.createPlot  = function(probeData) {
            // Split probeData into segments on "NEXTSEGMENT", ignore lines starting with ';'
            let segments = [];
            let currentSegment = [];
            for (let i = 0; i < probeData.length; i++) {
                const point = probeData[i];
                // Ignore comments
                if (typeof point === "string" && point.startsWith(";")) {
                    continue;
                }
                if (point === "NEXTSEGMENT") {
                    if (currentSegment.length > 0) {
                        segments.push(currentSegment);
                        currentSegment = [];
                    }
                } else {
                    currentSegment.push(point);
                }
            }
            // Push the last segment if it has points
            if (currentSegment.length > 0) {
                segments.push(currentSegment);
            }

            // Build traces for each segment with different colors
            let traces = [];
            for (let i = 0; i < segments.length; i++) {
                let seg = segments[i];
                let x = seg.map(point => point[0]);
                let y = seg.map(point => point[1]);
                traces.push({
                    x: x,
                    y: y,
                    mode: 'lines',
                    name: 'Scan Profile',
                    line: {
                        color: colors[i % colors.length],
                        width: 2
                    }
                });
            }

            var layout = {
                title: self.scan_type() + '-axis Scan',
                xaxis: { 
                    title: 'X',
                    scaleanchor: 'y',
                    scaleratio: 1
                },
                yaxis: { 
                    title: 'Z',
                    scaleanchor: 'x',
                    scaleratio: 1,
                    autorange: 'reversed'
                },
                showlegend: false
            };

            Plotly.newPlot('plotarea', traces, layout);
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
                self.createPlot(data.probe);
            }
        }
    }
    OCTOPRINT_VIEWMODELS.push({
        construct: ScanningViewModel,
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        elements: [ "#tab_plugin_scanning" ]
    });
});
