// apps/edit-course/edit_course_controller.js

define(["app",
        "apps/edit-course/views/edit_course_views"],
    function(ProducerManager, EditCourseViews){
  ProducerManager.module("ProducerApp.EditCourse", function(EditCourse, ProducerManager, Backbone, Marionette, $, _){
    EditCourse.Controller = {
      renderCanvas: function () {
          ProducerManager.regions.canvas.show(new EditCourseViews.CourseCanvasView({}));
          ProducerManager.regions.addRegion('composition', '#composition-region');
          ProducerManager.regions.addRegion('course', '#course-selector-region');
          ProducerManager.regions.addRegion('courseActions', '#course-actions-region');
          ProducerManager.regions.addRegion('run', '#run-selector-region');
          require(["apps/course-actions/views/course_action_views"], function (DomainController) {
              executeAction(DomainController.listUserCourseRuns, courseId);
              executeAction(DomainController.renderUserCourseRun, runId);
          });
      }
    }
  });

  return ProducerManager.ProducerApp.EditCourse.Controller;
});