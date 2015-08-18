// app/course-actions/course_actions_app_router.js

define(["app",
        "apps/course-actions/views/course_actions_views"],
    function(ProducerManager, CourseActionsViews){
  ProducerManager.module("Routers.CourseActionsApp", function(CourseActionsRouter, ProducerManager, Backbone, Marionette, $, _){
    CourseActionsRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("CourseActionsApp");
      action(arg);
    };

    var API = {};

    ProducerManager.Routers.on("start", function(){
      new CourseActionsRouter.Router({
        controller: API
      });

      try {
          ProducerManager.regions.courseActions.show(new CourseActionsViews.CourseActionsView({}));
      } catch (e) {

      }
    });
  });

  return ProducerManager.CourseActionsRouter;
});