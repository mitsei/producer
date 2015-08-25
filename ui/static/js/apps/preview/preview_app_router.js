// app/preview/preview_app_router.js

define(["app",
        "apps/preview/views/preview_views"],
    function(ProducerManager, PreviewViews){
  ProducerManager.module("Routers.PreviewApp", function(PreviewAppRouter, ProducerManager, Backbone, Marionette, $, _){
    PreviewAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("PreviewApp");
      action(arg);
    };

    var API = {};

    ProducerManager.Routers.on("start", function(){
      new PreviewAppRouter.Router({
        controller: API
      });
    });
  });

  return ProducerManager.PreviewAppRouter;
});