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
        "text!apps/dashboard/assets/templates/asset_template.html",
        "jquery-sortable"],
       function(ProducerManager, CourseCollection, RunCollection, CompositionsCollection,
                CompositionModel, PreviewViews, Utils,
                RepoSelectorTemplate, CompositionTemplate, CompositionsTemplate,
                ResourceTemplate){
  ProducerManager.module("ProducerApp.Domain.View", function(View, ProducerManager, Backbone, Marionette, $, _){

    function updateCompositionChildrenAndAssets ($obj) {
        // $obj is assumed to be an <li .resortable></li> tag
        var childIds = [],
            parentObj,
            parentComposition,
            $parent;

        if (!$obj.is('li.resortable')) {
            return false;
        }
        $parent = $obj.parent();
        if ($parent.is('ul.run-list')) {
            if ($obj.is('li.resource')) {
                $obj.remove();
                ProducerManager.vent.trigger("msg:error",
                    'You cannot add resources to the root level.');
            } else {
                var runId = $('select.run-selector').val(),
                    parentRun = new RunCollection([], {id: runId});

                $parent.children(':visible').not('.no-children,.ui-sortable-helper').each(function () {
                    var thisObj = $(this).children('div.object-wrapper').data('obj');
                    childIds.push(thisObj.id);
                });
                parentRun.childIds = childIds;
                parentRun.save();
            }
        } else {
            parentObj = $parent.siblings('.composition-object-wrapper')
                .data('obj');
            parentComposition = new CompositionModel(parentObj);
            $parent.children(':visible').not('.no-children,.ui-sortable-helper').each(function () {
                var thisObj = $(this).children('div.object-wrapper').data('obj');
                childIds.push(thisObj.id);
            });
            parentComposition.set('childIds', childIds);
            parentComposition.save();
        }
    }

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

    View.CompositionsView = Marionette.CompositeView.extend({
        initialize: function () {
            this.collection = new CompositionsCollection(this.model.get('children'));
        },
        tagName: 'li',
        className: 'resortable composition list-group-item',
        template: function (serializedData) {
            if (serializedData.type === 'Composition') {
                return _.template(CompositionsTemplate)({
                    composition: serializedData,
                    compositionType: Utils.parseGenusType(serializedData.genusTypeId),
                    rawObject: JSON.stringify(serializedData)
                });
            } else {
                return _.template(ResourceTemplate)({
                    resource: serializedData,
                    resourceType: Utils.parseGenusType(serializedData),
                    rawObject: JSON.stringify(serializedData)
                });
            }
        },
        onShow: function () {
            // fix the parent class for the resources...instead of
            // <li.composition.resortable> they should be <li.resource.resortable>
            _.each(this.$el.find('li.resortable:not(.no-children)'), function (node) {
                var $n = $(node),
                    rawObj = $n.children('div.object-wrapper').data('obj');
                if (rawObj.type !== 'Composition') {
                    $n.removeClass('composition')
                        .addClass('resource');
                }
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
        className: "list-group run-list",
        tagName: 'ul',
        onRender: function () {
            $('div.action-menu').removeClass('hidden');
        },
        onShow: function () {
            var _this = this;
            // make the sections sortable
            $('ul.run-list').sortable({
                group: 'producer',
                handle: 'div.drag-handles',
                itemSelector: 'li.resortable:not(.no-children), li.resource',
                pullPlaceholder: false,
                placeholderClass: 'sortable-placeholder',
                placeholder: '<li class="sortable-placeholder"></li>',
                onDragStart: function ($item, container, _super) {
                    // Duplicate items of the no drop area
                    if(!container.options.drop) {
                        $item.clone().insertAfter($item);
                    }

                    // Try to save an item in the pre-move parent
                    // use the no-children one because it is guaranteed to be present
                    $item.data('pre-move-parent-obj', $item.parent().children('li.no-children'));
                    _super($item, container);
                },
                onDrop: function ($item, container, _super, e) {
                    // transform the item if it came from the no-drop area
                    var $preMoveObj = $item.data('pre-move-parent-obj'),
                        $newObj;
                    if($item.hasClass('search-result')) {
                        var rawObj = $item.data('obj'),
                            $newObj = $('<li></li>').addClass('list-group-item resortable');

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

                        $item.replaceWith($newObj);
                    } else {
                        $newObj = $item;
                    }
                    _super($newObj, container);

                    // update the object's current parent and the old parent...
                    updateCompositionChildrenAndAssets($newObj);
                    if ($preMoveObj.parent()[0] != $newObj.parent()[0]) {
                        updateCompositionChildrenAndAssets($preMoveObj);
                    }

                    _this.refreshNoChildrenWarning();
                }
            });
//            $('#composition-region').sortable({
//                forcePlaceholderSize: true,
//                handle: 'div.drag-handles',
//                helper: 'clone',
//                items: 'li.resortable',
//                opacity: .6,
//                placeholder: 'sortable-placeholder',
//                revert: 250,
//                tolerance: 'pointer',
//                beforeStop: function (e, ui) {
//                    // ui.helper.parent() is the original parent here, before
//                    // DOM position change. Remove the item from the
//                    // parent list.
//                    updateCompositionChildrenAndAssets(ui.helper);
//                },
//                receive: function (e, ui) {
//                    var rawObj = ui.item.data('obj'),
//                        $newObj = $('<li></li>').addClass('list-group-item resortable');
//
//                    if (rawObj.type === 'Composition') {
//                        $newObj.addClass('composition');
//                        $newObj.append(_.template(CompositionsTemplate)({
//                            composition: rawObj,
//                            compositionType: Utils.parseGenusType(rawObj),
//                            rawObject: JSON.stringify(rawObj)
//                        }));
//
//                        // TODO: here still need to figure out how to get the children...
//                    } else {
//                        $newObj.addClass('resource');
//                        $newObj.append(_.template(ResourceTemplate)({
//                            resource: rawObj,
//                            resourceType: Utils.parseGenusType(rawObj),
//                            rawObject: JSON.stringify(rawObj)
//                        }));
//                    }
//
//                    $(this).data('ui-sortable').currentItem.replaceWith($newObj);
//                    _this.hideNoChildren($newObj);
//
//                    // save this new item back to the server
//                    // update the parent composition model
//                    updateCompositionChildrenAndAssets($newObj);
//                },
//                update: function (e, ui) {
//                    // hide the no-children warning for this list
//                    _this.hideNoChildren(ui.item);
//
//                    // update the sequence order of sibling elements
//                    updateCompositionChildrenAndAssets(ui.item);
//
//                    // remove the item from the previous parent??
//                    // TODO
//
//                    // check other lists .. if this item's old list
//                    // now has no children, re-show the warning
//                    _.each(_this.$el.find('ul.children-compositions'), function (childList) {
//                        if ($(childList).children('li.list-group-item.resource,li.list-group-item.composition')
//                                .length === 0) {
//                            $(childList).children('li.no-children').removeClass('hidden');
//                        }
//                    });
//                }
//            });
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
        refreshNoChildrenWarning: function () {
            _.each(this.$el.find('ul.children-compositions'), function (childList) {
                if ($(childList).children('li.list-group-item.resource,li.list-group-item.composition')
                        .length === 0) {
                    $(childList).children('li.no-children').removeClass('hidden');
                } else {
                    $(childList).children('li.no-children').addClass('hidden');
                }
            });
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