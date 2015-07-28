// Filename: main.js

if (window.location.protocol === 'http:') {
    var baseUrl = '/static/js/';
} else {
    var baseUrl = '/static/js/';  // unnecessary?
}

require.config({
    baseUrl: baseUrl,
    paths: {
        'admin-utils'           : 'utilities/admin',
        'assignment-utils'      : 'utilities/assignmentUtilities',
        'backbone'              : 'vendor/backbone/backbone',
        'bloodhound'            : 'vendor/typeahead.js/dist/bloodhound.min',
        'bootstrap'             : 'vendor/bootstrap/dist/js/bootstrap.min',
        'bootstrap-dialog'      : 'vendor/bootstrap3-dialog/dist/js/bootstrap-dialog.min',
        'bootstrap-switch'      : 'vendor/bootstrap-switch/dist/js/bootstrap-switch.min',
        'csrf'                  : 'vendor/csrf',
        'item-utils'            : 'utilities/itemUtilities',
        'jquery'                : 'vendor/jquery/dist/jquery.min',
        'jquery-ui'             : 'vendor/jqueryui/jquery-ui.min',
        'metadata-utils'        : 'utilities/metadataUtilities',
        'select2'               : 'vendor/select2/select2.full.min',  // 4.0.0.rc2
//        'select2'               : 'vendor/select2/select2.min', // 3.5.2
        'sidebar-utils'         : 'utilities/sidebarUtilities',
        'tex-utils'             : 'utilities/texUtilities',
        'typeahead'             : 'vendor/typeahead.js/dist/typeahead.jquery.min',
        'underscore'            : 'vendor/lodash/dist/lodash.min'
    },
    shim: {
        'admin-utils': {
            deps: ['jquery', 'underscore'],
            exports: 'Admin'
        },
        'assignment-utils': {
            deps: ['jquery','underscore','admin-utils', 'item-utils'],
            exports: 'Assignment'
        },
        'backbone': {
            deps: ['underscore', 'jquery'],
            exports: 'Backbone'
        },
        'bootstrap': {
            deps: ['jquery']
        },
        'bootstrap-dialog': {
            deps: ['bootstrap','jquery'],
            exports: 'BootstrapDialog'
        },
        'bootstrap-switch': {
            deps: ['bootstrap','jquery']
        },
        'csrf': {
            deps: ['jquery']
        },
        'item-utils': {
            deps: ['jquery','underscore','admin-utils', 'tex-utils'],
            exports: 'Item'
        },
        'jquery-ui': {
            deps: ['jquery']
        },
        'metadata-utils': {
            deps: ['jquery','underscore'],
            exports: 'Metadata'
        },
        'select2': {
            deps: ['jquery']
        },
        'sidebar-utils': {
            deps: ['jquery', 'jquery-ui', 'underscore', 'admin-utils'],
            exports: 'Sidebar'
        },
        'tex-utils' : {
            deps: ['jquery', 'underscore'],
            exports: 'Tex'
        },
        'typeahead' : {
            deps: ['jquery','bloodhound']
        }
    }
});
require(['app'], function(App) {
    App.initialize();
    require(['views/project/login']);
    require(['views/project/dashboard']);
    require(['views/project/dashboard_sidebar']);
//    require(['views/project/dashboard_content_navbar']);
});