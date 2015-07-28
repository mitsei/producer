//Filename: views/project/otherSubjectContent.js

define([
    'jquery',
    'underscore',
    'backbone',
    'text!templates/subjectOwnersContent.html'
], function ($, _, Backbone, SubjectOwnersContentTemplate) {
    var OtherSubjectContentView = Backbone.View.extend({
        className: 'other-subject-content',
        initialize: function (options) {
            if (typeof options !== 'undefined' &&
                options.hasOwnProperty('owners')) {
                var owners = options['owners'];
                if (owners.constructor === Array) {
                    this.owners = owners;
                } else {
                    this.owners = [owners];
                }
            }

            return this;
        },
        render: function () {
            var compiledTemplate = _.template(SubjectOwnersContentTemplate, {
                'owners'    : this.owners
            });
            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);
            return this;
        }
    });

    return OtherSubjectContentView;
});