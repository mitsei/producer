// apps/dashboard/dashboard_app.js

define(["app",
        "apps/dashboard/dashboard_app_router",
        "bootstrap"],
    function(ProducerManager){
  ProducerManager.module("ProducerApp", function(ProducerApp, ProducerManager, Backbone, Marionette, $, _){
    ProducerApp.startWithParent = false;

    ProducerApp.onStart = function(){
      console.log("starting ProducerApp");
    };

    ProducerApp.onStop = function(){
      console.log("stopping ProducerApp");
    };
});

  return ProducerManager.ProducerApp;
});