//Filename: views/project/quickGuide.js

define([
    'jquery',
    'underscore',
    'backbone',
    'text!templates/quickGuide.html'
], function ($, _, Backbone, QuickGuideTemplate) {
    var QuickGuideView = Backbone.View.extend({
//        el: $('#dashboard_main_content'),
        className: 'dashboard-quick-guide',
        initialize: function () {
            var compiledTemplate = _.template(QuickGuideTemplate);
            this.$el.html(compiledTemplate);
            $('#dashboard_main_content').empty()
                .append(this.$el);
            return this;
        }
    });

    return QuickGuideView;
});