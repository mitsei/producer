// apps/dashboard/domains/domain_controller.js

define(["app",
        "apps/dashboard/domains/collections/courses"],
    function(ProducerManager, CourseCollection){
  ProducerManager.module("ProducerApp.Domain", function(Domain, ProducerManager, Backbone, Marionette, $, _){
    Domain.Controller = {
      listCourses: function(id){
        require(["apps/dashboard/domains/domain_views"], function(DomainViews){
            var courses = new CourseCollection([], {id: id}),
                coursesView = new DomainViews.CoursesView({collection: courses}),
                coursesPromise = coursesView.collection.fetch();

            coursesPromise.done(function (data) {
                ProducerManager.regions.course.show(coursesView);
                ProducerManager.regions.preview.$el.html('');
            });
        });
      }
    }
  });

  return ProducerManager.ProducerApp.Domain.Controller;
});