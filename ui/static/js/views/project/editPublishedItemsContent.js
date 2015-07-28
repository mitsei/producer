//Filename: views/project/editPublishedItemsContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'admin-utils',
    'metadata-utils',
    'tex-utils',
    'item-utils',
    'bootstrap-dialog',
    'text!templates/editPublishedItems.html',
    'text!templates/processing.html',
    'text!templates/noPublishedItemsFound.html',
    'text!templates/publishedItemTableRow.html'
], function ($, _, Backbone, Admin, Metadata, Tex, Item,
             BootstrapDialog, EditPublishedItemsTemplate,
             ProcessingTemplate, NoPublishedItemsTemplate,
             PublishedItemRowTemplate) {

    function checkItemActionStatus() {
        // check if an item is still active / selected.
        // If no visible row is active, hide the action buttons
        if ($('tr.published-item-row.active:not(.hidden)').length === 0) {
            $('section.item-actions').addClass('hidden');
            $('section.locked-warning').addClass('hidden');
            $('section.item-actions label.item-delete').addClass('hidden');
            $('tr.published-item-row.active').removeClass('active');
        }
    }

    var EditPublishedItemsContentView = Backbone.View.extend({
//        el: $('#dashboard_main_content'),
        className: 'my-subject-published-items',
        initialize: function () {
            var compiledTemplate = _.template(EditPublishedItemsTemplate);
            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);

            return this;
        },
        render: function () {
            // let's get the published items and put them into the right spots
            // also initialize the filters based on what is available
            var $itemTableBody = $('div.item-list tbody');

            Admin.processing();

            $.ajax({
                url:    Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                    '/items/?page=all'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                // just get the item names and IDs first
                // populate the table with them, and insert
                // "processing" into the unknown cells.
                // then get details of each row.
                // update the row based on a new ajax call
                //  -- update the filters with each row insert
                var processing = _.template(ProcessingTemplate);

                data = data['data']['results'];

                if (data.length > 0) {
                    // get filter values while appending data to table
                    _.each(data, function (datum) {
                        $itemTableBody.append(_.template(PublishedItemRowTemplate, {
                            description         : datum.description.text,
                            displayName         : datum.displayName.text,
                            pset                : Item.psetDisplayName(datum),
                            questionType        : Admin.questionType(datum),
                            questionDifficulty  : datum.difficulty,
                            rawObject           : Admin.rawObject(datum),
                            terms               : datum.terms.join(', ')
                        }));
                        Item.updateFilters(datum);
//                        Item.updateItemRow($itemTableBody.find('tr.published-item-row:last-child'),
//                            datum.mecqbankId);
                    });
                } else {
                    $itemTableBody.append(_.template(NoPublishedItemsTemplate));
                }

                Admin.doneProcessing();
            });

            return this;
        },
        events: {
            'click input[name="difficulty"]'        : 'toggleRows',
            'click input[name="pset"]'              : 'toggleRows',
            'click input[name="term"]'              : 'toggleRows',
            'click input[name="type"]'              : 'toggleRows',
            'click label.item-delete'               : 'deleteItem',
            'click label.item-minor-edit'           : 'minorEdit',
            'click label.item-major-edit'           : 'majorEdit',
            'click td.download-col'                 : 'downloadItem',
            'click td.metadata-col'                 : 'showMetadata',
            'click td.preview-col'                  : 'showQuestionPreview',
            'click td.solution-preview-col'         : 'showSolutionPreview',
            'click tr.published-item-row'           : 'showEditingOptions',
            'keyup input[name="keyword-search"]'    : 'searchItems'
        },
        deleteItem: function (e) {
            var $tableRow = $('tr.published-item-row.active'),
                $this = this,
                currentItem = Admin.activePublishedItem(),
                itemName = currentItem['displayName']['text'],
                url, header, method, message, cancelBtnClass, affirmBtnClass;

            method = 'DELETE';
            header = 'Delete ' + itemName;
            message = 'Are you sure you want to delete ' + itemName + '? ' +
                     'If you change your mind later, you will have to re-upload it ' +
                     'and a new serial number will be assigned.';
            url = Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + Admin.activePublishedItemId() + '/';
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
                                $this.toggleRows();
                                checkItemActionStatus();
                                dialog.close();
                            });
                        }
                    }
                ]
            });
        },
        downloadItem: function (e) {
            e.stopImmediatePropagation();

            var $e = $(e.currentTarget),
                rawObject = $e.parent().data('raw-object'),
                itemId = rawObject['mecqbankId'],
                subjectId = Admin.activeSubjectId(),
                url = Admin.api() + 'subjects/' + subjectId + '/items/' + itemId + '/download/';

            window.open(url, '_blank');
        },
        majorEdit: function (e) {
            var rawObject = Admin.activePublishedItem();

            Item.majorEdit(rawObject);
        },
        minorEdit: function (e) {
            var rawObject = Admin.activePublishedItem();

            Item.minorEdit(rawObject);
        },
        searchItems: function (e) {
            // Filter the rows by both Serial Number and keywords columns
            var $allItems = $('tr.published-item-row'),
                $searchInput = $('input[name="keyword-search"]');
            Item.searchRows($allItems, $searchInput, checkItemActionStatus);
        },
        showEditingOptions: function (e) {
            var rawObject = $(e.currentTarget).data('raw-object');
            $('tr.published-item-row.active').removeClass('active');
            $(e.currentTarget).addClass('active');

            if (rawObject.locked) {
                $('section.item-actions').addClass('hidden');
                $('section.item-actions label.item-delete').addClass('hidden');
                $('section.locked-warning').removeClass('hidden');
            } else {
                $('section.item-actions').removeClass('hidden');
                $('section.locked-warning').addClass('hidden');

                if (!rawObject.isUsed) {
                    $('section.item-actions label.item-delete').removeClass('hidden');
                } else {
                    $('section.item-actions label.item-delete').addClass('hidden');
                }
            }
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
                    Admin.updateStatus('No preview file available.')
                }
            });
        },
        toggleRows: function (e) {
            // this needs to check all the filter boxes...not just one passed
            // in attribute...
            var $allItems = $('tr.published-item-row');
            Item.toggleFromFilters($allItems, checkItemActionStatus);
        }
    });

    return EditPublishedItemsContentView;
});