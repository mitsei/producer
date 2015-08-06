//Filename: apps/navbar/views/navbar/navbarHome.js

define([
    'jquery',
    'underscore',
    'marionette',
    'text!templates/navbarHome.html'
], function ($, _, Marionette, NavbarTemplate) {
    var NavbarView = Marionette.View.extend({
        el: $('#home_navbar'),
        initialize: function () {
            var compiledTemplate, path;
            path = window.location.pathname;
            if (path.indexOf('/login') >= 0 || path === '/') {
                // do nothing
            } else {
                if (path.indexOf('/touchstone') > 0) {
                    compiledTemplate = _.template(NavbarTemplate, {
                        touchstone: true
                    });
                } else {
                    compiledTemplate = _.template(NavbarTemplate, {
                        touchstone: false
                    });
                }

                this.$el.html(compiledTemplate);
            }
            return this;
        }
    });

    return NavbarView;
});