// Sidebar utility methods
// File: utilities/sidebarUtilities.js

define(['jquery',
        'underscore',
        'admin-utils',
        'jquery-ui'],
    function ($, _, Admin) {
    var _sidebar = {};

    _sidebar.otherSubjects = function (_callback) {
        _sidebar.subjects(_callback, {'param':'other'});
    };

    _sidebar.saveSubject = function (payload, _callback) {
        var method = 'POST',
            options = {
                'method'        : method,
                'payload'       : payload
            };

        _sidebar.subjects(_callback, options);
    };

    _sidebar.subjects = function (_callback, options) {
        var urlOption = '',
            method = 'GET',
            payload = {};

        if (typeof(options) !== 'undefined') {
            if (options.hasOwnProperty('param')) {
                urlOption = '?' + options['param'];
            }

            if (options.hasOwnProperty('method')) {
                method = options['method'];
            }

            if (options.hasOwnProperty('payload')) {
                payload = options['payload'];
            }
        }
        $.ajax({
            url     : Admin.api() + 'subjects/' + urlOption,
            type    : method,
            data    : payload
        }).error( function (xhr, status, msg) {
            Admin.updateStatus('Server error: ' + xhr.responseText);
        }).success( function (data) {
            _callback(data);
        });
    };

    _sidebar.userSubjects = function (_callback) {
        _sidebar.subjects(_callback, {'param':'mine'})
    };

    return _sidebar;
});
