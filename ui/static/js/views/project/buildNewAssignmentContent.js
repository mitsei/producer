//Filename: views/project/buildNewAssignmentContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'admin-utils',
    'assignment-utils',
    'item-utils',
    'metadata-utils',
    'bootstrap-dialog',
    'text!templates/buildAssignment.html',
    'text!templates/processing.html',
    'text!templates/noAssignmentsFound.html',
    'text!templates/assignmentName.html',
    'text!templates/assignmentItemTableRow.html',
    'text!templates/noAssignmentItemsFound.html',
    'text!templates/assignmentItemsTableHeader.html',
    'text!templates/assignmentActions.html',
    'text!templates/filePreview.html',
    'text!templates/addAssignment.html',
    'text!templates/addAssignmentForm.html',
    'text!templates/addItemsToAssignments.html',
    'text!templates/availableItemRow.html',
    'text!templates/noAvailableItemsFound.html',
    'text!templates/filterCheckboxRow.html',
    'text!templates/uploadNewItemVersionSelector.html',
    'bootstrap-switch'
], function ($, _, Backbone, Admin, Assignment, Item, Metadata,
             BootstrapDialog,
             BuildAssignmentTemplate, ProcessingTemplate,
             NoAssignmentsFoundTemplate, AssignmentNameTemplate,
             AssignmentItemRowTemplate, NoAssignmentItemsFoundTemplate,
             AssignmentItemsTableHeaderTemplate, AssignmentActionsTemplate,
             FilePreviewTemplate, AddAssignmentBtnTemplate, AddAssignmentFormTemplate,
             AddItemsToAssignmentsTemplate, AvailableItemRowTemplate,
             NoAvailableItemsTemplate, FilterCheckboxRowTemplate,
             UploadNewItemVersionSelectorTemplate) {

    function addItemToAssignmentTable ($t, item, assignmentPublished, assignmentLocked) {
        var psetTypes = [],
            questionType = Admin.questionType(item),
            difficulty = item['difficulty'];

        if (item['psets'].length > 0) {
            _.each(item['psets'], function (pset) {
                var psetName = Admin.toTitle(pset.split(' ')[0]);
                if (psetName === 'Nil') {
                    psetName = 'Generic Bucket';
                }
                psetTypes.push(psetName);
            });
        }

        $t.append(_.template(AssignmentItemRowTemplate, {
            description: item['description']['text'],
            displayName: item['displayName']['text'],
            locked: assignmentLocked,
            pset: psetTypes.join(', '),
            published: assignmentPublished,
            questionType: questionType,
            questionDifficulty: difficulty,
            rawObject: Admin.rawObject(item),
            terms: item['terms'].join(', ')
        }));
    }

    function clearAvailableItems() {
        // check if an item is still active / selected.
        // If no visible row is active, hide the action buttons
        if ($('tr.available-item-row.active:not(.hidden)').length === 0) {
            $('tr.available-item-row.active').removeClass('active');
            $('tr.available-item-row.hidden input.add-item-checkbox').prop('checked', false);
        }
    }

    function loadItemsIntoModal ($m, items) {
        var $t = $m.find('tbody'),
            availablePsets = [],
            availableTerms = [],
            availableTypes = [],
            availableDifficulties = [],
            availableBranches = [],
            includeNonePsetOption = false,
            includeNoneTermOption = false,
            $psetFilter = $m.find('div.pset-filter'),
            $difficultyFilter = $m.find('div.difficulty-filter'),
            $typesFilter = $m.find('div.types-filter'),
            $branchFilter = $m.find('div.branches-filter'),
            $yearSlider = $m.find('input.year-slider'),
            $yearSliderText = $m.find('div.year-selected-text'),
            $yearControl = $m.find('div.year-slider-control'),
            oldestTerm, oldestTermYearsAgo;

        if (items.length > 0) {
            // get filter values while appending data to table
            _.each(items, function (item) {
                var psetTypes = [],
                    questionType = Admin.questionType(item),
                    difficulty = item['difficulty'],
                    itemId = item.mecqbankId,
                    $thisItem, $thisItemPreview, $thisItemSolutionPreview;

                if (item['branches'].length > 0) {
                    _.each(item['branches'], function (branch) {
                        if (availableBranches.indexOf(branch) < 0) {
                            availableBranches.push(branch);
                        }
                    });
                }

                if (item['subbranches'].length > 0) {
                    _.each(item['subbranches'], function (subbranch) {
                        if (availableBranches.indexOf(subbranch) < 0) {
                            availableBranches.push(subbranch);
                        }
                    });
                }

                if (item['psets'].length > 0) {
                    _.each(item['psets'], function (pset) {
                        var psetName = Admin.toTitle(pset.split(' ')[0]);

                        if (psetName === 'Nil') {
                            psetName = 'Generic Bucket';
                        }

                        psetTypes.push(psetName);

                        if (availablePsets.indexOf(psetName) < 0) {
                            availablePsets.push(psetName);
                        }
                    });
                } else {
                    includeNonePsetOption = true;
                }

                if (item['terms'].length > 0) {
                    _.each(item['terms'], function (term) {
                        if (availableTerms.indexOf(term) < 0) {
                            availableTerms.push(term);
                        }
                    });
                } else {
                    includeNoneTermOption = true;
                }

                if (availableTypes.indexOf(questionType) < 0) {
                    availableTypes.push(questionType);
                }

                if (availableDifficulties.indexOf(difficulty) < 0) {
                    availableDifficulties.push(difficulty);
                }

                $thisItem = _.template(AvailableItemRowTemplate, {
                    description         : item['description']['text'],
                    displayName         : item['displayName']['text'],
                    locked              : item.locked,
                    pset                : psetTypes.join(', '),
                    questionType        : questionType,
                    questionDifficulty  : difficulty,
                    rawObject           : Admin.rawObject(item),
                    terms               : item['terms'].join(', ')
                });
                $t.append($thisItem);

                $thisItemPreview = $t.children()
                    .last()
                    .find('td.preview-col');

                $thisItemSolutionPreview = $t.children()
                    .last()
                    .find('td.solution-preview-col');

                // get the question preview for each file
                $thisItemPreview.on('click', function () {
                    Admin.updateStatus(_.template(ProcessingTemplate));

                    $.ajax({
                        url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + itemId + '/preview/'
                    }).error(function (xhr, msg, status) {
                        Admin.updateStatus('Server error: ' + xhr.responseText);
                    }).success(function (data) {
                        if (data !== "") {
                            Admin.updateStatus('');
                            Item.showPreview('', data, true);
                        } else {
                            Admin.updateStatus('No solution preview file available.')
                        }
                    });
                });

                // get the solution preview for each file
                $thisItemSolutionPreview.on('click', function () {
                    Admin.updateStatus(_.template(ProcessingTemplate));

                    $.ajax({
                        url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + itemId + '/solutionpreview/'
                    }).error(function (xhr, msg, status) {
                        Admin.updateStatus('Server error: ' + xhr.responseText);
                    }).success(function (data) {
                        if (data !== "") {
                            Admin.updateStatus('');
                            Item.showPreview('', data, true);
                        } else {
                            Admin.updateStatus('No solution preview file available.')
                        }
                    });
                });
            });

            // sort the filter lists
            availableTerms = _.chain(availableTerms)
                .sortBy(function (term) {
                    return term.split(' ')[0];
                }).sortBy(function (term) {
                    return parseInt(term.split(' ')[1]);
                });

            if (includeNoneTermOption) {
                availableTerms.push('None');
            }

            availablePsets.sort();

            if (includeNonePsetOption) {
                availablePsets.push('None');
            }

            availableDifficulties.sort();
            availableTypes.sort();
            availableBranches.sort();

            // now append the filters to the right sections
            oldestTerm = availableTerms.first().value();
            oldestTermYearsAgo = Admin.termTimeFromNow(oldestTerm);

            $('input.inclusive-years').removeClass('hidden')
                .bootstrapSwitch({
                    onText          : 'Incl.',
                    offText         : 'Excl.',
                    onSwitchChange  : function (e, state) {
                        Item.toggleFromFilters($m.find('tr.available-item-row'),
                                    clearAvailableItems);
                    }
            });
            // minimum year == 0
            // maximum year == "today" - oldest term

            $yearControl.removeClass('hidden')
                .slider({
                    min     : 0,
                    max     : oldestTermYearsAgo,
                    value   : oldestTermYearsAgo,
                    step    : 0.5,
                    slide   : function (e, ui) {
                        $yearSlider.val(ui.value)
                            .trigger('input');
                        $yearSliderText.text('0 -to- ' + ui.value + ' years ago')
                    }
                });
            $yearSlider.val(oldestTermYearsAgo);
            $yearSliderText.text('0 -to- ' + oldestTermYearsAgo + ' years ago');

            _.each(availableBranches, function (branch) {
                $branchFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : branch,
                    attrType        : 'branch'
                }));
            });

            _.each(availablePsets, function (pset) {
                $psetFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : pset,
                    attrType        : 'pset'
                }));
            });

            _.each(availableDifficulties, function (difficulty) {
                $difficultyFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : difficulty,
                    attrType        : 'difficulty'
                }));
            });

            _.each(availableTypes, function (type) {
                $typesFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : type,
                    attrType        : 'type'
                }));
            });
        } else {
            $t.append(_.template(NoAvailableItemsTemplate));
        }
    }

    function reportError (xhr) {
        Admin.updateStatus('Server error: ' + xhr.responseText);
    }

    var BuildAssignmentContentView = Backbone.View.extend({
//        el: $('#dashboard_main_content'),
        className: 'my-subject-build-assignment',
        initialize: function () {
            var compiledTemplate = _.template(BuildAssignmentTemplate),
                _this = this;
            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);

            // pre-load the items so they are cached...
            this.allItems = null;

            this.preloadItems();

            return this;
        },
        render: function () {
            var $assignmentNamesList = $('ul.assignment-names');
            Admin.updateStatus(_.template(ProcessingTemplate));
            $.ajax({
                url:    Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/?page=all'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                data = data['data']['results'];

                if (data.length > 0) {
                    // sort by year, then term, then name
                    data = _.chain(data)
                        .sortBy(function (datum) {
                            return datum.displayName.text;
                        }).sortBy(function (datum) {
                            return datum.term.split(' ')[0];
                        }).sortBy(function (datum) {
                            return parseInt(datum.term.split(' ')[1]);
                        });

                    data.each(function (datum) {
                        var displayName = datum['displayName']['text'],
                            assignmentId = datum.mecqbankId;

                        // unlock all assignments that this user may have inadvertently
                        // locked (i.e. if they refresh the page)
                        if (!datum.locked) {
                            Assignment.unlock(assignmentId, true);
                        }

                        if (displayName.toLowerCase() === 'nil') {
                            displayName = 'Generic Bucket -- ' + datum['term'];
                        } else {
                            displayName = displayName + ' -- ' + datum['term'];
                        }
                        $assignmentNamesList.append(_.template(AssignmentNameTemplate, {
                            displayName: displayName,
                            locked  : datum.locked,
                            published   : datum.published,
                            rawObject: Admin.rawObject(datum)
                        }));
                    });
                } else {
                    $assignmentNamesList.append(_.template(NoAssignmentsFoundTemplate));
                }

                // append the + Assignment button
                $assignmentNamesList.append(_.template(AddAssignmentBtnTemplate));
                Admin.updateStatus('');
            });

            return this;
        },
        events: {
            'click .download-assignment'            : 'downloadAssignment',
            'click label.add-item'                  : 'addItem',
            'click label.delete-assignment'         : 'deleteAssignment',
            'click label.publish-assignment'        : 'publishAssignment',
            'click li.add-new-assignment'           : 'addAssignment',
            'click li.assignment-name'              : 'showAssignmentDetails',
            'click td.delete-col'                   : 'removeItem',
            'click td.metadata-col'                 : 'showMetadata',
            'click td.preview-col'                  : 'showQuestionPreview',
            'click td.solution-preview-col'         : 'showSolutionPreview',
            'click td.upload-col'                   : 'uploadNewItemVersion',
            'keyup input[name="keyword-search"]'    : 'searchAssignments'
        },
        addAssignment: function (e) {
            BootstrapDialog.show({
                title: 'Create a new assignment',
                message: _.template(AddAssignmentFormTemplate),
                onshow: function (dialog) {
                    var $m = dialog.$modalBody;
                    Admin.removeBRs($m);

                    $m.find('select[name="termSelector"]').select2({
                        dropdownAutoWidth: 'true'
                    });

                    $m.find('select[name="psetSelector"]').select2({
                        dropdownAutoWidth: 'true'
                    });
                },
                buttons: [
                    {
                        label: 'Cancel',
                        cssClass: 'btn-danger',
                        action: function (dialog) {
                            dialog.close();
                        }
                    },{
                        label: 'Create',
                        cssClass: 'btn-success',
                        action: function (dialog) {
                            var assignmentForm = new FormData(),
                                $m = dialog.$modalBody,
                                year = $m.find('input[name="yearSelector"]').val(),
                                termName = $m.find('select[name="termSelector"]').val(),
                                assignmentType = $m.find('select[name="psetSelector"]').val(),
                                assignmentNum = $m.find('input[name="psetNumberSelector"]').val(),
                                term, assessment;

                            if (year === '' || termName === '' ||
                                assignmentType === '' || assignmentNum === '') {
                                Admin.updateStatus('Please provide all information.');
                            } else {
                                term = termName + ', ' + year;
                                assessment = assignmentType + ', ' + assignmentNum;
                                assignmentForm.append('term', term);
                                assignmentForm.append('assessment', assessment);
                                Assignment.createAssessmentAjax(assignmentForm,
                                    reportError,
                                    function (data) {
                                        $('#dashboard_content_navbar').find('button.active')
                                            .click();
                                        dialog.close();
                                    });
                            }
                        }
                    }
                ]
            });
        },
        addItem: function (e) {
            var _this = this,
                assignmentObj = Admin.activeAssignment(),
                assignmentName = assignmentObj.displayName.text + ' -- ' + assignmentObj.term,
                assignmentId = assignmentObj.mecqbankId,
                $itemsTable = $('div.assignment-items tbody'),
                assignmentLocked = assignmentObj.locked,
                assignmentPublished = assignmentObj.published,
                assignmentTerm = assignmentObj.term,
                assignmentType = assignmentObj.displayName.text;

            // Here is the interesting part...let users search through all items
            // in the course, with various topic / time related filters

            // Do NOT show the ones that are already in the assignment

            Admin.processing();
            this.preloadAllItems.done(function () {
                Admin.doneProcessing();
                console.log(_this.allItems);

                BootstrapDialog.show({
                    title: 'Add new item(s) to ' + assignmentName,
                    message: _.template(AddItemsToAssignmentsTemplate),
                    cssClass: 'add-items-modal extra-wide',
                    onshow: function(dialog) {
                        var $m = dialog.$modalBody;

                        dialog.setSize(BootstrapDialog.SIZE_WIDE);
                        Admin.removeBRs($m);
                    },
                    onshown: function (dialog) {
                        var $m = dialog.$modalBody,
                            itemsCurrentInAssignment = $('tr.assignment-item-row').map(function () {
                                return $(this).data('raw-object');
                            }),
                            itemIdsInAssignment = _.pluck(itemsCurrentInAssignment, 'mecqbankId'),
                            filteredItems = _.filter(_this.allItems, function (item) {
                                return itemIdsInAssignment.indexOf(item.mecqbankId) < 0;
                            });


                        loadItemsIntoModal($m, filteredItems);

                        Item.toggleFromFilters($m.find('tr.available-item-row'),
                                clearAvailableItems);

                        $m.find('input.filter-input-checkbox')
                            .on('click', function () {
                                Item.toggleFromFilters($m.find('tr.available-item-row'),
                                    clearAvailableItems);
                            });

                        // bind the text search box
                        $m.find('input[name="keyword-search"]')
                            .on('keyup', function () {
                                Item.searchRows($m.find('tr.available-item-row'),
                                    $(this),
                                    clearAvailableItems);
                            });

                        // bind the year selector
                        $m.find('input.year-slider')
                            .on('input', function () {
                                Item.toggleFromFilters($m.find('tr.available-item-row'),
                                    clearAvailableItems);
                            });
                    },
                    buttons: [
                        {
                            label: 'Cancel',
                            cssClass: 'btn-danger',
                            action: function (dialog) {
                                dialog.close();
                            }
                        },{
                            label: 'Save',
                            cssClass: 'btn-success',
                            action: function (dialog) {
                                // Link selected Items to the assignment...
                                // refresh the assignment items table
                                // close the dialog
                                var $m = dialog.$modalBody,
                                    selectedItems = $m.find('input.add-item-checkbox:checked'),
                                    numItems = selectedItems.length;

                                if (numItems > 0) {
                                    // remove the None Found row, if present
                                    $itemsTable.find('tr.danger').remove();

                                    _.each(selectedItems, function (item) {
                                        var itemObj = $(item).parents('tr.available-item-row').data('raw-object'),
                                            itemId = itemObj.mecqbankId,
                                            addItemForm = new FormData();

                                        addItemForm.append('itemId', itemId);
                                        Item.attachItemToAssessmentAjax(addItemForm,
                                            assignmentId,
                                            Admin.reportError,
                                            function (data) {
                                                // need to update the item's .terms and .pset
                                                // to include this assignment
                                                itemObj.terms.push(assignmentTerm);
                                                itemObj.psets.push(assignmentType);

                                                addItemToAssignmentTable($itemsTable,
                                                    itemObj,
                                                    assignmentPublished,
                                                    assignmentLocked);
                                                --numItems;
                                                if (numItems === 0) {
                                                    dialog.close();
                                                    _this.preloadItems();
                                                }
                                            });
                                    });
                                } else {
                                    dialog.close();
                                    Admin.updateStatus('No items added.');
                                }
                            }
                        }
                    ]
                });
            });
        },
        deleteAssignment: function (e) {
            var assignmentId = Admin.activeAssignmentId(),
                assignmentObj = Admin.activeAssignment(),
                assignmentName = assignmentObj.displayName.text + ' -- ' + assignmentObj.term;

            BootstrapDialog.show({
                title: 'Delete assignment: ' + assignmentName,
                message: 'Are you sure you want to delete assignment ' + assignmentName + '? ' +
                         'This action cannot be undone...the items will still be available to ' +
                         'other assignments, but you will not be able to recover this one.',
                buttons: [
                    {
                        label: 'Cancel (NO!)',
                        cssClass: 'btn-primary',
                        action: function (dialog) {
                            dialog.close();
                        }
                    },{
                        label: 'Yes, I\'m sure!',
                        cssClass: 'btn-danger',
                        action: function (dialog) {
                            $.ajax({
                                type    : 'DELETE',
                                url     : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' +
                                          Admin.activeAssignmentId() + '/'
                            }).error( function(xhr, status, msg) {
                                Admin.updateStatus('Server error: ' + xhr.responseText);
                            }).success( function (data) {
                                Admin.updateStatus('');
                                $('#dashboard_content_navbar').find('button.active')
                                    .click();
                                dialog.close();
                            });
                        }
                    }
                ]
            });
        },
        downloadAssignment: function (e) {
            var assignmentId = Admin.activeAssignmentId(),
                subjectId = Admin.activeSubjectId(),
                url = Admin.api() + 'subjects/' + subjectId + '/assessments/' + assignmentId + '/download/';

            window.open(url, '_blank');
        },
        preloadItems: function () {
            var _this = this;
            this.preloadAllItems = $.ajax({
                url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/?published&page=all'
            }).error(function (xhr, status, msg) {
                Admin.updateStatus('Unable to load items...you will only be able to ' +
                    'download published assignments.');
            }).success(function (data) {
                _this.allItems = data['data']['results'];
            });
            return this;
        },
        publishAssignment: function (e) {
            var assignmentId = Admin.activeAssignmentId(),
                assignmentObj = Admin.activeAssignment(),
                assignmentName = assignmentObj.displayName.text + ' -- ' + assignmentObj.term,
                url, header, method, message, cancelBtnClass, affirmBtnClass;

            method = 'PATCH';
            header = 'Publish ' + assignmentName + '?';
            message = 'Are you sure you want to publish assignment ' + assignmentName + '? ' +
                      'It will be frozen in time -- you will only be able to download a copy of ' +
                      'the problems, and will not be able to change anything.';
            url = Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' +
                Admin.activeAssignmentId() + '/publish/';
            cancelBtnClass = 'btn-primary';
            affirmBtnClass = 'btn-warning';

            BootstrapDialog.show({
                title: header,
                message: message,
                buttons: [
                    {
                        label: 'Cancel (NO!)',
                        cssClass: cancelBtnClass,
                        action: function (dialog) {
                            dialog.close();
                        }
                    },{
                        label: 'Yes, I\'m sure!',
                        cssClass: affirmBtnClass,
                        action: function (dialog) {
                            $.ajax({
                                type    : method,
                                url     : url
                            }).error( function(xhr, status, msg) {
                                Admin.updateStatus('Server error: ' + xhr.responseText);
                            }).success( function (data) {
                                Admin.updateStatus('Assignment published.');

                                // Update the UI / show the published icon?
                                $('#dashboard_content_navbar').find('button.active')
                                    .click();
                                dialog.close();
                            });
                        }
                    }
                ]
            });
        },
        removeItem: function (e) {
            var _this = this,
                $tableRow = $(e.currentTarget).parents('tr'),
                currentItem = $tableRow.data('raw-object'),
                itemName = currentItem.displayName.text,
                itemId = currentItem.mecqbankId,
                $assignmentItems = $('div.assignment-items tbody'),
                url, header, method, message, cancelBtnClass, affirmBtnClass;

            method = 'DELETE';
            header = 'Remove ' + itemName;
            message = 'Are you sure you want to remove ' + itemName + ' from this assignment?';
            url = Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' +
                Admin.activeAssignmentId() + '/items/' + itemId + '/';
            cancelBtnClass = 'btn-primary';
            affirmBtnClass = 'btn-danger';

            BootstrapDialog.show({
                title: header,
                message: message,
                buttons: [
                    {
                        label: 'Cancel (NO!)',
                        cssClass: cancelBtnClass,
                        action: function (dialog) {
                            dialog.close();
                        }
                    },{
                        label: 'Yes, I\'m sure!',
                        cssClass: affirmBtnClass,
                        action: function (dialog) {
                            $.ajax({
                                type    : method,
                                url     : url
                            }).error( function(xhr, status, msg) {
                                Admin.updateStatus('Server error: ' + xhr.responseText);
                            }).success( function (data) {
                                $tableRow.remove();
                                _this.preloadItems();
                                dialog.close();
                                if ($assignmentItems.children().length === 0) {
                                    $assignmentItems.append(_.template(NoAssignmentItemsFoundTemplate, {
                                        locked      : false,  // because if either of these were true,
                                        published   : false   // you wouldn't have been able to remove an item!
                                    }));
                                }
                            });
                        }
                    }
                ]
            });
        },
        searchAssignments: function (e) {
            // Filter the rows by both Serial Number and keywords columns
            var $allAssignments = $('li.assignment-name'),
                allSearchWords = $('input[name="keyword-search"]').val().trim().split(' ');

            if (allSearchWords.length === 1 && allSearchWords[0] === "") {
                _.each($allAssignments, function (assignment) {
                    $(assignment).removeClass('hidden');
                });
            } else {
                _.each($allAssignments, function (assignment) {
                    var $a = $(assignment),
                        assignmentWords = $a.find('span.display-name')
                            .text()
                            .toLowerCase()
                            .split(' ');

                    if (!_.some(allSearchWords, function (searchWord) {
                        return _.some(assignmentWords, function (assignmentWord) {
                            return assignmentWord.indexOf(searchWord) >= 0;
                        });
                    })) {
                        $a.addClass('hidden');
                    } else {
                        $a.removeClass('hidden');
                    }
                });
            }
        },
        showAssignmentDetails: function (e) {
            var $e = $(e.currentTarget),
                assignmentData = $e.data('raw-object'),
                assignmentLocked = assignmentData.locked,
                assignmentPublished = assignmentData.published,
                assignmentId = assignmentData['mecqbankId'],
                $assignmentDetailsWrapper = $('div.assignment-details-wrapper'),
                $assignmentActionsWrapper = $('section.assignment-actions'),
                $assignmentItems = $('div.assignment-items'),
                $assignmentTableHeader  = $assignmentItems.find('thead'),
                $assignmentTableBody = $('div.assignment-items tbody');


            // unlock other assignments if not already locked (because it
            // will only show locked if someone else locks it, not this user)
            $('li.assignment-name.active').each(function() {
                var myRawObject = $(this).data('raw-object');
                if (!myRawObject.locked) {
                    Assignment.unlock(myRawObject.mecqbankId);
                }
            });
            $('li.assignment-name').removeClass('active');

            // lock this assignment
            if (!assignmentLocked) {
                Assignment.lock(assignmentId);
            }
            $e.addClass('active');

            $assignmentDetailsWrapper.addClass('hidden');
            $assignmentActionsWrapper.addClass('hidden');
            $assignmentItems.addClass('hidden');
            $assignmentTableBody.empty();
            $assignmentTableHeader.empty();
            $assignmentActionsWrapper.empty();

            Admin.updateStatus(_.template(ProcessingTemplate));

            $.ajax({
                url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' + assignmentId + '/items/'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                data = data['data']['results'];

                $assignmentTableHeader.append(_.template(AssignmentItemsTableHeaderTemplate, {
                    locked      : assignmentLocked,
                    published   : assignmentPublished
                }));

                $assignmentActionsWrapper.append(_.template(AssignmentActionsTemplate, {
                    locked      : assignmentLocked,
                    published   : assignmentPublished
                }));

                if (data.length > 0) {
                    // put in right table headers and action buttons
                    _.each(data, function (datum) {
                        addItemToAssignmentTable($assignmentTableBody,
                            datum,
                            assignmentPublished,
                            assignmentLocked);
                    });
                } else {
                    $assignmentTableBody.append(_.template(NoAssignmentItemsFoundTemplate, {
                        locked      : assignmentLocked,
                        published   : assignmentPublished
                    }));
                }
                $assignmentItems.removeClass('hidden');
                $assignmentDetailsWrapper.removeClass('hidden');

                if (!assignmentLocked) {
                    $assignmentActionsWrapper.removeClass('hidden');
                }

                Admin.updateStatus('');
            });
        },
        showMetadata: function (e) {
            e.stopImmediatePropagation();

            var $e = $(e.currentTarget),
                rawObject = $e.parent().data('raw-object'),
                itemName = rawObject['displayName']['text'];

            BootstrapDialog.show({
                title: 'Metadata for ' + itemName,
                message: '<div class="metadata-wrapper"></div>',
                cssClass: 'file-preview-modal',
                onshow: function(dialog) {
                    var $target = dialog.$modalBody.find('div.metadata-wrapper');
                    Metadata.render($target, rawObject);
//                    dialog.setSize(BootstrapDialog.SIZE_WIDE);
                },
                buttons: [
                    {
                        label: 'Close',
                        cssClass: 'btn-primary',
                        action: function (dialog) {
                            dialog.close();
                        }
                    }
                ]
            });
        },
        showQuestionPreview: function (e) {
            e.stopImmediatePropagation();

            var $e = $(e.currentTarget),
                rawObject = $e.parent().data('raw-object'),
                itemId = rawObject['mecqbankId'],
                itemName = rawObject['displayName']['text'];

            Admin.updateStatus(_.template(ProcessingTemplate));

            $.ajax({
                url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + itemId + '/preview/'
            }).error(function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success(function (data) {
                if (data !== "") {
                    Admin.updateStatus('');
                    Item.showPreview(itemName, data);
                } else {
                    Admin.updateStatus('No preview file available.')
                }
            });
        },
        showSolutionPreview: function (e) {
            e.stopImmediatePropagation();

            var $e = $(e.currentTarget),
                rawObject = $e.parent().data('raw-object'),
                itemId = rawObject['mecqbankId'],
                itemName = rawObject['displayName']['text'];

            Admin.updateStatus(_.template(ProcessingTemplate));

            $.ajax({
                url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + itemId + '/solutionpreview/'
            }).error(function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success(function (data) {
                if (data !== "") {
                    Admin.updateStatus('');
                    Item.showPreview(itemName, data);
                } else {
                    Admin.updateStatus('No solution preview file available.')
                }
            });
        },
        uploadNewItemVersion: function (e) {
            var _this = this,
                $e = $(e.currentTarget),
                $item = $e.parents('tr.assignment-item-row')
                    .data('raw-object'),
                itemId = $item.mecqbankId,
                itemName = $item.displayName.text;

            BootstrapDialog.show({
                title: 'Upload new version of ' + itemName,
                message: _.template(UploadNewItemVersionSelectorTemplate),
                onshow: function(dialog) {
                    var $m = dialog.$modalBody;
                    Admin.removeBRs($m);
                },
                onshown: function (dialog) {
                    // bind the button click events here
                    var $m = dialog.$modalBody;

                    $m.find('button.minor-item-edit')
                        .on('click', function () {
                            dialog.close();
                            Item.minorEdit($item);
                        });

                    $m.find('button.major-item-edit')
                        .on('click', function () {
                            dialog.close();
                            Item.majorEdit($item);
                        });
                },
                buttons: [
                    {
                        label: 'Cancel',
                        cssClass: 'btn-warning',
                        action: function (dialog) {
                            dialog.close();
                        }
                    }
                ]
            });
        }
    });

    return BuildAssignmentContentView;
});