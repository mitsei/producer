// apps/navbar/navbar_app.js

define(["app",
        "apps/navbar/views/navbar",
        "bootstrap"],
    function(ProducerManager, NavbarView){
  ProducerManager.module("NavbarApp", function(NavbarApp, ProducerManager, Backbone, Marionette, $, _){
    NavbarApp.onStart = function(){
      console.log("starting NavbarApp");
      ProducerManager.regions.navbar.show(new NavbarView());
    };

    NavbarApp.onStop = function(){
      console.log("stopping NavbarApp");
    };
});

  return ProducerManager.NavbarApp;
});