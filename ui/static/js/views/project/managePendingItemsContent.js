//Filename: views/project/managePendingItemsContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'admin-utils',
    'metadata-utils',
    'bootstrap-dialog',
    'text!templates/managePendingItems.html',
    'text!templates/itemSerialNumber.html',
    'text!templates/processing.html',
    'text!templates/itemFile.html',
    'text!templates/filePreview.html',
    'text!templates/noItemSerialNumbersFound.html'
], function ($, _, Backbone, Admin, Metadata, BootstrapDialog,
             ManagePendingItemsTemplate, ItemSerialNumberTemplate,
             ProcessingTemplate, ItemFileTemplate,
             FilePreviewTemplate, NoItemSerialNumbersFoundTemplate) {

    function changePendingItemStatus(newStatus) {
        var currentItem = Admin.activeItem(),
                itemName = currentItem['displayName']['text'],
                $filesWrapper = $('section.files-section'),
                $filesContent = $('span.files-section-content'),
                $metadataWrapper = $('section.metadata-section'),
                $metadataContent = $('ul.metadata-section-content'),
                $itemActionsWrapper = $('section.item-actions'),
                url, header, method, message, cancelBtnClass, affirmBtnClass;

        if (newStatus.toLowerCase() === 'delete') {
            method = 'DELETE';
            header = 'Delete ' + itemName;
            message = 'Are you sure you want to delete ' + itemName + '? ' +
                     'If you change your mind later, you will have to re-upload it ' +
                     'and a new serial number will be assigned.';
            url = Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + Admin.activeItemId() + '/';
            cancelBtnClass = 'btn-primary';
            affirmBtnClass = 'btn-danger';
        } else if (newStatus.toLowerCase() === 'publish') {
            method = 'PATCH';
            header = 'Publish ' + itemName;
            message = 'Are you sure you want to publish ' + itemName + '? ' +
                     'It will become available for using in assessments, in your course.';
            url = Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + Admin.activeItemId() + '/publish/';
            cancelBtnClass = 'btn-warning';
            affirmBtnClass = 'btn-success';
        }

        BootstrapDialog.show({
            title: header,
            message: message,
            onshow: function(dialog) {
//                    dialog.setSize(BootstrapDialog.SIZE_WIDE);
            },
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
                            // remove the item from the SN list and
                            // the details from the panel
                            $filesWrapper.addClass('hidden');
                            $filesContent.empty();
                            $metadataWrapper.addClass('hidden');
                            $metadataContent.empty();
                            $itemActionsWrapper.addClass('hidden');

                            Admin.activeItemRemoveFromUI();

                            dialog.close();
                        });
                    }
                }
            ]
        });
    }

    var ManagePendingItemsContentView = Backbone.View.extend({
//        el: $('#dashboard_main_content'),
        className: 'my-subject-pending-items',
        initialize: function () {
            var compiledTemplate = _.template(ManagePendingItemsTemplate);
            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);

            return this;
        },
        render: function () {
            var $itemSNList = $('ul.item-serial-numbers');
            Admin.updateStatus(_.template(ProcessingTemplate));
            $.ajax({
                url:    Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/?pending&simple&page=all'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                data = data['data']['results'];

                if (data.length > 0) {
                    _.each(data, function (datum) {
                        $itemSNList.append(_.template(ItemSerialNumberTemplate, {
                            displayName: datum['displayName']['text'],
                            rawObject: Admin.rawObject(datum)
                        }));
                    });
                } else {
                    $itemSNList.append(_.template(NoItemSerialNumbersFoundTemplate));
                }

                Admin.updateStatus('');
            });

            return this;
        },
        events: {
            'click label.delete-pending-item'   : 'deleteItem',
            'click label.publish-pending-item'  : 'publishItem',
            'click li.item-serial-number'       : 'fetchItemDetails',
            'click span.item-file-preview'      : 'previewItemFile'
        },
        deleteItem: function (e) {
            changePendingItemStatus('delete');
        },
        fetchItemDetails: function (e) {
            var $e = $(e.currentTarget),
                itemData = $e.data('raw-object'),
                $filesWrapper = $('section.files-section'),
                $filesContent = $('span.files-section-content'),
                $metadataWrapper = $('section.metadata-section'),
                $metadataContent = $('ul.metadata-section-content'),
                $itemActionsWrapper = $('section.item-actions');

            $('li.item-serial-number').removeClass('active');
            $e.addClass('active');

            $filesWrapper.addClass('hidden');
            $filesContent.empty();
            $metadataWrapper.addClass('hidden');
            $metadataContent.empty();
            $itemActionsWrapper.addClass('hidden');

            Admin.updateStatus(_.template(ProcessingTemplate));

            $.ajax({
                url: Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + Admin.activeItemId() + '/'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                if (!data.hasOwnProperty("id")) {
                    Admin.updateStatus('Bad data returned...');
                    console.log(data);
                } else {
                    var files = data['files'];
                    _.each(files, function (fileUrl, fileName) {
                        var latex = false,
                            sourceType = 'remote',
                            fileLabel;
                        // re-format Image files so the filename
                        // looks as original
                        if (fileName.indexOf('image_') >= 0) {
                            fileLabel = fileName.replace('image_', '')
                                .replace('_pdf', '.pdf');
                        } else if (fileName.indexOf('metadata') >= 0) {
                            return;  // ignore metadata file because we are showing the actual values below
                        } else {
                            fileLabel = Admin.toTitle(fileName);
                        }

                        $filesContent.append(_.template(ItemFileTemplate, {
                            fileLabel       : fileLabel,
                            itemSource      : fileUrl,
                            latex           : latex,
                            sourceType      : sourceType
                        }));
                    });

                    // also handle latex and solutionLatex as files
                    $filesContent.append(_.template(ItemFileTemplate, {
                        fileLabel       : 'Question Latex',
                        itemSource      : Admin.encodeLatex(data['texts']['latex']),
                        latex           : true,
                        sourceType      : 'text'
                    }));
                    $filesContent.append(_.template(ItemFileTemplate, {
                        fileLabel       : 'Solution Latex',
                        itemSource      : Admin.encodeLatex(data['texts']['solutionLatex']),
                        latex           : true,
                        sourceType      : 'text'
                    }));

                    Metadata.render($metadataContent, data);

                    $filesWrapper.removeClass('hidden');
                    $metadataWrapper.removeClass('hidden');
                    $itemActionsWrapper.removeClass('hidden');
                    Admin.updateStatus('');
                }
            });
        },
        previewItemFile: function (e) {
            var $e = $(e.currentTarget),
                source = $e.data('source'),
                sourceType = $e.data('source-type'),
                label = $e.children('span.file-label').text();

            BootstrapDialog.show({
                title: 'Preview of ' + label,
                message: _.template(FilePreviewTemplate, {
                    source      : source,
                    sourceType  : sourceType
                }),
                cssClass: 'file-preview-modal',
                onshow: function(dialog) {
                    dialog.setSize(BootstrapDialog.SIZE_WIDE);
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
        publishItem: function (e) {
            changePendingItemStatus('publish');
        }
    });

    return ManagePendingItemsContentView;
});