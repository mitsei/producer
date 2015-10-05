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
            canvas: "#left-canvas",
            dialog: "#dialog-region",
            facetedSearchHeader: '#faceted-search-header',
            facetedSearchFacets: '#faceted-search-facets',
            facetedSearchPagination: '#faceted-search-pagination',
            facetedSearchResults: '#faceted-search-results',
            main: "#main-region",
            navbar: "#navbar-region",
            notifications: {
                regionClass: NotificationRegion,
                selector: "#notifications-region"
            },
            preview: "#preview-region"
        }
    });

    return RegionContainer;
});