// Item utilities
// File: utilities/itemUtilities.js

define(['jquery',
        'underscore',
        'admin-utils',
        'tex-utils',
        'bootstrap-dialog',
        'text!templates/itemFileOpenNewWindow.html',
        'text!templates/filePreviewWithCSS.html',
        'text!templates/filePreview.html',
        'text!templates/itemLockedWarning.html',
        'text!templates/filterCheckboxRow.html',
        'text!templates/rowSpanWrapper.html',
        'text!templates/processing.html',
        'text!templates/publishedItemTableRow.html',
        'text!templates/itemMinorEdit.html',
        'text!templates/branchOption.html',
        'text!templates/subbranchOption.html',
        'text!templates/imageFileOpenNewWindow.html',
        'text!templates/newOfferedTerm.html',
        'text!templates/newFileUpload.html',
        'text!templates/newItemFileThumbnail.html',
        'text!templates/imageFileUpdate.html',
        'text!templates/assignmentItemTableRow.html'],
    function ($, _, Admin, Tex, BootstrapDialog,
             ItemFileOpenNewWindowTemplate, FilePreviewWithCSSTemplate,
             FilePreviewTemplate, ItemLockedWarningTemplate,
             FilterCheckboxRowTemplate, RowSpanWrapperTemplate,
             ProcessingTemplate, PublishedItemRowTemplate,
             ItemMinorEditTemplate,
             BranchOptGroupTemplate, SubbranchOptionTemplate,
             ImageFileOpenNewWindowTemplate, NewOfferedTermTemplate,
             NewFileUploadTemplate, NewItemFileThumbnailTemplate,
             ImageFileUpdateTemplate, AssignmentItemRowTemplate) {
        var _item = {};

        function addTextToCell($t, text) {
            $t.empty();
            $t.append(_.template(RowSpanWrapperTemplate, {
                rowText    : text
            }));
        }

        function initEditingModal ($m, rawObject, fork) {
            var $branchSelect = $m.find('#itemBranchSelector'),
                $questionLatex = $m.find('div.item-question-latex-current'),
                $questionLatexNew = $m.find('div.item-question-latex-new'),
                $questionPdf = $m.find('div.item-question-preview-current'),
                $questionPdfNew = $m.find('div.item-question-preview-new'),
                $solutionLatex = $m.find('div.item-solution-latex-current'),
                $solutionLatexNew = $m.find('div.item-solution-latex-new'),
                $solutionPdf = $m.find('div.item-solution-preview-current'),
                $solutionPdfNew = $m.find('div.item-solution-preview-new'),
                $images = $m.find('div.image-files-wrapper');

            fork = typeof fork === 'undefined' ? false : fork;

            // inject the branch / subbranch options
            $.ajax({
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/objectives/'
            }).error(function (xhr,msg,status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success(function (data) {
                // sort the data alphabetically
                data = _.sortBy(data, function (datum) {
                    return datum.displayName.text;
                });

                // load data into the multi-selects and select the
                // current values
                _.each(data, function (datum) {
                    // the datum are roots
                    var branchSelected = false;

                    if (rawObject.branches.indexOf(datum.displayName.text) >= 0) {
                        branchSelected = true;
                    }

                    $branchSelect.append(_.template(BranchOptGroupTemplate, {
                        branchId    : datum.id,
                        branchName  : datum.displayName.text,
                        selected    : branchSelected
                    }));

                    if (Object.keys(datum['children']).length > 0) {
                        // sort the children alphabetically
                        var children = _.sortBy(datum['children'], function (child) {
                            return child.displayName.text;
                        });

                        _.each(children, function (child) {
                            var childSelected = false;

                            if (rawObject.subbranches.indexOf(child.displayName.text) >= 0) {
                                childSelected = true;
                            }

                            $branchSelect.append(_.template(SubbranchOptionTemplate, {
                                subbranchId     : child.id,
                                subbranchName   : child.displayName.text,
                                selected        : childSelected
                            }));
                        });
                    }
                });

                $branchSelect.select2({
                    dropdownAutoWidth: 'true'
                });

                Admin.updateStatus('');
            });

            // now select the current values for
            //   type, difficulty
            $m.find('select[name="item-type"]')
                .val(Admin.questionType(rawObject))
                .select2({
                    dropdownAutoWidth: 'true'
                });
            $m.find('select[name="item-difficulty"]')
                .val(rawObject.difficulty)
                .select2({
                    dropdownAutoWidth: 'true'
                });

            // bind the Add Term button
            $m.find('button.add-new-term')
                .on('click', function () {
                    var $p = $(this).parent();

                    $p.prepend(_.template(NewOfferedTermTemplate));
                    $p.find('select[name="termSelector"]')
                        .select2({
                            dropdownAutoWidth: 'true'
                        });
                    $p.find('select[name="psetSelector"]')
                        .select2({
                            dropdownAutoWidth: 'true'
                        });

                    $p.find('button.remove-new-offered')
                        .unbind()
                        .on('click', function () {
                            $(this).parent()
                                .parent()
                                .remove();
                        });
                });


            // now inject the extra templates...
            // like question LaTeX / PDF
            //      solution LaTeX / PDF
            //      image files

            if (!fork) {
                $.ajax({
                    url: Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                        '/items/' + rawObject.mecqbankId + '/'
                }).error(function (xhr, msg, status) {
                    Admin.updateStatus('Server error: ' + xhr.responseText);
                }).success(function (data) {
                    if (data.hasOwnProperty('files')) {
                        _item.injectRemoteFilePreview($questionLatex,
                            true,
                            data.texts.latex,
                                'Current Question LaTeX for ' + data.displayName.text);

                        _item.injectRemoteFilePreview($questionPdf,
                            false,
                            data.files.preview);

                        _item.injectRemoteFilePreview($solutionLatex,
                            true,
                            data.texts.solutionLatex,
                                'Current Solution LaTeX for ' + data.displayName.text);

                        _item.injectRemoteFilePreview($solutionPdf,
                            false,
                            data.files.solutionPreview);

                        _.each(data.files, function (url, fileName) {
                            if (fileName.indexOf('image_') >= 0) {
                                injectRemoteImagePreview($images,
                                    url,
                                    fileName.replace('image_', '').replace('_pdf', '.pdf'));
                            }
                        });


                        Admin.updateStatus('');
                    } else {
                        Admin.updateStatus('No files to preview.');
                    }
                });
            } else {
                $('label.comment-input').addClass('hidden');
            }

            // inject the upload file templates
            $questionLatexNew.append(_.template(NewFileUploadTemplate, {latex:true}));
            $questionPdfNew.append(_.template(NewFileUploadTemplate, {latex:false}));
            $solutionLatexNew.append(_.template(NewFileUploadTemplate, {latex:true}));
            $solutionPdfNew.append(_.template(NewFileUploadTemplate, {latex:false}));

            // bind the "add new" buttons
            $m.find('input[name="fileSelector"]')
                .on('change', function () {
                    var newFile = this.files[0],
                        $t = $(this).parents('div.new-file-wrapper'),
                        latex = false;

                    if (newFile.name.indexOf('.tex') >= 0) {
                        latex = true;
                    }

                    $t.find('span.filename-wrapper')
                        .html(_.template(NewItemFileThumbnailTemplate, {
                        fileLabel   : newFile.name,
                        latex       : latex
                    }));
                });

            $m.find('button.add-new-images input')
                .on('change', function () {
                    var $t = $(this).parents('div.image-files-wrapper'),
                        fileHandles = this.files;

                    $t.find('span.inserted-new-image').remove();

                    _.each(fileHandles, function (file) {
                        $t.prepend(_.template(ImageFileUpdateTemplate, {
                            fileLabel   : file.name
                        }));
                    });
                });
        }

        function injectRemoteImagePreview ($target, sourceUrl, title) {
            $target.prepend(_.template(ImageFileOpenNewWindowTemplate, {
                fileLabel   : title,
                itemUrl     : sourceUrl
            }));

            $target.find('button.remove-image-file')
                .unbind()
                .on('click', function () {
                    $(this).parent()
                        .addClass('alert')
                        .addClass('alert-danger')
                        .attr('role','alert');
                });
        }

        function validateItemEditData (_callback) {
            // validate that the new data entered into an "edit" modal
            // will work...basically
            // that images referenced in the .tex files are attached, and that
            // extra files are not uploaded.
            // An incomplete offered term is not allowed (empty pset is)
            var questionLatex = $('div.item-question-latex-new input[type="file"]'),
                solutionLatex = $('div.item-solution-latex-new input[type="file"]'),
                imageFileNames = [],
                latexFiles = [];

            _.each($('div.image-files-wrapper span.file-label'), function (imageBlock) {
                imageFileNames.push($(imageBlock).text());
            });

            if (_.any($('input[name="yearSelector"]'), function (year) {
                return $(year).val() === "" || parseInt($(year).val()) < 1999;
            })) {
                Admin.updateStatus('You cannot supply an incomplete year for an offered term.');
                _callback(false);
                return false;
            }

            if (!$('label.comment-input').hasClass('hidden') &&
                $('input[name="comment"]').val() === "") {
                Admin.updateStatus('Please provide a save comment.');
                _callback(false);
                return false;
            }

    //        if (($('div.item-question-latex-new span.filename-wrapper span.file-label').length +
    //             $('div.item-question-preview-new span.filename-wrapper span.file-label').length) === 1) {
    //            Admin.updateStatus('You must supply new question LaTeX and PDF together.');
    //            _callback(false);
    //            return false;
    //        }

    //        if (($('div.item-solution-latex-new span.filename-wrapper span.file-label').length +
    //             $('div.item-solution-preview-new span.filename-wrapper span.file-label').length) === 1) {
    //            Admin.updateStatus('You must supply new solution LaTeX and PDF together.');
    //            _callback(false);
    //            return false;
    //        }


            if (questionLatex.length !== 0) {
                questionLatex = questionLatex[0].files[0];

                if (typeof questionLatex !== 'undefined') {
                    latexFiles.push(questionLatex);
                }
            }

            if (solutionLatex.length !== 0) {
                solutionLatex = solutionLatex[0].files[0];

                if (typeof solutionLatex !== 'undefined') {
                    latexFiles.push(solutionLatex);
                }
            }

            if (latexFiles.length > 0) {
                Tex.extractImageFileNames(latexFiles, function (texImageFiles) {
                    if (_.some(texImageFiles, function (texImageFile) {
                        return imageFileNames.indexOf(texImageFile) < 0;
                    })) {
                        Admin.updateStatus('An image file specified in the LaTeX is missing. ' +
                            'Please check you have uploaded all required images as pdfs.');
                        _callback(false);
                        return false;
                    } else {
                        _callback(true);
                        return true;
                    }
                });
            } else {
                _callback(true);
                return true;
            }
        }

        _item.attachItemToAssessmentAjax = function (myForm, assessmentId, errorMethod, successCallback) {
            $.ajax({
                url         : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' + assessmentId + '/items/',
                data        : myForm,
                contentType : false,
                processData : false,
                type        : 'POST'
            }).error( function (xhr, status, msg) {
                errorMethod(xhr);
            }).success( function (data) {
                successCallback(data);
            });
        };

        _item.createAssessmentAjax = function (myForm, errorMethod, successCallback) {
            $.ajax({
                url         : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/',
                data        : myForm,
                contentType : false,
                processData : false,
                type        : 'POST'
            }).error( function (xhr, status, msg) {
                errorMethod(xhr);
            }).success( function (data) {
                successCallback(data);
            });
        };

        _item.createItemAjax = function (myForm, errorMethod, successCallback) {
            $.ajax({
                url         : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/',
                data        : myForm,
                contentType : false,
                processData : false,
                type        : 'POST'
            }).error( function (xhr, status, msg) {
                errorMethod(xhr);
            }).success( function (data) {
                successCallback(data);
            });
        };

        _item.getRowByItemId = function (itemId) {
            var $itemRows = $('tr.published-item-row, tr.assignment-item-row');

            return $(_.find($itemRows, function (item) {
                return $(item).data('raw-object')
                    .mecqbankId === itemId;
            }));
        };

        _item.handleNewAssessments = function (itemId, _callback) {
            var $newOffereds = $('div.new-term-offered-wrapper'),
                numNewOffereds = $newOffereds.length;

            if (numNewOffereds > 0) {
                _.each($newOffereds, function (offered) {
                    var $o = $(offered),
                        assessmentCreateForm = new FormData(),
                        assessmentAddItemForm = new FormData(),
                        assessmentName, offeredTerm;

                    if ($o.find('select[name="psetSelector"]').val() === 'nil') {
                        assessmentName = 'nil';
                    } else {
                        assessmentName = $o.find('select[name="psetSelector"]').val() + ', ' +
                            $o.find('input[name="psetNumberSelector"]').val();
                    }

                    offeredTerm = $o.find('select[name="termSelector"]').val() + ', ' +
                        $o.find('input[name="yearSelector"]').val();

                    assessmentCreateForm.append('term', offeredTerm);
                    assessmentCreateForm.append('assessment', assessmentName);
                    assessmentAddItemForm.append('itemId', itemId);

                    _item.createAssessmentAjax(assessmentCreateForm,
                        Admin.reportError,
                        function (assessmentData) {
                            _item.attachItemToAssessmentAjax(assessmentAddItemForm,
                                assessmentData['mecqbankId'],
                                Admin.reportError,
                                function (data) {
                                    --numNewOffereds;
                                    if (numNewOffereds === 0) {
                                        _callback(data);
                                    }
                                });
                        });
                });
            } else {
                _callback();
            }
        };

        _item.hasAttrChecked = function ($i) {
            var  allCheckedAttrs = $('div.filter input[type="checkbox"]:checked')
                    .not('input.inclusive-years')
                    .map(function() {
                    var name = this.name,
                        object = {};
                        object[name] = this.value;
                    return object;
                }),
                rawObject = $i.data('raw-object');

            if (_.all(allCheckedAttrs, function (obj) {
                var attr = _.keys(obj)[0],
                    value = obj[attr],
                    itemValues;

                if (attr === 'branch') {
                    // for branch, look in the rawObject
                    itemValues = rawObject.branches + rawObject.subbranches;
                } else {
                    itemValues = $i.find('td.' + attr + '-col span')
                        .text()
                        .split(',');

                    //http://stackoverflow.com/questions/19293997/javascript-apply-trim-function-to-each-string-in-an-array
                    itemValues = itemValues.map(Function.prototype.call,
                        String.prototype.trim);
                }

                if (itemValues.length === 1 && itemValues[0] === "" && value === 'None') {
                    return true;
                } else {
                    return itemValues.indexOf(value) >= 0;
                }
            })) {
                return true;
            } else {
                return false;
            }
        };

        _item.injectRemoteFilePreview = function ($target, latex, source, title, thumbnail) {
            var button;

            title = typeof title !== 'undefined' ? title : 'Current';
            thumbnail = typeof thumbnail !== 'undefined' ? thumbnail : true;

            if (latex) {
                button = _.template(ItemFileOpenNewWindowTemplate, {
                    fileLabel   : 'Current',
                    latex       : latex,
                    thumbnail   : thumbnail
                });

                $target.append(button);
                $target.find('span.item-file-preview')
                    .on('click', function () {
                        var newWindow = window.open("");
                        newWindow.document.body.innerHTML = _.template(
                            FilePreviewWithCSSTemplate, {
                            source  : source,
                            title   : title
                        });
                    });
            } else {
                $target.append(_.template(ItemFileOpenNewWindowTemplate, {
                    fileLabel   : title,
                    itemUrl     : source,
                    latex       : false,
                    thumbnail   : thumbnail
                }));
            }
        };

        _item.inSelectedDateRange = function ($i) {
            var inclusive = $('input.inclusive-years')
                .prop('checked'),
                $yearsAgo = parseFloat($('input.year-slider').val());

            if (typeof inclusive === 'undefined') {
                // this is the Published Items filter...no year,
                // always return False
                return true;
            } else {
                return _item.usedYearsAgo($i.data('raw-object'), $yearsAgo, !inclusive);
            }
        };

        _item.insertItemIntoTable = function ($t, itemData, inBuildAssignments) {
            var bundle = {
                description: itemData.description.text,
                displayName: itemData.displayName.text,
                questionType: Admin.questionType(itemData),
                questionDifficulty: itemData.difficulty,
                rawObject: Admin.rawObject(itemData)
            };

            try {
                bundle['pset'] = itemData.psets.join(', ');
            } catch (e) {
                bundle['pset'] = '';
            }

            try {
                bundle['terms'] = itemData.terms.join(', ');
            } catch (e) {
                bundle['terms'] = '';
            }

            if (inBuildAssignments) {
                // if can upload new item versions, then assignment i not
                // locked or published
                bundle['locked'] = false;
                bundle['published'] = false;
                $t.append(_.template(AssignmentItemRowTemplate, bundle));
            } else {
                $t.append(_.template(PublishedItemRowTemplate, bundle));
            }

            _item.updateFilters(itemData);
        };

        _item.lock = function (itemId) {
            $.ajax({
                type: 'PATCH',
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + itemId + '/lock/'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                console.log('Locked item ' + itemId + ' for editing.');
            });
        };

        _item.majorEdit = function (itemData) {
            var offeredTerms = [],
                itemId = itemData.mecqbankId,
                $t = $('div.item-list tbody'),
                inBuildAssignments = false;

            if ($t.length === 0) {
                // then in build assignments
                $t = $('div.assignment-items tbody');
                inBuildAssignments = true;
            }

            BootstrapDialog.show({
                title: 'Major edit / Fork of ' + itemData.displayName.text,
                message: _.template(ItemMinorEditTemplate, {
                    itemKeywords    : itemData.description.text,
                    itemSource      : itemData.source,
                    offeredTerms    : offeredTerms
                }),
                closable: false,
                cssClass: 'file-preview-modal',
                onshow: function(dialog) {
                    var $m = dialog.$modalBody;

                    dialog.setSize(BootstrapDialog.SIZE_WIDE);
                    Admin.removeBRs($m);
                    Admin.processing();
                },
                onshown: function (dialog) {
                    var $m = dialog.$modalBody;

                    initEditingModal($m, itemData, fork=true);
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
                            // Create a new item...
                            Admin.processing();

                            validateItemEditData( function (validData) {
                                if (validData) {
                                    _item.saveEdit(itemId, function (newItemData) {
                                            if (inBuildAssignments) {
                                                // get the assignment Id,
                                                // create the form with newItemData ID
                                                // send to _item.attachItemToAssessmentAjax
                                                // callback will remove the activeRow,
                                                // and insert new row
                                                // Need to clean up 3 things:
                                                //   1) add assignment term to newItemData.terms
                                                //   2) add assignment pset to newItemData.pset
                                                //   3) delete old item from assignment
                                                var $oldRow = _item.getRowByItemId(itemId),
                                                    assignmentForm = new FormData(),
                                                    assignmentObj = Admin.activeAssignment(),
                                                    assignmentId = Admin.activeAssignmentId(),
                                                    assignmentTerm = assignmentObj.term,
                                                    assignmentPset = assignmentObj.displayName.text.split(' ')[0];

                                                assignmentForm.append('itemId', newItemData.mecqbankId);
                                                _item.attachItemToAssessmentAjax(assignmentForm,
                                                    assignmentId,
                                                    Admin.reportError,
                                                function (data) {
                                                    dialog.close();

                                                    newItemData.terms.push(assignmentTerm);
                                                    newItemData.psets.push(assignmentPset);

                                                    _item.insertItemIntoTable($t,
                                                        newItemData,
                                                        inBuildAssignments);

                                                    _item.removeFromAssessment(itemId,
                                                        assignmentId,
                                                        function () {
                                                            $oldRow.remove();
                                                            Admin.doneProcessing();
                                                    });
                                                });
                                            } else {
                                                // need to attach the newly created item to assessments, here
                                                _item.handleNewAssessments(newItemData.mecqbankId,
                                                    function (data) {
                                                        Admin.updateStatus('Item created. SN: ' +
                                                            newItemData.displayName.text);
                                                        dialog.close();
                                                        // put the new Item in the UI
                                                        _item.insertItemIntoTable($t,
                                                            newItemData,
                                                            inBuildAssignments);

                                                        Admin.doneProcessing();
                                                });
                                            }
                                        },
                                        true);
                                } else {
                                    // pass, the exact error message should be displayed in validateItemEditData
                                    console.log('Failed form validation...');
//                                    Admin.updateStatus('');
                                }
                            });
                        }
                    }
                ]
            });
        };

        _item.minorEdit = function (itemData) {
            var offeredTerms = [],
                itemId = itemData.mecqbankId;

            _.each(itemData.terms, function (term, index) {
                offeredTerms.push(term + ' -- ' + itemData.psets[index]);
            });

            _item.lock(itemId);

            BootstrapDialog.show({
                title: 'Minor edit of ' + itemData.displayName.text,
                message: _.template(ItemMinorEditTemplate, {
                    itemKeywords    : itemData.description.text,
                    itemSource      : itemData.source,
                    offeredTerms    : offeredTerms
                }),
                closable: false,
                cssClass: 'file-preview-modal',
                onshow: function(dialog) {
                    var $m = dialog.$modalBody;

                    dialog.setSize(BootstrapDialog.SIZE_WIDE);
                    Admin.removeBRs($m);
                    Admin.processing();

                    initEditingModal($m, itemData);
                },
                buttons: [
                    {
                        label: 'Cancel',
                        cssClass: 'btn-danger',
                        action: function (dialog) {
                            _item.unlock(itemId);
                            dialog.close();
                        }
                    },{
                        label: 'Save',
                        cssClass: 'btn-success',
                        action: function (dialog) {
                            var itemRowClass = 'published-item-row',
                                assignmentRowClass = 'assignment-item-row',
                                inBuildAssignments = false,
                                rowClass = itemRowClass,
                                $activeRow = $('tr.' + rowClass + '.active'),
                                processing = _.template(ProcessingTemplate),
                                $newRow, indexHolder, bundle;

                            if ($activeRow.length === 0) {
                                rowClass = assignmentRowClass;
                                $activeRow = _item.getRowByItemId(itemId);
                                inBuildAssignments = true;
                            }

                            // Save all the data back to the same item
                            Admin.processing();

                            validateItemEditData( function (validData) {
                                if (validData) {
                                    _item.saveEdit(itemId, function (newItemData) {
                                        _item.unlock(itemId);
                                        Admin.updateStatus('Item saved.');
                                        dialog.close();
                                        // update the rawObject and row in the UI.

                                        indexHolder = $activeRow.index();

                                        bundle = {
                                            description: processing(),
                                            displayName: newItemData['displayName']['text'],
                                            pset: processing(),
                                            questionType: processing(),
                                            questionDifficulty: processing(),
                                            rawObject: Admin.rawObject(newItemData),
                                            terms: processing()
                                        };
                                        if (inBuildAssignments) {
                                            // if you are uploading items,
                                            // then the assignment is not
                                            // locked or published
                                            bundle['locked'] = false;
                                            bundle['published'] = false;
                                            $activeRow.replaceWith(
                                                _.template(AssignmentItemRowTemplate,
                                                    bundle));
                                        } else {
                                            $activeRow.replaceWith(
                                                _.template(PublishedItemRowTemplate,
                                                    bundle));
                                        }

                                        $newRow = $($('tr.' + rowClass)[indexHolder]);

                                        _item.updateItemRow($newRow,
                                            itemId);
                                    });
                                } else {
                                    // pass, the exact error message should be displayed in validateItemEditData
                                    console.log('Failed form validation...');
//                                    Admin.updateStatus('');
                                }
                            });
                        }
                    }
                ]
            });
        };

        _item.psetDisplayName = function (datum) {
            var displayNames = [],
                psets = datum.psets;

            _.each(psets, function (pset) {
                var psetLabel = pset.split(' ')[0];

                if (displayNames.indexOf(psetLabel) < 0) {
                    displayNames.push(psetLabel);
                }
            });

            return displayNames.join(', ');
        };

        _item.removeFromAssessment = function (itemId, assessmentId, successCallback) {
            $.ajax({
                url         : Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                    '/assessments/' + assessmentId + '/items/' + itemId + '/',
                type        : 'DELETE'
            }).error( function (xhr, status, msg) {
                Admin.reportError(xhr);
            }).success( function (data) {
                successCallback(data);
            });
        };

        _item.saveEdit = function (itemId, _callback, fork) {
            // scrape the data out of the modal and send it to the server
            var $m = $('div.modal-body'),
                keywords = $m.find('input[name="keywords"]').val(),
                source = $m.find('input[name="source"]').val(),
                comment = $m.find('input[name="comment"]').val(),
                branches = $m.find('option.branch-option:selected').map(function () {
                    return this.value;
                }).get(),
                subbranches = $m.find('option.subbranch-option:selected').map(function () {
                    return this.value;
                }).get(),
                itemType = $m.find('select[name="item-type"]').val(),
                difficulty = $m.find('select[name="item-difficulty"]').val(),
                newQuestionLatexFile = $m.find('div.item-question-latex-new input[name="fileSelector"]')[0].files,
                newQuestionPdfFile = $m.find('div.item-question-preview-new input[name="fileSelector"]')[0].files,
                newSolutionLatexFile = $m.find('div.item-solution-latex-new input[name="fileSelector"]')[0].files,
                newSolutionPdfFile = $m.find('div.item-solution-preview-new input[name="fileSelector"]')[0].files,
                newImageFiles = $m.find('div.image-files-wrapper input[name="addNewImages"]')[0].files,
                updateItemForm = new FormData(),
                $newOffereds = $('div.new-term-offered-wrapper'),
                numNewOffereds = $newOffereds.length,
                totalNumberOfCalls = numNewOffereds + 1,  // the extra one is for all the other attributes
                numLatexFiles = 0,
                hasLatex = false;

            fork = typeof fork === 'undefined' ? false : fork;

            if (fork) {
                updateItemForm.append('parentId', itemId);
            }

            updateItemForm.append('keywords', keywords);
            updateItemForm.append('source', source);
            updateItemForm.append('comment', comment);
            updateItemForm.append('branches', JSON.stringify(branches));
            updateItemForm.append('subbranches', JSON.stringify(subbranches));
            updateItemForm.append('type', itemType);
            updateItemForm.append('difficulty', difficulty);
            if (newQuestionPdfFile.length > 0) {
                updateItemForm.append('preview', newQuestionPdfFile[0]);
            }
            if (newSolutionPdfFile.length > 0) {
                updateItemForm.append('solutionPreview', newSolutionPdfFile[0]);
            }
            if (newImageFiles.length > 0) {
                _.each(newImageFiles, function (imageFile) {
                    updateItemForm.append(imageFile.name, imageFile);
                });
            }

            // have to parse the LaTeX files if present
            if (newQuestionLatexFile.length > 0) {
                var reader = new FileReader();

                hasLatex = true;
                numLatexFiles++;
                reader.onload = function (e) {
                    updateItemForm.append('latex', e.target.result);

                    --numLatexFiles;
                    if (numLatexFiles === 0) {
                        // submit the form!

                        if (fork) {
                            _item.createItemAjax(updateItemForm,
                                Admin.reportError,
                                function (data) {
                                    --totalNumberOfCalls;
                                    if (totalNumberOfCalls === 0) {
                                        _callback(data);
                                    }
                                });
                        } else {
                            _item.updateItemAjax(updateItemForm,
                                itemId,
                                Admin.reportError,
                                function (data) {
                                    --totalNumberOfCalls;
                                    if (totalNumberOfCalls === 0) {
                                        _callback(data);
                                    }
                                });
                        }
                    }
                };
                reader.readAsText(newQuestionLatexFile[0]);
            }

            if (newSolutionLatexFile.length > 0) {
                var reader = new FileReader();

                hasLatex = true;
                numLatexFiles++;
                reader.onload = function (e) {
                    updateItemForm.append('solutionLatex', e.target.result);

                    --numLatexFiles;
                    if (numLatexFiles === 0) {
                        // submit the form!
                        if (fork) {
                            _item.createItemAjax(updateItemForm,
                                Admin.reportError,
                                function (data) {
                                    --totalNumberOfCalls;
                                    if (totalNumberOfCalls === 0) {
                                        _callback(data);
                                    }
                                });
                        } else {
                            _item.updateItemAjax(updateItemForm,
                                itemId,
                                Admin.reportError,
                                function (data) {
                                    --totalNumberOfCalls;
                                    if (totalNumberOfCalls === 0) {
                                        _callback(data);
                                    }
                                });
                        }
                    }
                };
                reader.readAsText(newSolutionLatexFile[0]);
            }

            if (!hasLatex) {
                if (fork) {
                    _item.createItemAjax(updateItemForm,
                        Admin.reportError,
                        function (data) {
                            --totalNumberOfCalls;
                            if (totalNumberOfCalls === 0) {
                                _callback(data);
                            }
                        });
                } else {
                    _item.updateItemAjax(updateItemForm,
                        itemId,
                        Admin.reportError,
                        function (data) {
                            --totalNumberOfCalls;
                            if (totalNumberOfCalls === 0) {
                                _callback(data);
                            }
                        });
                }
            }

            // if new offereds, create new assessments and append this item
            if (numNewOffereds > 0 && !fork) {
                _item.handleNewAssessments(itemId, function (data) {
                    totalNumberOfCalls = totalNumberOfCalls - numNewOffereds;
                    if (totalNumberOfCalls === 0) {
                        _callback(data);
                    }
                });
            } else {
                // bypass the offereds for now
                totalNumberOfCalls = totalNumberOfCalls - numNewOffereds;
                if (totalNumberOfCalls === 0) {
                    _callback(data);
                }
            }
        };

        _item.searchRows = function (rows, searchInput, callback) {
            var $allItems = $(rows),
                allSearchWords = $(searchInput).val().trim().split(' ');

            if (allSearchWords.length === 1 && allSearchWords[0] === "") {
                _item.toggleFromFilters(rows, callback);  // reset the rows according to the other search filters
            } else {
                _.each($allItems, function (item) {
                    var $i = $(item),
                        itemWords = $.merge($i.find('td.serial-number-col span.display-name').text().split(','),
                            $i.find('td.keywords-col span').text().split(','));

                    if ((itemWords.length === 1 && itemWords[0] === "" && allSearchWords !== [""])) {
                        // hide anything with no keywords
                        $i.addClass('hidden');
                    } else {
                        if (!_.some(allSearchWords, function (searchWord) {
                            return _.some(itemWords, function (itemWord) {
                                return itemWord.indexOf(searchWord) >= 0;
                            });
                        })) {
                            $i.addClass('hidden');
                        } else {
                            $i.removeClass('hidden');
                        }
                    }

                });

                callback();
            }
        };

        _item.showPreview = function (itemName, fileUrl, remote) {
            // if the file is a PDF file, open it in a modal.
            // Otherwise, open it as a new tab / let the browser
            // download it
            remote = typeof remote !== 'undefined' ? remote : false;
            if (fileUrl.indexOf('.pdf') >= 0 && !remote) {
                BootstrapDialog.show({
                    title: 'Preview of ' + itemName,
                    message: _.template(FilePreviewTemplate, {
                        source: fileUrl,
                        sourceType: 'remote'
                    }),
                    cssClass: 'file-preview-modal',
                    onshow: function (dialog) {
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
            } else {
                window.open(fileUrl, '_blank');
            }
        };

        _item.toggleFromFilters = function (rows, callback) {
            // this needs to check all the filter boxes...not just one passed
            // in attribute...
            var $allItems = $(rows);

            _.each($allItems, function (item) {
                var $i = $(item);

                if (_item.hasAttrChecked($i) &&
                    _item.inSelectedDateRange($i)) {
                    $i.removeClass('hidden');
                } else {
                    $i.addClass('hidden');
                }
            });

            callback();
        };

        _item.unlock = function (itemId, suppress) {
            suppress = typeof suppress === 'undefined' ? false : suppress;
            $.ajax({
                type: 'PATCH',
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/items/' + itemId + '/unlock/'
            }).error( function (xhr, msg, status) {
                if (!suppress) {
                    Admin.updateStatus('Server error: ' + xhr.responseText);
                }
            }).success( function (data) {
                console.log('Unlocked item ' + itemId + '.');
            });
        };

        _item.updateItemAjax = function (myForm, itemId, errorMethod, successCallback) {
            $.ajax({
                url         : Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                    '/items/' + itemId + '/',
                data        : myForm,
                contentType : false,
                processData : false,
                type        : 'POST'
            }).error( function (xhr, status, msg) {
                errorMethod(xhr);
            }).success( function (data) {
                successCallback(data);
            });
        };

        _item.updateItemRow = function ($row, itemId) {
            $.ajax({
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                    '/items/' + itemId + '/'
            }).error(function (xhr, status, msg) {
                Admin.reportError(xhr);
            }).success(function (data) {
                // update the row and update the filters
                var $lockTarget = $row.find('td.serial-number-col'),
                    $descriptionTarget = $row.find('td.keywords-col'),
                    $typeTarget = $row.find('td.type-col'),
                    $difficultyTarget = $row.find('td.difficulty-col'),
                    $termTarget = $row.find('td.term-col'),
                    $psetTarget = $row.find('td.pset-col'),
                    psetTypes = [];

                $row.data('raw-object', data);

                // unlock all items that this user may have inadvertently
                // locked (i.e. if they refresh the page)
                // this unlocks the items for other users
                if (!data.locked) {
                    _item.unlock(itemId, true);
                } else {
                    // update the template in $row
                    $lockTarget.append(_.template(ItemLockedWarningTemplate));
                }

                addTextToCell($descriptionTarget, data.description.text);
                addTextToCell($typeTarget, Admin.questionType(data));
                addTextToCell($difficultyTarget, data.difficulty);
                try {
                    addTextToCell($termTarget, data.terms.join(', '));
                } catch (e) {
                    addTextToCell($termTarget, '');
                }
                try {
                    _.each(data.psets, function (pset) {
                        psetTypes.push(pset.split(' ')[0]);
                    });
                    addTextToCell($psetTarget, psetTypes.join(', '));
                } catch (e) {
                    addTextToCell($psetTarget, '');
                }

                _item.updateFilters(data);
            });
        };

        _item.updateFilters = function (item) {
            // update the row and update the filters
            var $termsFilter = $('div.terms-filter'),
                $psetFilter = $('div.pset-filter'),
                $typesFilter = $('div.types-filter'),
                $difficultyFilter = $('div.difficulty-filter'),
                currentTerms = $termsFilter.find('label.filter-row').map(function () {
                    return $(this).text().trim();
                }).get(),
                currentPsets = $psetFilter.find('label.filter-row').map(function () {
                    return $(this).text().trim();
                }).get(),
                currentTypes = $typesFilter.find('label.filter-row').map(function () {
                    return $(this).text().trim();
                }).get(),
                currentDifficulties = $difficultyFilter.find('label.filter-row').map(function () {
                    return $(this).text().trim();
                }).get(),
                questionType = Admin.questionType(item),
                difficulty = item.difficulty,
                includeNoneTermOption = false,
                includeNonePsetOption = false;

            if (item['psets'].length > 0) {
                _.each(item['psets'], function (pset) {
                    var psetName = Admin.toTitle(pset.split(' ')[0]);
                    if (psetName === 'Nil') {
                        psetName = 'Generic Bucket';
                    }

                    if (currentPsets.indexOf(psetName) < 0) {
                        currentPsets.push(psetName);
                    }
                });
            } else {
                includeNonePsetOption = true;
            }

            if (item['terms'].length > 0) {
                _.each(item['terms'], function (term) {
                    if (currentTerms.indexOf(term) < 0) {
                        currentTerms.push(term);
                    }
                });
            } else {
                includeNoneTermOption = true;
            }

            if (currentTypes.indexOf(questionType) < 0) {
                currentTypes.push(questionType);
            }

            if (currentDifficulties.indexOf(difficulty) < 0) {
                currentDifficulties.push(difficulty);
            }

            // sort the filter lists
            currentTerms = _.chain(currentTerms)
                .sortBy(function (term) {
                    return term.split(' ')[0];
                }).sortBy(function (term) {
                    return parseInt(term.split(' ')[1]);
                });

            if (includeNoneTermOption &&
                currentTerms.indexOf('None') < 0) {
                currentTerms.push('None');
            }

            currentPsets.sort();

            if (includeNonePsetOption &&
                currentPsets.indexOf('None') < 0) {
                currentPsets.push('None');
            }

            currentDifficulties.sort();
            currentTypes.sort();

            // now append the filters to the right sections
            $termsFilter.empty();

            currentTerms.each(function (term) {
                $termsFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : term,
                    attrType        : 'term'
                }));
            });

            $psetFilter.empty();
            _.each(currentPsets, function (pset) {
                $psetFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : pset,
                    attrType        : 'pset'
                }));
            });

            $difficultyFilter.empty();
            _.each(currentDifficulties, function (difficulty) {
                $difficultyFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : difficulty,
                    attrType        : 'difficulty'
                }));
            });

            $typesFilter.empty();
            _.each(currentTypes, function (type) {
                $typesFilter.append(_.template(FilterCheckboxRowTemplate, {
                    attrFullName    : type,
                    attrType        : 'type'
                }));
            });
        };

        _item.usedYearsAgo = function (itemObj, yearsAgo, exclusive) {
            // check if the item was used <= X (inclusive... > X for exclusive)
            // years ago
            // yearsAgo is a year in 0.5 increments
            // itemObj should be the rawObject of the item

            exclusive = typeof exclusive === 'undefined' ? false : exclusive;

            var terms = itemObj.terms,
                usedYearsAgo,
                termYearsAgo;

            if (exclusive) {
                usedYearsAgo = true; // because if any single use in the given time period, need to return false
            } else {
                usedYearsAgo = false; // because if any use in the given time period, return true
            }

            if (terms.length === 0) {
                // treat unused items as always "used"
                usedYearsAgo = true;
            } else {
                _.each(terms, function (term) {
                    termYearsAgo = Admin.termTimeFromNow(term);
                    if ((termYearsAgo <= yearsAgo) &&
                        (termYearsAgo >= 0)) {
                        if (exclusive) {
                            // cannot do a simple usedYearsAgo = !usedYearsAgo because of
                            // the corner case below -- could get double toggle
                            usedYearsAgo = false;
                        } else {
                            usedYearsAgo = true;
                        }
                    }

                    // tweak corner case of future assignments
                    // and inclusive, should return true still
                    if (!exclusive && termYearsAgo < 0) {
                        usedYearsAgo = true;
                    }
                });
            }

            return usedYearsAgo;
        };

        return _item;
});
