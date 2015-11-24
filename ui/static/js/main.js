// Filename: main.js

var baseUrl = '/static/js/';
if (window.location.hostname == 'localhost' || window.location.hostname == '127.0.0.1') {
    var socketioPath = window.location.protocol + '//' + window.location.hostname + ':8888/socket.io/socket.io';
} else {
    var socketioPath = window.location.protocol + '//' + window.location.hostname + '/socket.io/socket.io';
}
var enableNotifications = true;

requirejs.config({
    baseUrl: baseUrl,
    paths: {
        'backbone'              : 'vendor/backbone/backbone-min',
        'backbone.babysitter'   : 'vendor/backbone.babysitter/lib/backbone.babysitter.min',
        'backbone.radio'        : 'vendor/backbone.radio/build/backbone.radio.min',
        'bootstrap'             : 'vendor/bootstrap/dist/js/bootstrap.min',
        'bootstrap-dialog'      : 'vendor/bootstrap3-dialog/dist/js/bootstrap-dialog.min',
        'bootstrap-drawer'      : 'vendor/bootstrap-drawer/dist/js/drawer.min',
        'cookies'               : 'vendor/js-cookie/src/js.cookie',
        'csrf'                  : 'vendor/csrf',
        'jquery'                : 'vendor/jquery/dist/jquery.min',
        'jquery-bootpag'        : 'vendor/jquery-bootpag/lib/jquery.bootpag.min',
        'jquery-sortable'       : 'vendor/jquery-sortable/source/js/jquery-sortable-min',
        'jquery-ui'             : 'vendor/jqueryui/jquery-ui.min',
        'marionette'            : 'vendor/marionette/lib/backbone.marionette.min',
        'mathjax'               : 'https://edx-static.s3.amazonaws.com/mathjax-MathJax-727332c/MathJax.js?config=TeX-MML-AM_HTMLorMML-full',
        'socketio'              : socketioPath,
        'underscore'            : 'vendor/lodash/lodash.min'
    },
    shim: {
        'backbone': {
            deps: ['underscore', 'jquery'],
            exports: 'Backbone'
        },
        'backbone.babysitter': {
            deps: ['backbone']
        },
        'backbone.radio': {
            deps: ['backbone']
        },
        'bootstrap': {
            deps: ['jquery']
        },
        'bootstrap-dialog': {
            deps: ['bootstrap'],
            exports: 'BootstrapDialog'
        },
        'bootstrap-drawer': {
            deps: ['jquery', 'bootstrap']
        },
        'cookies': {
            exports: 'Cookies'
        },
        'csrf': {
            deps: ['jquery'],
            exports: 'csrftoken'
        },
        'jquery-bootpag': {
            deps: ['jquery', 'bootstrap']
        },
        'jquery-sortable': {
            deps: ['jquery']
        },
        'jquery-ui': {
            deps: ['jquery']
        },
        'marionette': {
            deps: ['backbone'],
            exports: 'Marionette'
        },
        'mathjax': {
            exports: 'MathJax'
        }
    }
});
requirejs(['app'], function(ProducerApp) {
    ProducerApp.start();
});