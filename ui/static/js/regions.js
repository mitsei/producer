// Filename: regions.js
define(['marionette'
], function (Marionette) {
    var RegionContainer = Marionette.LayoutView.extend({
        el: "#app-container",

        regions: {
            composition: "#composition-region",
            course: "#course-selector-region",
            dialog: "#dialog-region",
            main: "#main-region",
            navbar: "#navbar-region",
            preview: "#preview-region",
            run: "#run-selector-region"
        }
    });

    return RegionContainer;
});