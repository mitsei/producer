//Filename: views/project/dashboard_content_navbar.js

define([
    'jquery',
    'underscore',
    'backbone'
], function ($, _, Backbone) {
    var DashboardView = Backbone.View.extend({
//        el: $('#dashboard_content_navbar'),
        className: 'dashboard-content-navbar',
        initialize: function () {
            $('#dashboard_content_navbar').empty()
                .append(this.$el);
            return this;
        }
    });

    return DashboardView;
});