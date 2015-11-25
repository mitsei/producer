// apps/curate/views/curate_views.js

define(["app",
        "text!apps/curate/templates/curate_facets.html",
        "text!apps/curate/templates/add_objective.html",
        "text!apps/curate/templates/objective.html",
        "text!apps/curate/templates/objectives.html",
        "jquery-ui",
        "bootstrap-drawer"],
       function(ProducerManager, CurateFacetsTemplate,
                AddObjectiveTemplate, ObjectiveTemplate, ObjectivesTemplate){
  ProducerManager.module("CurateApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CurateView = Marionette.ItemView.extend({
        template: function () {
            return _.template(CurateFacetsTemplate)();
        }
    });

    View.LearningObjectiveView = Marionette.ItemView.extend({

    });
  });

  return ProducerManager.CurateApp.View;
});