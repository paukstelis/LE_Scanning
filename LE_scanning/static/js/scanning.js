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
        self.stl = ko.observable(false)


        self.start_scan = function() {
            console.log("Made to start_scan")
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
                })
                .fail(function() {
                    console.error("Failed to start scan");
                });
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: ScanningViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        // Elements to bind to, e.g. #settings_plugin_scanning, #tab_plugin_scanning, ...
        elements: [ "#tab_plugin_scanning" ]
    });
});
