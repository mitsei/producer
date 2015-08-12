// Filename: main.js

var baseUrl = '/static/js/';
var socketioPath = window.location.protocol + '//' + window.location.hostname + ':8080/socket.io/socket.io';

requirejs.config({
    baseUrl: baseUrl,
    paths: {
        'backbone'              : 'vendor/backbone/backbone',
        'backbone.babysitter'   : 'vendor/backbone.babysitter/lib/backbone.babysitter.min',
        'backbone.radio'        : 'vendor/backbone.radio/build/backbone.radio.min',
        'bootstrap'             : 'vendor/bootstrap/dist/js/bootstrap.min',
        'bootstrap-dialog'      : 'vendor/bootstrap3-dialog/dist/js/bootstrap-dialog.min',
        'csrf'                  : 'vendor/csrf',
        'jquery'                : 'vendor/jquery/dist/jquery.min',
        'jquery-ui'             : 'vendor/jqueryui/jquery-ui.min',
        'marionette'            : 'vendor/marionette/lib/backbone.marionette.min',
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
        'csrf': {
            deps: ['jquery']
        },
        'jquery-ui': {
            deps: ['jquery']
        },
        'marionette': {
            deps: ['backbone'],
            exports: 'Marionette'
        }
    }
});
requirejs(['app'], function(ProducerApp) {
    ProducerApp.start();
});