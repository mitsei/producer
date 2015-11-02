// apps/dashboard/domains/domain_views.js

define(["app",
        "apps/course-actions/views/course_actions_views",
        "apps/dashboard/domains/collections/domain_courses",
        "apps/dashboard/compositions/collections/compositions",
        "apps/dashboard/compositions/collections/composition_children",
        "apps/dashboard/compositions/models/composition",
        "apps/dashboard/domains/models/repository",
        "apps/preview/views/preview_views",
        "apps/common/utilities",
        "text!apps/dashboard/domains/templates/repo_selector.html",
        "text!apps/dashboard/compositions/templates/composition_template.html",
        "text!apps/dashboard/compositions/templates/compositions_template.html",
        "text!apps/dashboard/assets/templates/asset_template.html",
        "text!apps/common/templates/delete_dialog.html",
        "text!apps/dashboard/compositions/templates/create_user_course.html",
        "text!apps/dashboard/compositions/templates/create_user_run.html",
        "cookies",
        "jquery-sortable"],
       function(ProducerManager, CourseActionsViews, DomainCourseCollection, CompositionsCollection,
                CompositionChildrenCollection, CompositionModel, RepositoryModel, PreviewViews, Utils,
                RepoSelectorTemplate, CompositionTemplate, CompositionsTemplate,
                ResourceTemplate, DeleteConfirmationTemplate, CreateUserCourseTemplate,
                CreateUserRunTemplate, Cookies){
  ProducerManager.module("ProducerApp.Domain.View", function(View, ProducerManager, Backbone, Marionette, $, _){

    function renderChildren (data, $el) {
        // recursively render children from data onto the <ul.children-compositions> of $el
        // basically replicate functionality of Marionette's CompositeView, except
        // need to use this when injecting individual compositions from the
        // facet results pane.
        var $target = $el.children('ul.children-compositions'),
            canEdit = false,
            // check the parent object -- canEdit should inherit
            parent = $el.children('.object-wrapper').data('obj'),
            canEditParent = true,
            children;

        $target.children('li.resortable:not(.no-children)')
            .remove();

        if (data.hasOwnProperty('children')) {
            children = data.children;
        } else {
            children = data;
        }

        if (parent.hasOwnProperty('canEdit')) {
            canEditParent = parent.canEdit;
        }

        _.each(children, function (child) {
            var $wrapper = $('<li></li>').addClass('resortable list-group-item');

            if (child.hasOwnProperty('canEdit')) {
                canEdit = child.canEdit;
            }
            if (child.type === 'Composition') {
                $wrapper.append(_.template(CompositionsTemplate)({
                    canEdit: canEdit,
                    canEditParent: canEditParent,
                    composition: child,
                    compositionType: Utils.parseGenusType(child),
                    exportUrl: Utils.exportUrl(child),
                    rawObject: JSON.stringify(child)
                }));
                $wrapper.addClass('composition');
            } else {
                $wrapper.append(_.template(ResourceTemplate)({
                    canEdit: canEdit,
                    canEditParent: canEditParent,
                    exportUrl: Utils.exportUrl(child),
                    resource: child,
                    resourceType: Utils.parseGenusType(child),
                    rawObject: JSON.stringify(child)
                }));
                $wrapper.addClass('resource');
            }
            $target.append($wrapper);
            try {
                if (child.type === 'Composition' && child.children.length > 0) {
                    renderChildren(child, $wrapper);
                }
            } catch (e) {
                console.log(e);
            }
        });


    }

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
                    parentRun = new RepositoryModel({id: runId});

                $parent.children(':visible').not('.no-children,.ui-sortable-helper').each(function () {
                    var thisObj = $(this).children('div.object-wrapper').data('obj');
                    childIds.push(thisObj.id);
                });
                parentRun.set('childIds', childIds);
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
            var preselectedId = Utils.cookie('courseId');
            return _.template(RepoSelectorTemplate)({
                preselectedId: preselectedId,
                repoType: 'course',
                repos: serializedData.items
            });
        },
        onShow: function () {
            if (Utils.cookie('courseId') !== '-1') {
                this.$el.find('select.course-selector')
                    .trigger('change');
            }
        },
        events: {
            'change select.course-selector' : 'showRuns'
        },
        showRuns: function (e) {
            var courseId = $(e.currentTarget).val();

            if (courseId === '-1') {
                return;
            }

            if (courseId !== 'create') {
                ProducerManager.navigate("edit/" + courseId);
                require(["apps/dashboard/domains/domain_controller"], function(DomainController){
                    DomainController.listUserCourseRuns(courseId);
                });
            } else {
                // bring up a modal to create the course
                ProducerManager.regions.dialog.show(new View.CreateUserCourseView());
                ProducerManager.regions.dialog.$el.dialog({
                    modal: true,
                    width: 500,
                    height: 450,
                    title: 'Create a course in your scratch space',
                    buttons: [
                        {
                            text: "Cancel",
                            class: 'btn btn-danger',
                            click: function () {
                                $(this).dialog("close");
                            }
                        },
                        {
                            text: "Create",
                            class: 'btn btn-success',
                            click: function () {
                                // validate that at least course name and run are populated
                                var courseName = $('#newCourseName').val(),
                                    courseDesc = $('#newCourseDescription').val(),
                                    courseOffering = $('#newCourseOffering').val();

                                if (courseName === "" || courseOffering === "") {
                                    $('div.create-course-warning').removeClass('hidden');
                                } else {
                                    var newCourseComposition = new RepositoryModel(),
                                        newCourseRun = new RepositoryModel(),
                                        _this = this;

                                    newCourseComposition.set('genusTypeId', 'repository-genus-type%3Acourse-repo%40ODL.MIT.EDU');
                                    newCourseComposition.set('displayName', courseName);
                                    newCourseComposition.set('description', courseDesc);

                                    newCourseComposition.save(null, {
                                        success: function (data) {
                                            var createdCourseId = data.id,
                                                $courseOption = $('<option></option>')
                                                    .attr('value', createdCourseId)
                                                    .attr('selected', true)
                                                    .text(courseName + ' -- ' + courseDesc),
                                                $s = $('select.course-selector');

                                            // prepend this to the select.course-selector and select it
                                            $s.children('option:selected')
                                                .attr('selected', false);
                                            $courseOption.insertAfter($s.children('option[value="-1"]'));

                                            newCourseRun.set('genusTypeId', 'repository-genus-type%3Acourse-run-repo%40ODL.MIT.EDU');
                                            newCourseRun.set('displayName', courseOffering);
                                            newCourseRun.set('description', 'A single offering');
                                            newCourseRun.set('parentId', createdCourseId);

                                            newCourseRun.save(null, {
                                                success: function (data) {
                                                    // update screen
                                                    var runId = data.id;
                                                    console.log('created course and run.');
                                                    ProducerManager.navigate("edit/" + createdCourseId + '/' + runId);
                                                    ProducerManager.trigger("userCourseRun:edit", createdCourseId, runId);
                                                    $(_this).dialog('close');
                                                },
                                                error:function (xhr, status, msg) {
                                                    ProducerManager.vent.trigger('msg:error', xhr.responseText);
                                                }
                                            });
                                        },
                                        error: function (xhr, status, msg) {
                                            ProducerManager.vent.trigger('msg:error', xhr.responseText);
                                        }
                                    });
                                }
                            }
                        }
                    ]
                });
                Utils.bindDialogCloseEvents();
            }
        }
    });

    View.CreateUserCourseView = Marionette.ItemView.extend({
        template: function () {
            return _.template(CreateUserCourseTemplate)();
        }
    });

    View.CreateUserRunView = Marionette.ItemView.extend({
        template: function () {
            return _.template(CreateUserRunTemplate)();
        }
    });

    View.RunsView = Marionette.ItemView.extend({
        template: function (serializedData) {
            var preselectedId = Utils.cookie('runId');
            return _.template(RepoSelectorTemplate)({
                preselectedId: preselectedId,
                repoType: 'run',
                repos: serializedData.items
            });
        },
        onShow: function () {
            if (Utils.cookie('runId') !== '-1') {
                this.$el.find('select.run-selector')
                    .trigger('change');
            }
        },
        events: {
            'change select.run-selector' : 'renderCourseStructure'
        },
        renderCourseStructure: function (e) {
            var runId = $(e.currentTarget).val(),
                courseId = $('select.course-selector').val(),
                courseName = $('select.course-selector option:selected').text();

            if (runId === '-1') {
                return;
            }

            if (typeof courseId === 'undefined') {
                courseId = Utils.cookie('courseId');
            }

            if (runId !== 'create') {
                ProducerManager.navigate("edit/" + courseId + '/' + runId);
                require(["apps/dashboard/domains/domain_controller"], function(DomainController){
                    DomainController.renderUserCourseRun(runId);
                });
            } else {
                // bring up a modal to create the course
                ProducerManager.regions.dialog.show(new View.CreateUserRunView());
                ProducerManager.regions.dialog.$el.dialog({
                    modal: true,
                    width: 500,
                    height: 450,
                    title: 'Create a new offering in your scratch space for ' + courseName,
                    buttons: [
                        {
                            text: "Cancel",
                            class: 'btn btn-danger',
                            click: function () {
                                $(this).dialog("close");
                            }
                        },
                        {
                            text: "Create",
                            class: 'btn btn-success',
                            click: function () {
                                // validate that run name is populated
                                var courseOffering = $('#newCourseOffering').val();

                                if (courseOffering === "") {
                                    $('div.create-run-warning').removeClass('hidden');
                                } else {
                                    var newCourseRun = new RepositoryModel(),
                                        _this = this;

                                    newCourseRun.set('genusTypeId', 'repository-genus-type%3Acourse-run-repo%40ODL.MIT.EDU');
                                    newCourseRun.set('displayName', courseOffering);
                                    newCourseRun.set('description', 'A single offering');
                                    newCourseRun.set('parentId', courseId);

                                    newCourseRun.save(null, {
                                        success: function (data) {
                                            // update screen
                                            var runId = data.id;
                                            console.log('created new run.');
                                            ProducerManager.trigger("userCourseRun:edit", courseId, runId);
                                            $(_this).dialog('close');
                                        },
                                        error:function (xhr, status, msg) {
                                            ProducerManager.vent.trigger('msg:error', xhr.responseText);
                                        }
                                    });
                                }
                            }
                        }
                    ]
                });
                Utils.bindDialogCloseEvents();
            }
        }
    });

    View.CompositionsView = Marionette.CompositeView.extend({
        initialize: function () {
            this.collection = new CompositionsCollection(this.model.get('children'));
        },
        tagName: 'li',
        className: 'resortable composition list-group-item',
        template: function (serializedData) {
            var canEdit = false,
                canEditParent = true;

            if (serializedData.hasOwnProperty('canEdit')) {
                canEdit = serializedData.canEdit;
            }

            if (serializedData.type === 'Composition') {
                return _.template(CompositionsTemplate)({
                    canEdit: canEdit,
                    canEditParent: canEditParent,
                    composition: serializedData,
                    compositionType: Utils.parseGenusType(serializedData.genusTypeId),
                    exportUrl: Utils.exportUrl(serializedData),
                    rawObject: JSON.stringify(serializedData)
                });
            } else {
                return _.template(ResourceTemplate)({
                    canEdit: canEdit,
                    canEditParent: canEditParent,
                    exportUrl: Utils.exportUrl(serializedData),
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
            // prepend a hidden li.resortable.no-children chapter object
            // so can sort the chapters
            var hiddenChapter = $('<li></li>').addClass('resortable hidden composition');

            this.$el.prepend(hiddenChapter.clone());

            // init the course actions
            ProducerManager.regions.courseActions.show(new CourseActionsViews.CourseActionsView({}));

            // make the sections sortable
            $('ul.run-list').sortable({
                group: 'producer',
                handle: 'div.drag-handles',
                itemSelector: 'li.resortable:not(.no-children), li.resource, li.composition',
                pullPlaceholder: false,
                placeholderClass: 'sortable-placeholder',
                placeholder: '<li class="sortable-placeholder"></li>',
                isValidTarget: function ($item, container) {
                    return !$(container.el).hasClass('can-edit-state-false');
                },
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
                    if (container.options.drop) {
                        // if droppable, continue
                        var $preMoveObj = $item.data('pre-move-parent-obj'),
                            $newObj;

                        if ($item.hasClass('search-result')) {
                            var rawObj = $item.data('obj'),
                                $newObj = $('<li></li>').addClass('list-group-item resortable');

                            rawObj.canEdit = false;

                            if (rawObj.type === 'Composition') {
                                $newObj.addClass('composition');
                                $newObj.append(_.template(CompositionsTemplate)({
                                    canEdit: false,
                                    canEditParent: true,
                                    composition: rawObj,
                                    compositionType: Utils.parseGenusType(rawObj),
                                    exportUrl: Utils.exportUrl(rawObj),
                                    rawObject: JSON.stringify(rawObj)
                                }));
                            } else {
                                $newObj.addClass('resource');
                                $newObj.append(_.template(ResourceTemplate)({
                                    canEdit: false,
                                    canEditParent: true,
                                    exportUrl: Utils.exportUrl(rawObj),
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
                    } else {
                        $item.remove();
                        $('body').removeClass('dragging');
                    }
                }
            });
        },
        events: {
            'change .switch-genus-type': 'changeCompositionGenusType',
            'click .toggle-composition-children': 'toggleCompositionChildren',
            'click .unlock-composition': 'unlockComposition',
            'click .unlock-resource': 'unlockResource',
            'click .preview': 'previewObject',
            'click .remove-composition': 'removeObject',
            'click .remove-resource': 'removeObject'
        },
        changeCompositionGenusType: function (e) {
            var $e = $(e.currentTarget),
                $liParent = $e.parent().parent().parent().parent().parent(),
                $wrapper = $liParent.children('div.object-wrapper'),
                $icon = $wrapper.find('.content-type'),
                obj = $wrapper.data('obj'),
                objId = obj.id,
                originalGenus = Utils.parseGenusType(obj.genusTypeId),
                composition = new CompositionModel({id: objId}),
                newType = $e.val();

            composition.set('genusTypeId', Utils.genusType(newType));
            composition.save(null, {
                success: function (model, response) {
                    // now change it in the UI and update the raw object
                    $wrapper.removeClass(originalGenus)
                        .addClass(newType);
                    $icon.removeClass('badge-' + originalGenus)
                        .addClass('badge-' + newType);
                    $icon.attr('title', newType);
                    $icon.text(newType);

                    obj.genusTypeId = response.genusTypeId;

                    $wrapper.data('obj', obj);
                },
                error: function (model, response) {
                    ProducerManager.vent.trigger('msg:error', response.responseText);
                }
            });
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
                objId = rawObj.id,
                $drawer = $('#search-components-menu');

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

            if ($drawer.hasClass('open')) {
                $drawer.drawer('hide');
            }
            $('#add-new-components-btn').removeClass('active');
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
        removeObject: function (e) {
            // first destroy the composition
            // then, update the parent's childIds list
            var $e = $(e.currentTarget),
                $liParent = $e.parent().parent().parent().parent().parent(),
                $noChildrenObject = $liParent.siblings('li.no-children'),
                obj = $liParent.children('div.object-wrapper').data('obj'),
                displayName = obj.displayName.text,
                objId = obj.id;

            ProducerManager.regions.dialog.show(new View.DeleteConfirmationView({}));
            ProducerManager.regions.dialog.$el.dialog({
                modal: true,
                width: 500,
                height: 400,
                title: 'Confirm deletion of ' + displayName,
                buttons: [
                    {
                        text: "Cancel",
                        class: 'btn btn-danger',
                        click: function () {
                            $(this).dialog("close");
                        }
                    },
                    {
                        text: "Yes!",
                        class: 'btn btn-success',
                        click: function () {
                            var _this = this;

                            Utils.processing();

                            // TODO: If the item is locked, just remove it
                            // as a child...if the item is unlocked, then
                            // delete it (and have to check the children
                            // that only delete when they belong to the
                            // user...not those that belong to others)
                            if (obj.type === 'Composition' && obj.canEdit == true) {
                                var compositionModel = new CompositionModel({id: objId,
                                    withChildren: true});

                                compositionModel.destroy({
                                    data: JSON.stringify({
                                        repoId: Utils.runId()
                                    }),
                                    success: function (model, response) {
                                        $liParent.remove();
                                        updateCompositionChildrenAndAssets($noChildrenObject);
                                        $(_this).dialog("close");
                                        Utils.doneProcessing();
                                    },
                                    error: function (model, response) {
                                        ProducerManager.vent.trigger('msg:error', response.responseText);
                                        $(_this).dialog("close");
                                        Utils.doneProcessing();
                                    }
                                });
                            } else if (obj.type === 'Composition') {
                                // for a locked composition, just remove it
                                // from the UI and call updateCompositionChildrenAndAssets
                                $liParent.remove();
                                updateCompositionChildrenAndAssets($noChildrenObject);
                                $(_this).dialog("close");
                                Utils.doneProcessing();
                            } else if (obj.canEdit == true) {
                                // if is an editable Asset or Item, delete it
                                // from the service, then call updateCompositionChildrenAndAssets
//                                var compositionModel = new CompositionModel({id: objId,
//                                    withChildren: true});
//
//                                compositionModel.destroy({
//                                    data: JSON.stringify({
//                                        repoId: Utils.runId()
//                                    }),
//                                    success: function (model, response) {
//                                        $liParent.remove();
//                                        updateCompositionChildrenAndAssets($noChildrenObject);
//                                        $(_this).dialog("close");
//                                        Utils.doneProcessing();
//                                    },
//                                    error: function (model, response) {
//                                        ProducerManager.vent.trigger('msg:error', response.responseText);
//                                        $(_this).dialog("close");
//                                        Utils.doneProcessing();
//                                    }
//                                });
                            } else {
                                // if is a non-editable Asset or Item, just remove it
                                // from the UI and call updateCompositionChildrenAndAssets
                                $liParent.remove();
                                updateCompositionChildrenAndAssets($noChildrenObject);
                                $(_this).dialog("close");
                                Utils.doneProcessing();
                            }
                        }
                    }
                ]
            });
            Utils.bindDialogCloseEvents();
        },
        toggleCompositionChildren: function (e) {
            var $e = $(e.currentTarget),
                $composition = $e.closest('li.resortable.composition'),
                compositionId = $composition.children('.object-wrapper')
                    .data('obj').id,
                childrenCollection = new CompositionChildrenCollection([],
                    {id: compositionId,
                     repoId: Utils.runId()
                    }),
                $children = $composition.children('.children-compositions'),
                _this = this,
                promise;

            $children.toggleClass('hidden');
            $e.find('.children-icon').toggleClass('fa-chevron-up')
                .toggleClass('fa-chevron-down');
            $e.find('.children-action-hide').toggleClass('hidden');
            $e.find('.children-action-show').toggleClass('hidden');

            // now get the actual children of the clicked composition and
            // populate the list
            if (!$children.hasClass('hidden')) {
                promise = childrenCollection.fetch();
                promise.done(function (data) {
                    renderChildren(data.data.results, $composition);
                    _this.refreshNoChildrenWarning();
                });
            }
        },
        unlockComposition: function (e) {
            var $e = $(e.currentTarget),
                $composition = $e.parent().parent().parent().parent().parent(),  // is the <li> element
                compositionId = $composition.children('.object-wrapper')
                    .data('obj').id,
                composition = new CompositionModel({id: compositionId},
                    {repositoryId: Utils.runId()}),
                parentId;

            if ($composition.parent().hasClass('run-list')) {
                // parentId is the selected run composition
                parentId = $('select.run-selector').val();
            } else {
                // parentId is in the course structure
                parentId = $composition.parent()
                    .siblings('div.object-wrapper')
                    .data('obj').id;
            }

            composition.unlock(parentId, function (data) {
                var $newObj = $('<li></li>').addClass('list-group-item resortable composition');

                $newObj.append(_.template(CompositionsTemplate)({
                    canEdit: true,
                    canEditParent: true,
                    composition: data,
                    compositionType: Utils.parseGenusType(data),
                    exportUrl: Utils.exportUrl(data),
                    rawObject: JSON.stringify(data)
                }));
                console.log(data);

                $composition.replaceWith($newObj);
            });
        },
        unlockResource: function (e) {
            ProducerManager.vent.trigger('msg:error', "This feature is not enabled yet.");
        }
    });

    View.DeleteConfirmationView = Marionette.ItemView.extend({
        template: function () {
            return _.template(DeleteConfirmationTemplate)();
        }
    });
  });

  return ProducerManager.ProducerApp.Domain.View;
});