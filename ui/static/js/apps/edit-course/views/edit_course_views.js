// apps/edit-course/views/edit_course_views.js

define(["app",
        "text!apps/edit-course/templates/course_canvas.html",
        "jquery-ui",
        "bootstrap-drawer"],
       function(ProducerManager, CourseCanvasTemplate){
  ProducerManager.module("EditCourseApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CourseCanvasView = Marionette.ItemView.extend({
        template: function () {
            return _.template(CourseCanvasTemplate)();
        }
    });
  });

  return ProducerManager.EditCourseApp.View;
});