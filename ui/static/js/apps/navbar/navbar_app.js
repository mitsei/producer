// apps/navbar/navbar_app.js

define(["app",
        "apps/navbar/navbar_app_router",
        "bootstrap"],
    function(ProducerManager){
  ProducerManager.module("NavbarApp", function(NavbarApp, ProducerManager, Backbone, Marionette, $, _){
    NavbarApp.startWithParent = false;

    NavbarApp.onStart = function(){
      console.log("starting NavbarApp");
    };

    NavbarApp.onStop = function(){
      console.log("stopping NavbarApp");
    };
});

  return ProducerManager.NavbarApp;
});