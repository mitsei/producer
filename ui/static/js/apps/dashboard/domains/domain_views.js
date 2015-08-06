// apps/dashboard/domains/domain_views.js

define(["app",
        "apps/dashboard/domains/collections/courses",
        "text!apps/dashboard/domains/templates/repo_selector.html"],
       function(ProducerManager, CourseCollection, RepoSelectorTemplate){
  ProducerManager.module("ProducerApp.Domain.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CoursesView = Marionette.ItemView.extend({
      template: function (serializedData) {
          return _.template(RepoSelectorTemplate)({
              repoType: 'course',
              repos: serializedData.items
          });
      },
        events: {
            'change select.course-selector' : 'showRuns'
        },
        showRuns: function (e) {
            var courseId = $(e.currentTarget).val(),
                runs = new CourseCollection([], {id: courseId}),
                runsView = new View.RunsView({collection: runs}),
                runsPromise = runsView.collection.fetch();

            runsPromise.done(function (data) {
                ProducerManager.regions.run.show(runsView);
                ProducerManager.regions.preview.$el.html('');
            });
            console.log('showing runs');
        }
    });

    View.RunsView = Marionette.ItemView.extend({
        template: function (serializedData) {
            return _.template(RepoSelectorTemplate)({
                repoType: 'run',
                repos: serializedData.items
            });
        }
    });
  });

  return ProducerManager.ProducerApp.Domain.View;
});