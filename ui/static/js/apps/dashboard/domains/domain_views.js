// apps/dashboard/domains/domain_views.js

define(["app",
        "apps/dashboard/domains/collections/courses",
        "apps/dashboard/domains/collections/single_run",
        "apps/dashboard/compositions/collections/compositions",
        "apps/dashboard/compositions/models/composition",
        "apps/preview/views/preview_views",
        "apps/common/utilities",
        "text!apps/dashboard/domains/templates/repo_selector.html",
        "text!apps/dashboard/compositions/templates/composition_template.html",
        "text!apps/dashboard/compositions/templates/compositions_template.html",
        "text!apps/dashboard/assets/templates/asset_template.html"],
       function(ProducerManager, CourseCollection, RunCollection, CompositionsCollection,
                CompositionModel, PreviewViews, Utils,
                RepoSelectorTemplate, CompositionTemplate, CompositionsTemplate,
                ResourceTemplate){
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

            Utils.processing();

            runsPromise.done(function (data) {
                ProducerManager.regions.run.show(runsView);
                ProducerManager.regions.preview.$el.html('');
                Utils.doneProcessing();
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

            Utils.processing();
            runPromise.done(function (data) {
                ProducerManager.regions.composition.show(runView);
                ProducerManager.regions.preview.$el.html('');
                Utils.doneProcessing();
            });
            console.log('showing a single run');
        }
    });

    View.CompositionView = Marionette.ItemView.extend({
        tagName: 'li',
        className: 'composition',
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
        tagName: 'li',
        className: 'resortable composition list-group-item',
        template: function (serializedData) {
            return _.template(CompositionsTemplate)({
                composition: serializedData,
                compositionType: Utils.parseGenusType(serializedData.genusTypeId),
                rawObject: JSON.stringify(serializedData)
            });
        },
        onShow: function () {
            // Render the assets manually...not sure how to get two collections into
            // a single CompositeView?
            var resources = this.model.get('assets'),
                $target = this.$el.children('ul.children-compositions'),
                $resourceWrapper;

            _.each(resources, function (resource) {
                $resourceWrapper = $('<li></li>').addClass('resource resortable list-group-item');
                $resourceWrapper.append(_.template(ResourceTemplate)({
                    resource: resource,
                    resourceType: Utils.parseGenusType(resource),
                    rawObject: JSON.stringify(resource)
                }));
                $target.append($resourceWrapper);
            });


            _.each(this.$el.find('ul.children-compositions'), function (childList) {
                if ($(childList).children('li.resortable').length > 1) {
                    $(childList).children('li.no-children').addClass('hidden');
                }
            });
        },
        childViewContainer: 'ul.children-compositions'
    });

    View.SingleRunView = Marionette.CollectionView.extend({
        // this should probably be a layout of some sort...
        childView: View.CompositionsView,
        className: "list-group",
        tagName: 'ul',
        onRender: function () {
            $('div.action-menu').removeClass('hidden');
        },
        onShow: function () {
            var _this = this;
            // make the sections sortable
            $('#composition-region').sortable({
                forcePlaceholderSize: true,
                handle: 'div.drag-handles',
                helper: 'clone',
                items: 'li.resortable',
                opacity: .6,
                placeholder: 'sortable-placeholder',
                revert: 250,
                tolerance: 'intersect',
                receive: function (e, ui) {
                    var rawObj = ui.item.data('obj'),
                        $newObj = $('<li></li>').addClass('list-group-item resortable'),
                        assetIds = [],
                        parentObj, parentComposition;

                    if (rawObj.type === 'Composition') {
                        $newObj.addClass('composition');
                        $newObj.append(_.template(CompositionsTemplate)({
                            composition: rawObj,
                            compositionType: Utils.parseGenusType(rawObj),
                            rawObject: JSON.stringify(rawObj)
                        }));

                        // TODO: here still need to figure out how to get the children...
                    } else {
                        $newObj.addClass('resource');
                        $newObj.append(_.template(ResourceTemplate)({
                            resource: rawObj,
                            resourceType: Utils.parseGenusType(rawObj),
                            rawObject: JSON.stringify(rawObj)
                        }));
                    }

                    $(this).data('ui-sortable').currentItem.replaceWith($newObj);
                    _this.hideNoChildren($newObj);

                    // TODO need to save this new item back to the server
                    if (rawObj.type === 'Composition') {
                        // something
                    } else {
                        // update the parent composition model
                        parentObj = $newObj.parent()
                            .siblings('.composition-object-wrapper')
                            .data('obj');
                        parentComposition = new CompositionModel(parentObj);
                        $newObj.parent().children().not('.no-children').each(function () {
                            assetIds.push($(this).children('div.resource-object-wrapper').data('obj').id);
                        });
                        parentComposition.set('assetIds', assetIds);
                        parentComposition.save();
                    }
                },
                update: function (e, ui) {
                    // hide the no-children warning for this list
                    _this.hideNoChildren(ui.item);

                    // update the sequence order of sibling elements
                    // TODO

                    // check other lists .. if this item's old list
                    // now has no children, re-show the warning
                    _.each(_this.$el.find('ul.children-compositions'), function (childList) {
                        if ($(childList).children('li.resortable:visible').length === 0) {
                            $(childList).children('li.no-children').removeClass('hidden');
                        }
                    });
                }
            });
        },
        events: {
            'click .toggle-composition-children': 'toggleCompositionChildren',
            'click .preview': 'previewObject'
        },
        clearActiveElement: function () {
            $('div.object-wrapper').removeClass('alert alert-info');
        },
        hideNoChildren: function (el) {
            $(el).siblings('li.no-children').addClass('hidden');
        },
        previewObject: function (e) {
            var $wrapper = $(e.currentTarget).closest('div.object-wrapper'),
                rawObj = $wrapper.data('obj'),
                objId = rawObj.id;

            this.clearActiveElement();
            $wrapper.addClass('alert alert-info');

            if (rawObj.type === 'Composition') {
                ProducerManager.regions.preview.show(new PreviewViews.CompositionView({
                    objId: objId
                }));
            } else {
                ProducerManager.regions.preview.show(new PreviewViews.ResourceView({
                    objId: objId
                }));
            }
        },
        toggleCompositionChildren: function (e) {
            var $e = $(e.currentTarget),
                $footer = $e.parent(),
                $composition = $e.parent().parent().parent(),
                $children = $composition.children('.children-compositions');

//            this.clearActiveElement();
            $children.toggleClass('hidden');
            $footer.toggleClass('expanded');
            $e.find('.children-icon').toggleClass('fa-chevron-up')
                .toggleClass('fa-chevron-down');
            $e.find('.children-action-hide').toggleClass('hidden');
            $e.find('.children-action-show').toggleClass('hidden');
        }
    });
  });

  return ProducerManager.ProducerApp.Domain.View;
});