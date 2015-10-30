// apps/dashboard/domains/domain_controller.js

define(["app",
        "apps/dashboard/domains/collections/domain_courses",
        "apps/dashboard/domains/collections/domain_course_offerings",
        "apps/dashboard/domains/collections/single_run",
        "apps/dashboard/domains/domain_views",
        "apps/common/utilities",
        "cookies"],
    function(ProducerManager, DomainCourseCollection, DomainCourseOfferingsCollection,
             SingleRunCollection,
             DomainViews, Utils, Cookies){
  ProducerManager.module("ProducerApp.Domain", function(Domain, ProducerManager, Backbone, Marionette, $, _){
    Domain.Controller = {
      listUserCourses: function (id) {
        require(["apps/dashboard/domains/domain_views"], function(DomainViews){
            var courses = new DomainCourseCollection([], {id: id}),
                coursesView = new DomainViews.CoursesView({collection: courses}),
                coursesPromise = coursesView.collection.fetch();

            coursesPromise.done(function (data) {
                ProducerManager.regions.course.show(coursesView);
                ProducerManager.regions.preview.$el.html('');
            });
        });
      },
      listUserCourseRuns: function (courseId) {
        var runs = new DomainCourseOfferingsCollection([], {id: courseId}),
            runsView = new DomainViews.RunsView({collection: runs}),
            runsPromise = runsView.collection.fetch({
                reset: true,
                error: function (model, xhr, options) {
                    ProducerManager.vent.trigger('msg:error', xhr.responseText);
                    Utils.doneProcessing();
                }
            });

        ProducerManager.regions.composition.empty();
        ProducerManager.regions.preview.$el.html('');
        $('div.action-menu').addClass('hidden');

        Utils.processing();

        runsPromise.done(function (data) {
            ProducerManager.regions.run.show(runsView);
            ProducerManager.regions.preview.$el.html('');
            Utils.doneProcessing();
        });
        console.log('showing runs');
      },
      renderUserCourseRun: function (runId) {
        var run = new SingleRunCollection([], {id: runId}),
            runView = new DomainViews.SingleRunView({collection: run}),
            runPromise = runView.collection.fetch({
                reset: true,
                error: function (model, xhr, options) {
                    ProducerManager.vent.trigger('msg:error', xhr.responseText);
                    Utils.doneProcessing();
                }
            }),
            downloadUrl = window.location.protocol + '//' + window.location.hostname +
                ':' + window.location.port + '/api/v1/repository/compositions/' + runId +
                '/download/';

        Utils.processing();

        $('#download-run-btn').attr('href', downloadUrl);
        runPromise.done(function (data) {
            ProducerManager.regions.composition.show(runView);
            ProducerManager.regions.preview.$el.html('');
            Utils.doneProcessing();

        });
        console.log('showing a single run');
      }
    }
  });

  return ProducerManager.ProducerApp.Domain.Controller;
});