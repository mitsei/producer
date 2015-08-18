// app/navbar/navbar_app_router.js

define(["app",
        "apps/navbar/views/navbar_views"],
    function(ProducerManager, NavbarViews){
  ProducerManager.module("Routers.NavbarApp", function(NavbarAppRouter, ProducerManager, Backbone, Marionette, $, _){
    NavbarAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("NavbarApp");
      action(arg);
    };

    var API = {};

    ProducerManager.Routers.on("start", function(){
      new NavbarAppRouter.Router({
        controller: API
      });

      try {
          ProducerManager.regions.navbar.show(new NavbarViews.NavbarView({}));
      } catch (e) {

      }
    });
  });

  return ProducerManager.NavbarAppRouter;
});