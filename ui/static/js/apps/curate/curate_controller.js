// apps/curate/curate_controller.js

define(["app",
        "apps/curate/views/curate_views",
        "apps/curate/collections/objectives"],
    function(ProducerManager, CurateViews, ObjectivesCollection){
  ProducerManager.module("ProducerApp.Curate", function(Curate, ProducerManager, Backbone, Marionette, $, _){
    Curate.Controller = {
      showFacets: function () {
          ProducerManager.regions.canvas.show(new CurateViews.CurateView({}));
          ProducerManager.regions.addRegion('curateFacetedSearchHeader', '#curate-faceted-search-header');
          ProducerManager.regions.addRegion('curateFacetedSearchFacets', '#curate-faceted-search-facets');
          ProducerManager.regions.addRegion('curateFacetedSearchPagination', '#curate-faceted-search-pagination');
          ProducerManager.regions.addRegion('curateFacetedSearchResults', '#curate-faceted-search-results');
          ProducerManager.regions.addRegion('curateLearningObjectives', '#curate-learning-objectives');
          require(["apps/faceted-search/views/faceted_search_views"], function(FacetedSearchViews){
              ProducerManager.regions.curateFacetedSearchHeader.show(new FacetedSearchViews.HeaderView({}));
          });
      },
      showLearningObjectives: function (objectId) {
          var objectives = new ObjectivesCollection([], {id: objectId}),
                runsView = new DomainViews.RunsView({collection: runs}),
                runsPromise = runsView.collection.fetch({
                    reset: true,
                    error: function (model, xhr, options) {
                        ProducerManager.vent.trigger('msg:error', xhr.responseText);
                        Utils.doneProcessing();
                    }
                });

            ProducerManager.regions.composition.empty();
            ProducerManager.regions.preview.$el.html('');
            $('div.action-menu').addClass('hidden');

            Utils.processing();

            runsPromise.done(function (data) {
                ProducerManager.regions.run.show(runsView);
                ProducerManager.regions.preview.$el.html('');
                Utils.doneProcessing();
            });
          ProducerManager.regions.curateLearningObjectives.show(new CurateViews.LearningObjectiveView({}));
      }
    }
  });

  return ProducerManager.ProducerApp.Curate.Controller;
});