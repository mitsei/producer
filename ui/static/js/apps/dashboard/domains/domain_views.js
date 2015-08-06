// apps/dashboard/domains/domain_views.js

define(["app",
        "text!apps/dashboard/domains/templates/repo_selector.html"],
       function(ProducerManager, RepoSelectorTemplate){
  ProducerManager.module("ProducerApp.Domain.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CoursesView = Marionette.ItemView.extend({
      template: function (serializedData) {
          return _.template(RepoSelectorTemplate)({
              repoType: 'course',
              repos: serializedData.items
          });
      },
        events: {

        }
    });

    View.showCourses = function (options) {
        var courseView = new View.CoursesView(options);
        courseView.render();
    };
  });

  return ProducerManager.ProducerApp.Domain.View;
});