// apps/curate/curate_controller.js

define(["app",
        "apps/common/utilities",
        "apps/curate/views/curate_views",
        "apps/curate/collections/asset_objectives",
        "apps/curate/collections/composition_objectives",
        "apps/curate/collections/item_objectives"],
    function(ProducerManager, Utils, CurateViews, AssetObjectivesCollection,
             CompositionObjectivesCollection, ItemObjectivesCollection){
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
          if (objectId.indexOf('repository.Asset') >= 0) {
              var objectives = new AssetObjectivesCollection([], {id: objectId});
          } else if (objectId.indexOf('repository.Composition') >= 0) {
              var objectives = new CompositionObjectivesCollection([], {id: objectId});
          } else if (objectId.indexOf('assessment.Item') >= 0) {
              var objectives = new ItemObjectivesCollection([], {id: objectId});
          } else {
              console.log('error in objectId: ' + objectId);
          }

          var objectivesView = new CurateViews.ManageLearningObjectivesView({collection: objectives}),
              objectivesPromise = objectivesView.collection.fetch({
                  reset: true,
                  error: function (model, xhr, options) {
                      ProducerManager.vent.trigger('msg:error', xhr.responseText);
                      Utils.doneProcessing();
                  }
              });

            Utils.processing();

            objectivesPromise.done(function (data) {
                ProducerManager.regions.curateLearningObjectives.show(objectivesView);
                Utils.doneProcessing();
            });
      }
    }
  });

  return ProducerManager.ProducerApp.Curate.Controller;
});