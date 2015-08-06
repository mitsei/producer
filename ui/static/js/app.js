// Filename: app.js

define([
  'jquery',
  'underscore',
  'backbone',
  'marionette',
  'regions',
  'jquery-ui'
], function($, _, Backbone, Marionette, RegionContainer){
    var ProducerManager = new Marionette.Application();

    ProducerManager.navigate = function(route,  options){
        options || (options = {});
        Backbone.history.navigate(route, options);
    };

    ProducerManager.getCurrentRoute = function(){
        return Backbone.history.fragment
    };

    ProducerManager.startSubApp = function(appName, args){
        var currentApp = appName ? ProducerManager.module(appName) : null;
        if (ProducerManager.currentApp === currentApp){ return; }

        if (ProducerManager.currentApp){
          ProducerManager.currentApp.stop();
        }

        ProducerManager.currentApp = currentApp;
        if(currentApp){
          currentApp.start(args);
        }
    };

    ProducerManager.on('before:start', function () {
        ProducerManager.regions = new RegionContainer();
    });

    ProducerManager.on('start', function () {
        if (Backbone.history) {
            require(["apps/dashboard/dashboard_app"], function () {
                if (ProducerManager.getCurrentRoute() === "") {
                    $("#login_tabs").tabs();
                }

                ProducerManager.Routers.trigger('start');

                Backbone.history.start();
            });
        }
    });

    return ProducerManager;
});