// apps/navbar/views/navbar_views.js

define(["app",
        "apps/common/utilities",
        "apps/dashboard/domains/models/repository",
        "apps/dashboard/domains/collections/domains",
        "text!apps/navbar/templates/import_course.html",
        "text!apps/navbar/templates/new_domain.html",
        "text!apps/navbar/templates/domain_selector.html",
        "text!apps/faceted-search/templates/domain_selector.html",
        "csrf",
        "cookies",
        "jquery-ui"],
       function(ProducerManager, Utils, RepositoryModel, DomainsCollection,
                ImportCourseTemplate, NewDomainTemplate,
                DomainSelectorTemplate, SearchDomainSelectorTemplate, csrftoken, Cookies){
  ProducerManager.module("NavbarApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.NavbarView = Marionette.ItemView.extend({
        template: false,
        el: 'nav.navbar',
        onRender: function () {
        },
        onShow: function () {
            var loc = window.location.href;

            if (loc.indexOf('#curate') >= 0) {
                this.updateActiveStatus($('button.repository-btn.curate-objects'));
            } else if (loc.indexOf('#edit') >= 0 ||
                loc.indexOf('#sandbox') >= 0 ||
                loc.indexOf('#') < 0) {
                this.updateActiveStatus($('button.repository-btn.sandbox'));
                this.loadUserCourses();
            }
        },
        updateActiveStatus: function ($el) {
            $('button.repository-btn.active').removeClass('active');

            $el.addClass('active');
        },
        events: {
            'click .add-new-domain': 'createNewDomain',
            'click .curate-objects': 'curateObjects',
            'click .import-course': 'importNewCourse',
            'click .sandbox': 'mySandbox'
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
                                    var $t = $('select.domain-selector'),
                                        domains = new DomainsCollection(),
                                        promise = domains.fetch(),
                                        preselectedDomainId = Utils.cookie('domainId');

                                    $t.children()
                                        .remove();

                                    promise.done(function (data) {
                                        $t.append(_.template(SearchDomainSelectorTemplate)({
                                            preselectedDomainId: preselectedDomainId,
                                            repos: data.data.results
                                        }));
                                    });
                                    ProducerManager.vent.trigger("msg:status",
                                        "Domain created");
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
        curateObjects: function (e) {
            ProducerManager.navigate("curate");
            ProducerManager.trigger('curate');
            this.updateActiveStatus($(e.currentTarget));
            this.closeDrawer();
        },
        importNewCourse: function () {
            var _this = this,
                domains = new DomainsCollection(),
                promise = domains.fetch();
            console.log('importing a course');

            _this.closeDrawer();

            promise.done(function (data) {
                ProducerManager.regions.dialog.show(new View.ImportCourseDialogView(data));
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
                                // check if a domain is selected or not
                                var formEl = $('#uploadItemForm'),
                                    selectedDomain = Utils.selectedDomainId(),
                                    targetUrl = '/api/v1/repository/repositories/' + Utils.selectedDomainId() + '/upload/',
                                    xhr = new XMLHttpRequest();

                                if (selectedDomain === '-1') {
                                    $('div.import-warning').removeClass('hidden')
                                        .html('Please select a domain to upload to.');
                                } else {
                                    formEl.find('input[name="csrfmiddlewaretoken"]').val(csrftoken);

                                    var form = new FormData(formEl[0]);

                                    xhr.open("POST", targetUrl);

                                    xhr.onload = function (e) {
                                        if (xhr.readyState === 4 && xhr.status !== 200) {
                                            ProducerManager.vent.trigger("msg:error",
                                                xhr.responseText);
                                        }
                                    };

                                    xhr.send(form);

                                    ProducerManager.vent.trigger("msg:status",
                                            "Your course is being processed, and you will be notified " +
                                            "when it has finished.");
                                    $(this).dialog("close");
                                }
                            }
                        }
                    ]
                });
                Utils.bindDialogCloseEvents();
                $('input[name="fileSelector"]').on('change', function () {
                    _this.loadFileNamePreview(this);
                });

            });
        },
        loadFileNamePreview: function (obj) {
            var filename = obj.files[0].name;
            $('div.selected-file-name').removeClass('hidden')
                .html('<strong>Selected:</strong> ' + filename);
        },
        loadUserCourses: function () {
            console.log('loading user courses');
            require(["apps/edit-course/edit_course_controller",
                     "apps/dashboard/domains/domain_controller"], function(EditCourseController,
                                                                           DomainController){
                EditCourseController.renderCanvas();
                DomainController.listUserCourses(Utils.userRepoId());
            });
        },
        mySandbox: function (e) {
            ProducerManager.navigate("sandbox");
            ProducerManager.trigger('sandbox');
            this.updateActiveStatus($(e.currentTarget));
        }
    });

    View.ImportCourseDialogView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;
            return this;
        },
        serializeData: function () {
            return {
                domains: this.options.data.results
            };
        },
        template: function (serializedModel) {
            var domainId = typeof Cookies.get('domainId') === 'undefined' ? '-1' : Cookies.get('domainId');
            return _.template(ImportCourseTemplate)({
                preselectedDomainId: domainId,
                repos: serializedModel.domains
            });
        },
        events: {
            'change select.domain-selector': 'setDomainPreference'
        },
        setDomainPreference: function (e) {
            var domainId = $(e.currentTarget).val();
            Cookies.set('domainId', domainId);
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