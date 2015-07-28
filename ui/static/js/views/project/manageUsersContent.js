//Filename: views/project/manageUsersContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'admin-utils',
    'text!templates/manageUsers.html',
    'text!templates/facultyOwner.html',
    'text!templates/noFacultyOwnersFound.html',
    'text!templates/ta.html',
    'text!templates/noTAsFound.html',
    'typeahead'
], function ($, _, Backbone, Admin,
             ManageUsersTemplate, FacultyOwnerTemplate,
             NoFacultyOwnersFoundTemplate, TATemplate,
             NoTAsFoundTemplate) {

    function addUserAsOwner (userData, _callback) {
        // take userId + activeSubjectId and add the user as an owner
        $.ajax({
            url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/users/',
            type: 'POST',
            data: {
                userId  : userData.mecqbankId
            }
        }).error( function (xhr, status, msg) {
            Admin.updateStatus('Server error: ' + xhr.responseText);
        }).success( function (data) {
            _callback();
        });
    }

    function createUser (kerberos, _callback) {
        kerberos = kerberos.indexOf('@mit.edu') < 0 ? kerberos += '@mit.edu' : kerberos;

        $.ajax({
            url : Admin.api() + 'users/',
            type: 'POST',
            data: {
                faculty     : true,
                kerberos    : kerberos
            }
        }).error( function (xhr, status, msg) {
            Admin.updateStatus('Server error: ' + xhr.responseText);
        }).success( function (data) {
            _callback(data);
        });
    }

    function removeUserAsOwner (userId, _callback) {
        $.ajax({
            url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/users/' + userId + '/',
            type: 'DELETE'
        }).error( function (xhr, status, msg) {
            Admin.updateStatus('Server error: ' + xhr.responseText);
        }).success( function () {
            _callback();
        });
    }

    var ManageUsersContentView = Backbone.View.extend({
//        el: $('#dashboard_main_content'),
        className: 'my-subject-manage-users',
        initialize: function () {
            var compiledTemplate = _.template(ManageUsersTemplate),
                _this = this;

            _this.facultyOwners = [];
            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);

            // initialize the various search and drop-down tools

            // tie in faculty search to typeahead
            _this.facultyEngine = new Bloodhound({
                datumTokenizer  : Bloodhound.tokenizers.obj.whitespace('username'),
                queryTokenizer  : Bloodhound.tokenizers.whitespace,
                prefetch        : {
                    url : Admin.api() + 'users/?faculty',
                    filter: function (data) {
                        return _.filter(data, function (datum) {
                            return _this.facultyOwners.indexOf(datum['username']) < 0;
                        });
                    },
                    ttl: 1
                }
            });

            // get the current list of faculty owners
            $.ajax({
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/users/'
            }).error( function (xhr, status, msg) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                var $t = $('ul.faculty-owners-list');

                if (data.length > 0) {
                    _.each(data, function (datum) {
                        $t.append(_.template(FacultyOwnerTemplate, {
                            displayName     : datum.username,
                            rawObject       : Admin.rawObject(datum)
                        }));
                        _this.facultyOwners.push(datum.username);
                    });

                    _this.facultyEngine.initialize();
                    $('input[name="addFacultyInput"]').typeahead(null,{
                        name        : 'faculty-users',
                        displayKey  : 'username',
                        valueKey    : 'mecqbankId',
                        source      : _this.facultyEngine.ttAdapter()
                    });
                } else {
                    $t.append(_.template(NoFacultyOwnersFoundTemplate));
                }
            });

            // initialize the term selector
            $('select[name="taTermSelector"]').select2({
                dropdownAutoWidth   : 'true',
                placeholder : 'Select a term',
                ajax    : {
                    url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/terms/',
                    data: function (params) {
                        return {
                            q: params.term,
                            page: params.page
                        }
                    },
                    processResults: function (data, page) {
                        return {
                            results: data
                        };
                    }
                }
            });


            return this;
        },
        render: function () {
            return this;
        },
        events: {
            'change select[name="taTermSelector"]'      : 'showTAList',
            'change input.ta-selector'                  : 'toggleTAStatus',
            'click button.add-faculty-btn'              : 'addFacultyOwner',
            'click .remove-owner'                       : 'removeOwner',
            'keyup input[name="addFacultyInput"]'       : 'selectFirstName'
        },
        addFacultyOwner: function (e) {
            var $i = $('input[name="addFacultyInput"]'),
                $t = $('ul.faculty-owners-list'),
                kerberos = $i.val(),
                _this = this;

            if (kerberos === '') {
                Admin.updateStatus('Please select an existing user or type a new one.');
            } else {
                // create user POST should return user Id if already exists
                // then add user as owner, if not already in the list of owners
                Admin.processing();
                createUser(kerberos, function (data) {
                    addUserAsOwner(data, function () {
                        // reflect this in the UI, clear out the input field / re-initialize it?
                        $t.append(_.template(FacultyOwnerTemplate, {
                            displayName     : data.username,
                            rawObject       : Admin.rawObject(data)
                        }));
                        _this.facultyOwners.push(data.username);

                        // re-initialize Bloodhound engine and typeahead
                        _this.reinitializeTypeahead();
                        Admin.updateStatus('');
                    });
                });
            }
        },
        reinitializeTypeahead: function () {
            var $i = $('input[name="addFacultyInput"]'),
                _this = this;

            _this.facultyEngine.clearPrefetchCache();
            _this.facultyEngine.initialize(true);
            $i.typeahead('val', '');
        },
        removeOwner: function (e) {
            var $ele = $(e.currentTarget).parent(),
                userObj = $ele.data('raw-object'),
                username = userObj.username,
                userId = userObj.mecqbankId,
                _this = this;

            removeUserAsOwner(userId, function () {
                Admin.updateStatus(userObj.username + ' removed as owner of this subject.');
                $ele.remove();

                _this.facultyOwners = _.remove(_this.facultyOwners, function (owner) {
                    return owner !== username;
                });

                _this.reinitializeTypeahead();
            });
        },
        selectFirstName: function (e) {
            // http://stackoverflow.com/questions/26785109/select-first-suggestion-from-typeahead-js-when-hit-enter-key-in-the-field
            if(e.which == 13) {
                $(".tt-suggestion:first-child").trigger('click');
            }
        },
        showTAList: function (e) {
            var $t = $('ul.ta-term-list'),
                $e = $(e.currentTarget),
                term = $e.val();

            Admin.processing();
            $t.empty();

            $.ajax({
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/users/?term=' + term
            }).error( function (xhr, status, msg) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                data = _.remove(data, function (datum) {
                    return !datum.faculty;
                });

                if (data.length > 0) {
                    _.each(data, function (datum) {
                        $t.append(_.template(TATemplate, {
                            active      : datum.active,
                            displayName : datum.username,
                            rawObject   : Admin.rawObject(datum)
                        }));
                    });
                } else {
                    $t.append(_.template(NoTAsFoundTemplate));
                }

                Admin.updateStatus('');
            });
        },
        toggleTAStatus: function (e) {
            var $e = $(e.currentTarget),
                userObj = $e.parents('li.ta')
                    .data('raw-object'),
                active = $e.prop('checked');

            if (active) {
                addUserAsOwner(userObj, function () {
                    // do nothing.
                });
            } else {
                removeUserAsOwner(userObj.mecqbankId, function () {
                    // do nothing.
                });
            }
        }
    });

    return ManageUsersContentView;
});