// app/notification/notification_app_router.js

define(["app",
        "apps/notification/views/notification_views"],
    function(ProducerManager, NotificationViews){
  ProducerManager.module("Routers.NotificationApp", function(NotificationAppRouter, ProducerManager, Backbone, Marionette, $, _){
    NotificationAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("NotificationApp");
      action(arg);
    };

    var API = {};

    ProducerManager.Routers.on("start", function(){
      new NotificationAppRouter.Router({
        controller: API
      });

      ProducerManager.vent.on('msg:error', function (data) {
          var message;

          if (data.hasOwnProperty('data')) {
              message = data.data;
          } else {
              message = data;
          }
            ProducerManager.regions.notifications.show(new NotificationViews.ErrorView({
                msg: message
            }));
      });

      ProducerManager.vent.on('msg:status', function (data) {
          var message;

          if (data.hasOwnProperty('verb')) {
              message = data.verb + " " + data.objType + ": " + data.data;
          } else {
              message = data;
          }
            ProducerManager.regions.notifications.show(new NotificationViews.StatusView({
                msg: message
            }));
      });

      ProducerManager.vent.on('msg:success', function (data) {
            ProducerManager.regions.notifications.show(new NotificationViews.SuccessView({
                msg: data.data
            }));
      });

    });
  });

  return ProducerManager.NavbarAppRouter;
});