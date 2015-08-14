// Filename: regions.js
define(['marionette'
], function (Marionette) {
    var NotificationRegion = Marionette.Region.extend({
        attachHtml: function (view) {
            this.$el.fadeIn("slow");
            this.$el.append(view.el);
        }
    });

    var RegionContainer = Marionette.LayoutView.extend({
        el: "#app-container",

        regions: {
            composition: "#composition-region",
            course: "#course-selector-region",
            courseActions: "#course-actions-region",
            dialog: "#dialog-region",
            main: "#main-region",
            navbar: "#navbar-region",
            notifications: {
                regionClass: NotificationRegion,
                selector: "#notifications-region"
            },
            preview: "#preview-region",
            run: "#run-selector-region"
        }
    });

    return RegionContainer;
});