//Filename: views/navbar/navbar.js

define([
    'jquery',
    'underscore',
    'backbone',
    'text!templates/navbar.html'
], function ($, _, Backbone, NavbarTemplate) {
    var NavbarView = Backbone.View.extend({
        className: 'my-content-navbar',
//        el: $('#content_navbar'),
        initialize: function () {
            var compiledTemplate;
            compiledTemplate = _.template(NavbarTemplate, {});
            this.$el.html(compiledTemplate);
            $('#content_navbar').empty()
                .append(this.$el);
            return this;
        }
    });

    return NavbarView;
});