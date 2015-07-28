//Filename: views/project/mySubjectContentNavbar.js

define([
    'jquery',
    'underscore',
    'backbone',
    'views/project/buildNewAssignmentContent',
    'views/project/createNewItemContent',
    'views/project/editPublishedItemsContent',
    'views/project/manageUsersContent',
    'views/project/managePendingItemsContent',
    'views/project/uploadItemsContent',
    'views/project/manageGeneralAssets',
    'text!templates/subjectDetailsContentNavbar.html'
], function ($, _, Backbone,
             BuildNewAssignmentContentView, CreateNewItemContentView,
             EditPublishedItemsContentView, ManageUsersContentView,
             ManagePendingItemsContentView, UploadItemsContentView,
             ManageGeneralAssetsContentView,
             SubjectDetailsContentNavbarTemplate) {
    var MySubjectContentNavbarView = Backbone.View.extend({
//        el: $('#dashboard_content_navbar'),
        className: 'my-subject-content-navbar',
        initialize: function () {
            return this;
        },
        render: function (options) {
            var compiledTemplate = _.template(SubjectDetailsContentNavbarTemplate, {
                faculty : options['isFaculty']
            });

            this.$el.html(compiledTemplate);

            $('#dashboard_content_navbar').empty()
                .append(this.$el);

            this.$el.find('.upload-items').click();
            return this;
        },
        events: {
            'click .build-assignments'      : 'buildNewAssignment',
            'click .create-item'            : 'createNewItem',
            'click .published-items'        : 'editPublishedItems',
            'click .manage-assets'          : 'manageAssets',
            'click .manage-users'           : 'manageUsers',
            'click .upload-items'           : 'uploadNewItems'
        },
        buildNewAssignment: function (e) {
            var content = new BuildNewAssignmentContentView();

            this.$el.find('button').removeClass('active');
            $(e.target).addClass('active');

            content.render();
        },
        editPublishedItems: function (e) {
            var content = new EditPublishedItemsContentView();

            this.$el.find('button').removeClass('active');
            $(e.target).addClass('active');

            content.render();
        },
        manageAssets: function (e) {
            var content = new ManageGeneralAssetsContentView();

            this.$el.find('button').removeClass('active');
            $(e.target).addClass('active');

            content.render();
        },
        manageUsers: function (e) {
            var content = new ManageUsersContentView();

            this.$el.find('button').removeClass('active');
            $(e.target).addClass('active');

            content.render();
        },
        uploadNewItems: function (e) {
            var content = new UploadItemsContentView();

            this.$el.find('button').removeClass('active');
            $(e.target).addClass('active');

            content.render();
        }
    });

    return MySubjectContentNavbarView;
});