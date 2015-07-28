// Assignment utilities
// File: utilities/assignmentUtilities.js

define(['jquery',
        'underscore',
        'admin-utils',
        'item-utils'],
    function ($, _, Admin, Item) {
        var _assignment = {};

        _assignment.createAssessmentAjax = function (myForm, errorMethod, successCallback) {
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

        _assignment.handleNewAssessments = function (itemId, _callback) {
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

                    _assignment.createAssessmentAjax(assessmentCreateForm,
                        Admin.reportError,
                        function (assessmentData) {
                            Item.attachItemToAssessmentAjax(assessmentAddItemForm,
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

        _assignment.lock = function (assignmentId) {
            $.ajax({
                type: 'PATCH',
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' + assignmentId + '/lock/'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                console.log('Locked assignment ' + assignmentId + ' for editing.');
            });
        };

        _assignment.publish = function (assignmentId) {
            $.ajax({
                type: 'PATCH',
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' + assignmentId + '/publish/'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                console.log('Published assignment ' + assignmentId + '.');
            });
        };

        _assignment.unlock = function (assignmentId, suppress) {
            suppress = typeof suppress === 'undefined' ? false : suppress;
            $.ajax({
                type: 'PATCH',
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assessments/' + assignmentId + '/unlock/'
            }).error( function (xhr, msg, status) {
                if (!suppress) {
                    Admin.updateStatus('Server error: ' + xhr.responseText);
                }
            }).success( function (data) {
                console.log('Unlocked assignment ' + assignmentId + '.');
            });
        };


        return _assignment;
});
