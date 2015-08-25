// apps/preview/preview_app.js

define(["app",
        "apps/preview/preview_app_router",
        "bootstrap"],
    function(ProducerManager){
  ProducerManager.module("PreviewApp", function(PreviewApp, ProducerManager, Backbone, Marionette, $, _){
    PreviewApp.startWithParent = false;

    PreviewApp.onStart = function(){
      console.log("starting PreviewApp");
    };

    PreviewApp.onStop = function(){
      console.log("stopping PreviewApp");
    };
});

  return ProducerManager.PreviewApp;
});