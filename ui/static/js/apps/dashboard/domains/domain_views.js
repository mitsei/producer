// apps/dashboard/domains/domain_views.js

define(["app",
        "apps/dashboard/domains/collections/courses",
        "apps/dashboard/domains/collections/single_run",
        "apps/dashboard/compositions/collections/compositions",
        "apps/common/utilities",
        "text!apps/dashboard/domains/templates/repo_selector.html",
        "text!apps/dashboard/compositions/templates/composition_template.html",
        "text!apps/dashboard/compositions/templates/compositions_template.html"],
       function(ProducerManager, CourseCollection, RunCollection, CompositionsCollection,
                Utils,
                RepoSelectorTemplate, CompositionTemplate, CompositionsTemplate){
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
                runsPromise = runsView.collection.fetch(),
                _this = this;

            ProducerManager.regions.composition.empty();
            ProducerManager.regions.preview.$el.html('');
            $('div.action-menu').addClass('hidden');

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
        },
        events: {
            'change select.run-selector' : 'renderCourseStructure'
        },
        renderCourseStructure: function (e) {
            var courseId = $(e.currentTarget).val(),
                run = new RunCollection([], {id: courseId}),
                runView = new View.SingleRunView({collection: run}),
                runPromise = runView.collection.fetch();

            runPromise.done(function (data) {
                ProducerManager.regions.composition.show(runView);
                ProducerManager.regions.preview.$el.html('');
            });
            console.log('showing a single run');
        }
    });

    View.CompositionView = Marionette.ItemView.extend({
        tagName: 'li',
        template: function (serializedData) {
            return _.template(CompositionTemplate)({
                composition: serializedData
            });
        }
    });

    View.CompositionsView = Marionette.CompositeView.extend({
        initialize: function () {
            this.collection = new CompositionsCollection(this.model.get('children'));
        },
        template: function (serializedData) {
            return _.template(CompositionsTemplate)({
                composition: serializedData,
                compositionType: Utils.parseGenusType(serializedData.genusTypeId),
                rawObject: JSON.stringify(serializedData)
            });
        }
    });

    View.SingleRunView = Marionette.CollectionView.extend({
        childView: View.CompositionsView,
        className: "list-group",
        onRender: function () {
            $('div.action-menu').removeClass('hidden');
        }
    });
  });

  return ProducerManager.ProducerApp.Domain.View;
});