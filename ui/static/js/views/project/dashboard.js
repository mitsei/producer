//Filename: views/project/dashboard.js

define([
    'jquery',
    'underscore',
    'backbone',
    'views/project/quickGuide'
], function ($, _, Backbone, QuickGuideView) {
    var DashboardView = Backbone.View.extend({
//        el: $('#main_container'),
        className: 'dashboard-main-content',
        initialize: function () {
            var guide = new QuickGuideView();
            return this;
        }
    });

    return DashboardView;
});