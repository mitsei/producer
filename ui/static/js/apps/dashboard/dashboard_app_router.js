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
        "sandbox": "showMySandbox",
        "edit/:courseId": "showCourseRuns",
        "edit/:courseId/:runId": "editCourseRun"
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("ProducerApp");
      action(arg);
    };

    var API = {
        curateObjects: function () {
            // placeholder for a dashboard for curating objects and applying tags
            require(["apps/curate/curate_controller"], function(CurateController){
                CurateController.showFacets();
            });
        },
        editCourseRun: function (courseId, runId) {
            // placeholder for showing a course run in the edit canvas (on left)
            console.log('editing: ' + courseId + ', ' + runId);
            require(["apps/edit-course/edit_course_controller"], function(EditCourseController) {
                EditCourseController.renderCanvas();
                if (Cookies.get('courseId') !== courseId || Cookies.get('runId') !== runId) {
                    Cookies.set('courseId', courseId);
                    Cookies.set('runId', runId);

                    require(["apps/dashboard/domains/domain_controller"], function (DomainController) {
                        executeAction(DomainController.listUserCourses, Utils.userRepoId());
                        executeAction(DomainController.listUserCourseRuns, courseId);
                        executeAction(DomainController.renderUserCourseRun, runId);
                    });
                }
            });
        },
        initialize: function () {
            Cookies.remove('courseId');
            Cookies.remove('runId');
        },
        showCourseRuns: function (courseId) {
            console.log('editing course: ' + courseId);
            require(["apps/edit-course/edit_course_controller"], function(EditCourseController) {
                EditCourseController.renderCanvas();
                if (Cookies.get('courseId') !== courseId) {
                    Cookies.set('courseId', courseId);
                    Cookies.remove('runId');
                    require(["apps/dashboard/domains/domain_controller"], function (DomainController) {
                        executeAction(DomainController.listUserCourses, Utils.userRepoId());
                        executeAction(DomainController.listUserCourseRuns, courseId);
                    });
                }
            });
        },
        showMySandbox: function () {
            require(["apps/dashboard/domains/domain_controller",
                     "apps/edit-course/edit_course_controller"],
                function (DomainController, EditCourseController) {
                    executeAction(EditCourseController.renderCanvas);
                    executeAction(DomainController.listUserCourses, Utils.userRepoId());
            });
        }
    };

    ProducerManager.on("curate", function(){
        API.curateObjects();
    });

    ProducerManager.on("sandbox", function(){
        if (Utils.cookie('courseId') === '-1' && Utils.cookie('runId') === '-1') {
            API.showMySandbox();
        } else if (Utils.cookie('runId') === '-1') {
            // only have courseId
            ProducerManager.navigate('edit/' + Utils.cookie('courseId'));
            API.showCourseRuns(Utils.cookie('courseId'));
        } else {
            // has runId and courseId
            var courseId = Utils.cookie('courseId'),
                runId = Utils.cookie('runId');

            ProducerManager.navigate('edit/' + courseId + '/' + runId);

            Cookies.remove('courseId');
            Cookies.remove('runId');

            API.editCourseRun(courseId, runId);
        }
    });

    ProducerManager.on("userCourseRun:edit", function(courseId, runId){
        API.editCourseRun(courseId, runId);
    });

    ProducerManager.on("userCourseRuns:show", function(courseId){
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