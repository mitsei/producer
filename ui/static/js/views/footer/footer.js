//Filename: views/footer/footer.js

define([
    'jquery',
    'underscore',
    'backbone',
    'text!templates/footer.html'
], function ($, _, Backbone, FooterTemplate) {
    var FooterView = Backbone.View.extend({
        el: $('#footer'),
        initialize: function () {
            var compiledTemplate = _.template(FooterTemplate, {});
            this.$el.html(compiledTemplate);
            return this;
        }
    });

    return FooterView;
});