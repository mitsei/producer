// apps/notification/notification_app.js

define(["app",
        "apps/notification/notification_app_router",
        "bootstrap"],
    function(ProducerManager){
  ProducerManager.module("NotificationApp", function(NotificationApp, ProducerManager, Backbone, Marionette, $, _){
    NotificationApp.startWithParent = false;

    NotificationApp.onStart = function(){
      console.log("starting NotificationApp");
    };

    NotificationApp.onStop = function(){
      console.log("stopping NotificationApp");
    };
});

  return ProducerManager.NotificationApp;
});