// app/faceted-search/faceted_search_app_router.js

define(["app",
        "apps/faceted-search/views/faceted_search_views"],
    function(ProducerManager, FacetedSearchViews){
  ProducerManager.module("Routers.FacetedSearchApp", function(FacetedSearchAppRouter, ProducerManager, Backbone, Marionette, $, _){
    FacetedSearchAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("FacetedSearchApp");
      action(arg);
    };

    var API = {};

    ProducerManager.Routers.on("start", function(){
      new FacetedSearchAppRouter.Router({
        controller: API
      });

      try {
          ProducerManager.regions.facetedSearchHeader.show(new FacetedSearchViews.HeaderView({}));
      } catch (e) {
          console.log(e);
      }
    });
  });

  return ProducerManager.FacetedSearchAppRouter;
});