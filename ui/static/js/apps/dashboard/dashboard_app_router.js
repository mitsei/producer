// app/dashboard/dashboard_app_router.js

define(["app",
        "apps/common/utilities",
        "cookies"],
    function(ProducerManager, Utils, Cookies){
  ProducerManager.module("Routers.ProducerApp", function(ProducerAppRouter, ProducerManager, Backbone, Marionette, $, _){
    ProducerAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
        "": "initialize",
        "curate": "curateObjects",
        "edit/:courseId": "showCourseRuns",
        "edit/:courseId/:runId": "editCourseRun"
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("ProducerApp");
      action(arg);
    };

    var API = {
//      addDomainRepo: function(){
//          Utils.fixDomainSelector('#repos/new');
//      },
        curateObjects: function () {
            // placeholder for a dashboard for curating objects and applying tags
        },
        editCourseRun: function (courseId, runId) {
            // placeholder for showing a course run in the edit canvas (on left)
            console.log('editing: ' + courseId + ', ' + runId);

            Cookies.set('courseId', courseId);
            Cookies.set('runId', runId);

            require(["apps/dashboard/domains/domain_controller"], function(DomainController){
                executeAction(DomainController.renderUserCourseRun, runId);
            });
        },
        initialize: function () {
            Cookies.remove('courseId');
            Cookies.remove('runId');
        },
        showCourseRuns: function (courseId) {
            console.log('editing course: ' + courseId);
            Cookies.set('courseId', courseId);
            require(["apps/dashboard/domains/domain_controller"], function(DomainController){
                executeAction(DomainController.listUserCourseRuns, courseId);
            });
        }
    };

    ProducerManager.on("userCourseRun:edit", function(courseId, runId){
        ProducerManager.navigate("edit/" + courseId + '/' + runId);
        API.editCourseRun(courseId, runId);
    });

    ProducerManager.on("userCourseRuns:show", function(courseId){
        ProducerManager.navigate("edit/" + courseId);
        API.showCourseRuns(courseId);
    });

    ProducerManager.Routers.on("start", function(){
      new ProducerAppRouter.Router({
        controller: API
      });
    });
  });

  return ProducerManager.ProducerAppRouter;
});