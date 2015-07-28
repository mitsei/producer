//Filename: views/project/uploadItemsContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'admin-utils',
    'item-utils',
    'text!templates/uploadItems.html',
    'text!templates/itemUploadForm.html',
    'text!templates/metadataAttrs.html',
    'text!templates/itemFigures.html',
    'text!templates/uploadProcessingButton.html',
    'text!templates/uploadSuccessButton.html',
    'text!templates/uploadErrorButton.html'
], function ($, _, Backbone, Admin, Item, UploadItemsTemplate,
             ItemUploadFormTemplate, MetadataAttributesTemplate,
             ItemFiguresTemplate, UploadProcessingTemplate,
             UploadSuccessTemplate, UploadErrorTemplate) {

    function attachSubmitFormData (itemName, metadataAttrs, fileObjs) {
        // need to create 3 forms:
        //   1) create the assessment
        //   2) create the item
        //   3) attach the item to the assessment
        var $submit = $('div.' + itemName).find('button.upload-item-button'),
            $wrapper = $('div.' + itemName).find('div.submit-this-item'),
            createAssessmentForm = new FormData(),
            createItemForm = new FormData(),
            attachItemToAssessmentForm = new FormData(),
            subbranches = [],
            branches = [],
            itemOnlyCreate = true,
            hasTerm = false,
            hasPset = false;

        function errorMethod(xhr) {
            Admin.updateStatus('Server error when uploading ' + itemName + ': ' + xhr.responseText);
            $wrapper.html(_.template(UploadErrorTemplate));
        }


        // compress the branches & subbranches first
        _.each(metadataAttrs, function (attr) {
            if (attr.attr === 'Subbranch') {
                subbranches.push(attr.value);
            } else if (attr.attr === 'Branch') {
                branches.push(attr.value);
            }

        });

        _.each(metadataAttrs, function (attr) {
            if (attr.attr === 'Term') {
//                myForm.append('term', attr.value.split(',')[0]);
//                myForm.append('year', attr.value.split(',')[1].trim());
                createAssessmentForm.append('term', attr.value);
                hasTerm = true;
            } else if (attr.attr === 'Subbranch') {
                createItemForm.append('subbranches', JSON.stringify(subbranches));
            } else if (attr.attr === 'Branch') {
                createItemForm.append('branches', JSON.stringify(branches));
            } else if (attr.attr.toLowerCase() === 'qtype') {
                createItemForm.append('type', attr.value);
            } else if (attr.attr.toLowerCase() === 'topic') {
                createItemForm.append('keywords', attr.value);
            } else if (attr.attr === 'Pset') {
                createAssessmentForm.append('assessment', attr.value);
                hasPset = true;
                if (attr.value.toLowerCase().indexOf('pset') >= 0 ||
                    attr.value.toLowerCase().indexOf('quiz') >= 0) {
                    itemOnlyCreate = false;
                }
            } else {
                var camelCaseAttr = attr.attr.charAt(0).toLowerCase() + attr.attr.slice(1);
                createItemForm.append(camelCaseAttr, attr.value);
            }
        });

        if (hasTerm && !hasPset) {
            createAssessmentForm.append('assessment', 'nil');
            itemOnlyCreate = false;
        }

        _.each(fileObjs, function (fileObj) {
            createItemForm.append(fileObj.fileName, fileObj.fileObj);
        });

        $submit.unbind('click').on('click', function () {
            Admin.clearStatusBoxes();
            $wrapper.html(_.template(UploadProcessingTemplate));

            if (itemOnlyCreate) {
                Item.createItemAjax(createItemForm, errorMethod, function () {
                    $wrapper.html(_.template(UploadSuccessTemplate));
                    updateProgressBar();
                });
            } else {
                Item.createAssessmentAjax(createAssessmentForm, errorMethod, function (assessmentData) {
                    Item.createItemAjax(createItemForm, errorMethod, function (itemData) {
                        attachItemToAssessmentForm.append('itemId', itemData['mecqbankId']);
                        Item.attachItemToAssessmentAjax(attachItemToAssessmentForm,
                            assessmentData['mecqbankId'],
                            errorMethod, function () {
                                $wrapper.html(_.template(UploadSuccessTemplate));
                                updateProgressBar();
                            });
                    });
                });
            }
        });
    }

    function checkSubmitEligibility (itemName) {
        var $itemFiles = $('div.' + itemName);
        if ($itemFiles.find('div.alert.alert-danger').length === 0) {
            $itemFiles.find('div.item-actions')
                .addClass('show')
                .removeClass('hidden');
            return true;
        } else {
            $itemFiles.find('div.item-actions')
                .removeClass('show')
                .addClass('hidden');
            return false;
        }
    }

    function extractFigureName (text) {
        var onlyImageText = text.substring(text.indexOf('includegraphics'), text.length),
            initialAttempt = extractTextBetweenCurlyBraces(onlyImageText);
//        if (initialAttempt.indexOf('.pdf') < 0) {
//            return initialAttempt + '.pdf';
//        } else {
        return initialAttempt;
    }

    function extractMetadataAttribute (text) {
        var attr = text.substring(1, text.indexOf('{'));
        return attr.charAt(0).toUpperCase() + attr.slice(1);
    }

    function extractTextBetweenCurlyBraces (text) {
        return text.substring(text.indexOf('{') + 1, text.indexOf('}'));
    }

    function fileDragHover(e) {
        e.stopPropagation();
        e.preventDefault();
        if (e.type == 'dragover') {
            $(e.target).addClass('hover');
        } else {
            $(e.target).removeClass('hover');
        }
    }

    function fileSelectHandler(e) {
        fileDragHover(e);

        var files = e.target.files || e.originalEvent.dataTransfer.files,
            content;

        Admin.clearStatusBoxes();

        if (window.File && window.FileReader && window.FileList && window.Blob) {
            content = new UploadItemsContentView();
            content.render(files);
        } else {
            alert('The File APIs are not fully supported by your browser. ' +
                  'Please use a modern browser to upload items.');
        }
    }

    function updateProgressBar() {
        var completedItems = $('div.submit-this-item div.alert-success:visible').length,
            totalItems = $('div.submit-this-item:visible').length,
            errorItems = $('div.submit-this-item div.alert-danger:visible').length,
            progressBar = $('div.progress-bar'),
            progressText = $('div.progress-text');

        progressBar.width(parseInt(100 * completedItems / totalItems) + '%');
        progressText.html(completedItems + ' / ' + totalItems);

        if (totalItems === completedItems) {
            Admin.updateStatus('Done uploading all ' + totalItems + ' questions.');
        } else if (errorItems > 0) {
            Admin.updateStatus('Error processing an item...');
        }
    }

    var UploadItemsContentView = Backbone.View.extend({
//        el: $('#dashboard_main_content'),
        className: 'my-subject-upload-items',
        initialize: function () {
            var compiledTemplate = _.template(UploadItemsTemplate, {
                    'upload'    : false
                }),
                xhr = new XMLHttpRequest();

            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);

            // drag and drop tutorial here:
            // http://www.sitepoint.com/html5-file-drag-and-drop/
            this.$el.find('span.upload-files-button').on('change', fileSelectHandler);
            if (xhr.upload) {
                this.$el.find('div.file-drop-area')
                    .on('dragover dragleave', fileDragHover)
                    .on('drop', fileSelectHandler)
                    .css('display', 'inline-block');
            }
            return this;
        },
        render: function (files) {
            var itemNamePrefixes = ['CONT','RBEL','VISC','PLST','FRCT','FATG','DSGN','MISC'],
                itemNames = [],
                fileIndexToItemNameMap = {},  // send this to the API as an input
                fileNamesToItemMap = {},
                fileNamesToFileIndexMap = {},
                imageFiles = {},  // Map file_name (minus .pdf) to fileIndex
                $uploadActions = $('div.upload-actions');

            // cycle through each file, and parse the item name from it
            // Each item *should* have a *.meta, _Sol.tex/pdf, *.tex/pdf,
            // and associated figures.
            // Parse the two *.tex files to see what figures go with
            // each item (indicated by \includegraphics{ <filename> }
            // Because we can't move the files to another input (browser security),
            // let's make a mapping from fileIndex -> itemIndex, where
            // each itemIndex represents a single item
            // Keep figures in a separate list...
            _.each(files, function (file, fileIndex) {
                // Sort the files by name into each item,
                // and for each item, append an ItemUploadForm for that item
                // This form will be used by the user to verify that
                // the right files are included...we should flag in each
                // form which files seem to be missing (figures, metadata, solution, etc.)
                if (itemNamePrefixes.some(function (prefix) {
                    return file.name.indexOf(prefix) >= 0;
                    })) {
                    // is a problem file

                    var itemName = file.name.split('.')[0],
                        itemIndex;

                    if (itemName.indexOf('_Sol') >= 0) {
                        itemName = itemName.replace('_Sol', '');
                    }
                    if (itemNames.indexOf(itemName) >= 0) {
                        // item already exists, point this fileIndex to that item
                        // also add this filename to the fileNameToItemMap.
                        itemIndex = itemNames.indexOf(itemName);
                    } else {
                        // item does not exist, add it to the itemNames array
                        itemNames.push(itemName);
                        itemIndex = itemNames.length - 1;
                    }
                    fileIndexToItemNameMap[fileIndex] = itemIndex;
                    fileNamesToItemMap[file.name] = itemIndex;
                    fileNamesToFileIndexMap[file.name] = fileIndex;

                } else {
                    // is an image file. Store it in a separate dict for now
                    // remove the .pdf extension because the LaTeX only maps to
                    // filename
                    imageFiles[file.name.replace('.pdf', '').toLowerCase()] = fileIndex;
                }

            });

            // here make the forms. Include the metadata values from *.meta
            // so the user can verify that the right data was in the file.
            _.each(itemNames, function (itemName, index) {
                // also scan the *.tex files for figures
                var metadataAttrs = [],     // send this in the FormData
                    myFiles = [],
                    myFileObjs = [],        // send this in the FormData
                    questionLatex,
                    questionPreview, solutionLatex, solutionPreview,
                    metadataFile, compiledTemplate,
                    reader;

                // get the files associated with this item from fileNamesToItemMap
                _.each(fileNamesToItemMap, function (itemIndex, fileName) {
                    if (itemIndex === index) {
                        myFiles.push(fileName);
                    }
                });

                _.each(myFiles, function(myFileName) {
                    // account for non .pdf files...like .doc
                    // but blacklist a set of useless files
                    // generated in tex process.
                    var fileName, blacklist;

                    blacklist = ['.bak','.aux','.log','.synctex.gz','.synctex'];
                    if (!blacklist.some(function (extension) {
                        return myFileName.indexOf(extension) >= 0;
                    })) {
                        if (myFileName.indexOf('_Sol') >= 0 &&
                            myFileName.indexOf('.tex') < 0) {
                            solutionPreview = myFileName;
                            fileName = 'solutionPreview';
                        } else if (myFileName.indexOf('_Sol.tex') >= 0) {
                            solutionLatex = myFileName;
                            fileName = 'solutionLatex';
                            // scan the latex for images
                            reader = new FileReader();
                            reader.onload = function (e) {
                                var lines = e.target.result.split('\n'),
                                    figureNames = [],
                                    template, figureName;
                                _.each(lines, function (line) {
                                    if (line.indexOf('includegraphics') >= 0 &&
                                        line[0] !== '%') {
                                        figureName = extractFigureName(line);
                                        figureNames.push(figureName);
                                        myFileObjs.push({
                                            "fileName"  : figureName,
                                            "fileObj"   : files[imageFiles[figureName.replace('.pdf','').toLowerCase()]]
                                        });
                                    }
                                });

                                metadataAttrs.push({
                                    'attr': 'solutionLatex',
                                    'value': e.target.result
                                });

                                if (figureNames.length > 0) {
                                    template = _.template(ItemFiguresTemplate, {
                                        figureNames     : figureNames,
                                        imageFiles      : imageFiles
                                    });

                                    $('div.' + itemName).find('ul.figures-list')
                                        .append(template);
                                    $('div.' + itemName).find('ul.figures-list')
                                        .find('div.alert.alert-info')
                                        .remove();
                                }

                                // check if should show the Submit button
                                if (checkSubmitEligibility(itemName)) {
                                    attachSubmitFormData(itemName,
                                                         metadataAttrs,
                                                         myFileObjs);
                                }
                            };
                            reader.readAsText(files[fileNamesToFileIndexMap[myFileName]]);

                        } else if (myFileName.indexOf('.meta') >= 0) {
                            metadataFile = myFileName;
                            fileName = 'metadata';
                            reader = new FileReader();
                            reader.onload = function (e) {
                                var lines = e.target.result.split('\n'),
                                    template;
                                _.each(lines, function (line) {
                                    if (line !== '' && line[0] !== '%') {
                                        var attr = extractMetadataAttribute(line),
                                            attr_lc = attr.toLowerCase(),
                                            value = extractTextBetweenCurlyBraces(line),
                                            metadata = {
                                                'attr': attr,
                                                'value': value
                                            };
                                        if (attr_lc === 'difficulty' &&
                                            ['low','medium','hard'].indexOf(value) < 0) {
                                            metadata['error'] = true;
                                        } else if (attr_lc === 'qtype' &&
                                            ['long','concept','mcq','true/false','code'].indexOf(value) < 0) {
                                            metadata['error'] = true;
                                        } else if (attr_lc === 'term' &&
                                            (value.split(',').length !== 2 &&
                                                value.length > 0)) {
                                            metadata['error'] = true;
                                        } else if (attr_lc === 'pset' &&
                                            (value.split(',').length !== 2 &&
                                                value.length > 0)) {
                                            metadata['error'] = true;
                                        }
                                        if (value === '' &&
                                            (attr_lc === 'term' ||
                                             attr_lc === 'pset' ||
                                             attr_lc === 'subbranch')) {
                                            // do nothing if blank value passed in
                                            // for optional params
                                        } else {
                                            metadataAttrs.push(metadata);
                                        }
                                    }
                                });
                                template = _.template(MetadataAttributesTemplate, {
                                    metadataAttrs: metadataAttrs
                                });
                                $('div.' + itemName).find('ul.metadata-attrs-list')
                                    .append(template);

                                // check if should show the Submit button
                                if (checkSubmitEligibility(itemName)) {
                                    attachSubmitFormData(itemName,
                                                         metadataAttrs,
                                                         myFileObjs);
                                }
                            };

                            reader.readAsText(files[fileNamesToFileIndexMap[myFileName]]);
                        } else if (myFileName.indexOf('.tex') >= 0) {
                            questionLatex = myFileName;
                            fileName = 'latex';
                            // scan the latex for images
                            reader = new FileReader();
                            reader.onload = function (e) {
                                var lines = e.target.result.split('\n'),
                                    figureNames = [],
                                    template, figureName;
                                _.each(lines, function (line) {
                                    if (line.indexOf('includegraphics') >= 0 &&
                                        line[0] !== '%') {
                                        figureName = extractFigureName(line);
                                        figureNames.push(figureName);
                                        myFileObjs.push({
                                            "fileName"  : figureName,
                                            "fileObj"   : files[imageFiles[figureName.replace('.pdf','').toLowerCase()]]
                                        });
                                    }
                                });

                                metadataAttrs.push({
                                    'attr'  : 'latex',
                                    'value' : e.target.result
                                });

                                if (figureNames.length > 0) {
                                    template = _.template(ItemFiguresTemplate, {
                                        figureNames     : figureNames,
                                        imageFiles      : imageFiles
                                    });
                                    $('div.' + itemName).find('ul.figures-list')
                                        .append(template);
                                    $('div.' + itemName).find('ul.figures-list')
                                        .find('div.alert.alert-info')
                                        .remove();
                                }

                                // check if should show the Submit button
                                if (checkSubmitEligibility(itemName)) {
                                    attachSubmitFormData(itemName,
                                                         metadataAttrs,
                                                         myFileObjs);
                                }
                            };
                            reader.readAsText(files[fileNamesToFileIndexMap[myFileName]]);
                        } else {
                            questionPreview = myFileName;
                            fileName = 'preview';
                        }

                        if (fileName !== 'latex' && fileName !== 'solutionLatex') {
                            myFileObjs.push({
                                "fileName": fileName,
                                "fileObj": files[fileNamesToFileIndexMap[myFileName]]
                            });
                        }
                    }

                });
                // now compile the template and append it to
                // the div.item-grouping-wrapper
                compiledTemplate = _.template(ItemUploadFormTemplate, {
                    itemName            : itemName,
                    metadataFileName    : metadataFile,
                    questionLatex       : questionLatex,
                    questionPreview     : questionPreview,
                    solutionLatex       : solutionLatex,
                    solutionPreview     : solutionPreview
                });
                $('div.item-grouping-wrapper').append(compiledTemplate);
                checkSubmitEligibility(itemName);
            });

            if (typeof files !== 'undefined') {
                $uploadActions.removeClass('hidden');
            }

            return this;
        },
        events: {
            'click button.upload-all-btn'       : 'uploadAllItems'
        },
        uploadAllItems: function (e) {
            var itemSubmitBtns = $('button.upload-item-button:visible'),
                totalItems = itemSubmitBtns.length,
                progressBar = $('div.progress-bar'),
                progressText = $('div.progress-text'),
                uploadBtn = $(e.currentTarget);

            uploadBtn.addClass('hidden');

            progressBar.width('0%');
            progressText.html('0 / ' + totalItems);

            _.each(itemSubmitBtns, function (btn) {
                $(btn).trigger('click');
            });

            Admin.processing();
        }
    });

    return UploadItemsContentView;
});
