// apps/navbar/views/navbar_views.js

define(["app",
        "apps/common/utilities",
        "text!apps/navbar/templates/import_course.html",
        "csrf",
        "jquery-ui"],
       function(ProducerManager, Utils, ImportCourseTemplate, csrftoken){
  ProducerManager.module("NavbarApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.NavbarView = Marionette.ItemView.extend({
        template: false,
        el: 'nav.navbar',
        events: {
            'click .repositories-menu li a' : 'loadRepoCourses',
            'click button.import-course.repository-btn': 'importNewCourse'
        },
        importNewCourse: function () {
            var _this = this;
            console.log('importing a course');

            // close the drawer if it is open
            if ($('#search-components-menu').hasClass('open')) {
                $('#search-components-menu').drawer('hide');
            }

            ProducerManager.regions.dialog.show(new View.ImportCourseDialogView({}));
            ProducerManager.regions.dialog.$el.dialog({
                modal: true,
                width: 500,
                height: 400,
                close: function (e, ui) {
                },
                title: 'Import a new course',
                buttons: [
                    {
                        text: "Cancel",
                        class: 'btn btn-danger',
                        click: function () {
                            $(this).dialog("close");
                        }
                    },
                    {
                        text: "Upload",
                        class: 'btn btn-success',
                        click: function () {
                            var formEl = $('#uploadItemForm'),
                                targetUrl = '/api/v1/repository/repositories/' + Utils.selectedRepoId() + '/upload/',
                                xhr = new XMLHttpRequest();
                            formEl.find('input[name="csrfmiddlewaretoken"]').val(csrftoken);

                            var form = new FormData(formEl[0]);

                            xhr.open("POST", targetUrl);
                            xhr.send(form);

                            ProducerManager.vent.trigger("msg:status",
                                "Your course is being processed, and you will be notified " +
                                    "when it has finished.");
                            $(this).dialog("close");
                        }
                    }
                ]
            });
            Utils.bindDialogCloseEvents();
            $('input[name="fileSelector"]').on('change', function () {
                _this.loadFileNamePreview(this);
            });
        },
        loadFileNamePreview: function (obj) {
            var filename = obj.files[0].name;
            $('div.selected-file-name').removeClass('hidden')
                .html('<strong>Selected:</strong> ' + filename);
        },
        loadRepoCourses: function () {
            console.log('here in view event manager');
            require(["apps/common/utilities"], function (Utils) {
              $(".repositories-menu li a").on('click', function () {
                  Utils.fixDomainSelector($(this).attr('href'));
              });
            });
        }
    });

    View.ImportCourseDialogView = Marionette.ItemView.extend({
        template: function () {
            return _.template(ImportCourseTemplate)();
        }
    });
  });

  return ProducerManager.NavbarApp.View;
});