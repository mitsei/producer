// apps/navbar/views/navbar_views.js

define(["app",
        "apps/common/utilities",
        "apps/dashboard/domains/models/repository",
        "text!apps/navbar/templates/import_course.html",
        "text!apps/navbar/templates/new_domain.html",
        "text!apps/navbar/templates/domain_selector.html",
        "csrf",
        "jquery-ui"],
       function(ProducerManager, Utils, RepositoryModel,
                ImportCourseTemplate, NewDomainTemplate,
                DomainSelectorTemplate, csrftoken){
  ProducerManager.module("NavbarApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.NavbarView = Marionette.ItemView.extend({
        template: false,
        el: 'nav.navbar',
        events: {
            'click .add-new-domain': 'createNewDomain',
            'click .repositories-menu li a:not(.add-new-domain)' : 'loadRepoCourses',
            'click button.import-course.repository-btn': 'importNewCourse'
        },
        closeDrawer: function () {
            // close the drawer if it is open
            if ($('#search-components-menu').hasClass('open')) {
                $('#search-components-menu').drawer('hide');
            }
        },
        createNewDomain: function (e) {
            var _this = this;
            console.log('creating a domain');

            _this.closeDrawer();

            ProducerManager.regions.dialog.show(new View.NewDomainDialogView({}));
            ProducerManager.regions.dialog.$el.dialog({
                modal: true,
                width: 500,
                height: 400,
                title: 'Create a new domain',
                buttons: [
                    {
                        text: "Cancel",
                        class: 'btn btn-danger',
                        click: function () {
                            $(this).dialog("close");
                        }
                    },
                    {
                        text: "Create",
                        class: 'btn btn-success',
                        click: function () {
                            var repo = new RepositoryModel(),
                                name = $('#newDomainName').val(),
                                desc = $('#newDomainDescription').val(),
                                _this = this;

                            repo.set('displayName', name);
                            repo.set('description', desc);
                            repo.set('genusTypeId', Utils.domainGenus());
                            repo.save()
                                .success(function (model, response, options) {
                                    ProducerManager.vent.trigger("msg:status",
                                        "Domain created");
                                    $('ul.repositories-menu').prepend(_.template(DomainSelectorTemplate)({
                                        repoDisplayName: model.displayName.text,
                                        repoId: model.id,
                                        repoSlug: Utils.slugify(model.displayName.text)
                                    }));
                                }).error(function (model, xhr, options) {
                                    ProducerManager.vent.trigger("msg:error",
                                        xhr.responseText);
                                }).always(function () {
                                    $(_this).dialog("close");
                                });
                        }
                    }
                ]
            });
            Utils.bindDialogCloseEvents();
            $('input[name="fileSelector"]').on('change', function () {
                _this.loadFileNamePreview(this);
            });
        },
        importNewCourse: function () {
            var _this = this;
            console.log('importing a course');

            _this.closeDrawer();

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
            Utils.processing();
            require(["apps/common/utilities"], function (Utils) {
              Utils.doneProcessing();
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

    View.NewDomainDialogView = Marionette.ItemView.extend({
        template: function () {
            return _.template(NewDomainTemplate)();
        }
    });
  });

  return ProducerManager.NavbarApp.View;
});