// apps/curate/curate_controller.js

define(["app",
        "apps/curate/views/curate_views"],
    function(ProducerManager, CurateViews){
  ProducerManager.module("ProducerApp.Curate", function(Curate, ProducerManager, Backbone, Marionette, $, _){
    Curate.Controller = {
      showFacets: function () {
          ProducerManager.regions.canvas.show(new CurateViews.CurateView({}));
          ProducerManager.regions.addRegion('curateFacetedSearchHeader', '#curate-faceted-search-header');
          ProducerManager.regions.addRegion('curateFacetedSearchFacets', '#curate-faceted-search-facets');
          ProducerManager.regions.addRegion('curateFacetedSearchPagination', '#curate-faceted-search-pagination');
          ProducerManager.regions.addRegion('curateFacetedSearchResults', '#curate-faceted-search-results');
          require(["apps/faceted-search/views/faceted_search_views"], function(FacetedSearchViews){
              ProducerManager.regions.curateFacetedSearchHeader.show(new FacetedSearchViews.HeaderView({}));
          });
      }
    }
  });

  return ProducerManager.ProducerApp.Curate.Controller;
});