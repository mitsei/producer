// apps/course-actions/course_actions_app.js

define(["app",
        "apps/course-actions/course_actions_app_router"],
    function(ProducerManager){
  ProducerManager.module("CourseActionsApp", function(CourseActionsApp, ProducerManager, Backbone, Marionette, $, _){
    CourseActionsApp.startWithParent = false;

    CourseActionsApp.onStart = function(){
      console.log("starting CourseActionsApp");
    };

    CourseActionsApp.onStop = function(){
      console.log("stopping CourseActionsApp");
    };
});

  return ProducerManager.CourseActionsApp;
});