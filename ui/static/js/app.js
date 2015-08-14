// Filename: app.js

define([
  'jquery',
  'underscore',
  'backbone',
  'marionette',
  'regions',
  'socketio',
  'apps/common/utilities',
  'jquery-ui'
], function($, _, Backbone, Marionette, RegionContainer, io, Utils){
    var ProducerManager = new Marionette.Application();

    ProducerManager.navigate = function(route,  options){
        options || (options = {});
        Backbone.history.navigate(route, options);
    };

    ProducerManager.getCurrentRoute = function(){
        return Backbone.history.fragment
    };

    ProducerManager.startSubApp = function(appName, args){
//        var currentApp = appName ? ProducerManager.module(appName) : null;
//        if (ProducerManager.currentApp === currentApp){ return; }
//
//        if (ProducerManager.currentApp){
//          ProducerManager.currentApp.stop();
//        }
//
//        ProducerManager.currentApp = currentApp;
//        if(currentApp){
//          currentApp.start(args);
//        }
        var app = ProducerManager.module(appName);
        if (app) {
            app.start(args);
        }
    };

    ProducerManager.on('before:start', function () {
        var socketBaseUrl = window.location.protocol + '//' + window.location.hostname + ':8080/',
            conn = io.connect(socketBaseUrl);

        ProducerManager.regions = new RegionContainer();

        conn.on('message', function (obj) {
            var msg = JSON.parse(obj);
            console.log(obj);

            // parse the message, and do something -- hand off to a
            // notification view?
            if (msg.username === Utils.activeUser || msg.username === "all") {
                if (msg.hasOwnProperty('status')) {
                    if (msg.status === 'success') {
                        ProducerManager.vent.trigger('msg:success',
                            msg);
                    } else if (msg.status === 'error') {
                        ProducerManager.vent.trigger('msg:error',
                            msg);
                    }
                } else {
                    ProducerManager.vent.trigger("msg:status",
                        msg);
                }
            }
        });
    });

    ProducerManager.on('start', function () {
        if (Backbone.history) {
            require(["apps/dashboard/dashboard_app",
                     "apps/navbar/navbar_app",
                     "apps/notification/notification_app"], function () {
                if ($("#login_tabs").length > 0) {
                    $("#login_tabs").tabs();
                }

                ProducerManager.Routers.trigger('start');
//                ProducerManager.startSubApp("NavbarApp");

                Backbone.history.start();
            });
        }
    });

    return ProducerManager;
});