// apps/faceted-search/faceted_search_app.js

define(["app",
        "apps/faceted-search/faceted_search_app_router",
        "bootstrap"],
    function(ProducerManager){
  ProducerManager.module("FacetedSearchApp", function(FacetedSearchApp, ProducerManager, Backbone, Marionette, $, _){
    FacetedSearchApp.startWithParent = false;

    FacetedSearchApp.onStart = function(){
      console.log("starting FacetedSearchApp");
    };

    FacetedSearchApp.onStop = function(){
      console.log("stopping FacetedSearchApp");
    };
});

  return ProducerManager.FacetedSearchApp;
});