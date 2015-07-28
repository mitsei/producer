//Filename: views/project/dashboard_sidebar.js
// manages the class listings for user

define([
    'jquery',
    'underscore',
    'backbone',
    'views/project/dashboard_content_navbar',
    'views/project/otherSubjectContent',
    'views/project/otherSubjectContentNavbar',
    'views/project/mySubjectContentNavbar',
    'views/project/dashboard',
    'admin-utils',
    'sidebar-utils',
    'bootstrap-dialog',
    'text!templates/myClassSelector.html',
    'text!templates/otherClasses.html',
    'text!templates/addSubjectTemplate.html',
    'jquery-ui',
    'select2',
    'csrf',
    'bootstrap'
], function ($, _, Backbone, ContentNavbarView,
             OtherSubjectContentView, OtherSubjectContentNavbarView,
             MySubjectContentNavbarView, DashboardView,
             Admin, Sidebar, BootstrapDialog,
             MyClassesTemplate, OtherClassesTemplate,
             AddSubjectTemplate) {

    function deactivateSubjects () {
        $('li.edit-subject').removeClass('active');
        $('li.view-subject-owners').removeClass('active');
    }

    var DashboardSidebarView = Backbone.View.extend({
//        el: $('#dashboard_sidebar_content'),
        className: 'dashboard-sidebar',
        initialize: function () {
            var compiledTemplate;

            compiledTemplate = _.template(MyClassesTemplate, {
                'mySubjects': []
            });
            compiledTemplate += _.template(OtherClassesTemplate, {
                'otherSubjects': []
            });

            this.$el.html(compiledTemplate);
            $('#dashboard_sidebar_content').empty()
                .append(this.$el);
            return this;
        },
        render: function () {
            // get current user's list of classes
            Sidebar.userSubjects(this.populateUserSubjects);
            Sidebar.otherSubjects(this.populateOtherSubjects);
        },
        events: {
            'click .add-subject'            : 'addSubjectModal',
            'click .edit-subject'           : 'viewSubjectDetails',
            'click .view-subject-owners'    : 'viewSubjectOwners'
        },
        addSubjectModal: function (e) {
            var modalTemplate = _.template(AddSubjectTemplate),
                $this = this;

            BootstrapDialog.show({
                title: 'Add Subject',
                message: modalTemplate,
                cssClass: 'add-subject-modal',
                onshow: function (dialog) {
                    Admin.removeBRs(dialog.$modalBody);
                    dialog.$modalBody.find('input[name="subjectName"]').focus();
                    dialog.$modalBody.find('select[name="courseNumber"]').select2({
                        dropdownAutoWidth: 'true'
                    });
                    dialog.$modalBody.find('select[name="subjectTerm"]').select2({
                        dropdownAutoWidth: 'true',
                        minimumResultsForSearch: -1
                    });
                },
                buttons: [
                    {
                        label: 'Cancel',
                        cssClass: 'btn-primary',
                        action: function (dialog) {
                            dialog.close();
                            console.log('Canceled.');
                        }
                    },
                    {
                        label: 'Save',
                        cssClass: 'btn-success',
                        action: function (dialog) {
                            var $m, subjectName, subjectNumber, subjectCourse,
                                subjectDescription, payload;

                            $m = dialog.$modalBody;

                            subjectCourse = $m.find('select[name="courseNumber"]').val();
                            subjectName = $m.find('input[name="subjectName"]').val();
                            subjectNumber = $m.find('input[name="subjectNumber"]').val();
                            subjectDescription = $m.find('textarea[name="subjectDescription"]').val();

                            if (subjectCourse === "0" ||
                                subjectName === "" ||
                                subjectNumber === "") {
                                $m.find('.modalStatusBox').text('Please fill in all the data.');
                            } else {
                                $m.find('.modalStatusBox').html('<i class="fa fa-spinner fa-spin"></i>' +
                                    ' Processing...');
                                payload = {
                                    'course'        : subjectCourse,
                                    'description'   : subjectDescription,
                                    'name'          : subjectName,
                                    'number'        : subjectNumber
                                };
                                Sidebar.saveSubject(payload,
                                    function () {
                                        $('.add-subject-modal').modal('hide');
                                        // re-render the sidebar
                                        $this.render();
                                        // clear out the content and top navbar
                                        $('span#dashboard_content_navbar').empty();
                                        new DashboardView();
                                    });
                            }
                        }
                    }
                ]
            });
        },
        populateOtherSubjects: function (data) {
            var otherSubjects = [];
            _.each(data['data']['results'], function (otherSubject) {
                otherSubject['rawObject'] = JSON.stringify(otherSubject).replace(/"/g, "&quot;");
                otherSubjects.push(otherSubject);
            });
            compiledTemplate = _.template(OtherClassesTemplate, {
                'otherSubjects': otherSubjects
            });
            $('section.other-classes').replaceWith(compiledTemplate);
        },
        populateUserSubjects: function (data) {
            var mySubjects = [];
            _.each(data['data']['results'], function (mySubject) {
                mySubject['rawObject'] = JSON.stringify(mySubject).replace(/"/g, "&quot;");
                mySubjects.push(mySubject);
            });
            compiledTemplate = _.template(MyClassesTemplate, {
                'mySubjects': mySubjects
            });
            $('section.my-classes').replaceWith(compiledTemplate);
        },
        viewSubjectDetails: function (e) {
            var subjectData = $(e.target).data('raw-object');
            var navbar = new MySubjectContentNavbarView(subjectData);
            $.ajax({
                url : Admin.api() + 'users/self/'
            }).error(function (xhr,status,msg) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success(function (data) {
                navbar.render({
                    isFaculty   : data['isFaculty']
                });
            });
            // Let the navbar pick / control the content in this case
            deactivateSubjects();
            $(e.target).addClass('active');
        },
        viewSubjectOwners: function (e) {
            var subjectData = $(e.target).data('raw-object');
            var content = new OtherSubjectContentView(subjectData);
            content.render();

            var navbar = new OtherSubjectContentNavbarView(subjectData);
            navbar.render();

            deactivateSubjects();
            $(e.target).addClass('active');
        }
    });

    var mySidebar = new DashboardSidebarView();
    mySidebar.render();
    return DashboardSidebarView;
});