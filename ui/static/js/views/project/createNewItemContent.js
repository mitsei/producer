//Filename: views/project/createNewItemContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'text!templates/createNewItem.html'
], function ($, _, Backbone, CreateNewItemTemplate) {
    var CreateNewItemContentView = Backbone.View.extend({
        el: $('#dashboard_main_content'),
        initialize: function (options) {
            var owners = options['owners'];
            if (owners.constructor === Array) {
                this.owners = owners;
            } else {
                this.owners = [owners];
            }

            return this;
        },
        render: function () {
            var compiledTemplate = _.template(SubjectOwnersContentTemplate, {
                'owners'    : this.owners
            });
            this.$el.html(compiledTemplate);
            return this;
        }
    });

    return CreateNewItemContentView;
});