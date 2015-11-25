// apps/curate/views/curate_views.js

define(["app",
        "text!apps/curate/templates/curate_facets.html",
        "jquery-ui",
        "bootstrap-drawer"],
       function(ProducerManager, CurateFacetsTemplate){
  ProducerManager.module("CurateApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CurateView = Marionette.ItemView.extend({
        template: function () {
            return _.template(CurateFacetsTemplate)();
        }
    });
  });

  return ProducerManager.CurateApp.View;
});