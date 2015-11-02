// apps/curate/curate_controller.js

define(["app",
        "apps/curate/views/curate_views"],
    function(ProducerManager, CurateViews){
  ProducerManager.module("ProducerApp.Curate", function(Curate, ProducerManager, Backbone, Marionette, $, _){
    Curate.Controller = {
      renderCanvas: function () {
          ProducerManager.regions.canvas.show(new EditCourseViews.CourseCanvasView({}));
          ProducerManager.regions.addRegion('composition', '#composition-region');
          ProducerManager.regions.addRegion('course', '#course-selector-region');
          ProducerManager.regions.addRegion('courseActions', '#course-actions-region');
          ProducerManager.regions.addRegion('run', '#run-selector-region');
//          require(["apps/course-actions/views/course_actions_views"], function (DomainController) {
//              executeAction(DomainController.listUserCourseRuns, courseId);
//              executeAction(DomainController.renderUserCourseRun, runId);
//          });
      }
    }
  });

  return ProducerManager.ProducerApp.Curate.Controller;
});