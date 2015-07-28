//Filename: views/project/otherSubjectContentNavbar.js

define([
    'jquery',
    'underscore',
    'backbone',
    'text!templates/subjectOwnersContentNavbar.html'
], function ($, _, Backbone, SubjectOwnersContentNavbarTemplate) {
    var OtherSubjectContentNavbarView = Backbone.View.extend({
        className: 'other-subject-content-navbar',
        initialize: function (options) {
            if (typeof options !== 'undefined' &&
                options.hasOwnProperty('displayName')) {
                this.displayName = options['displayName'];
            }

            return this;
        },
        render: function () {
            var compiledTemplate = _.template(SubjectOwnersContentNavbarTemplate, {
                'displayName'    : this.displayName
            });
            this.$el.html(compiledTemplate);

            $('#dashboard_content_navbar').empty()
                .append(this.$el);

            return this;
        }
    });

    return OtherSubjectContentNavbarView;
});