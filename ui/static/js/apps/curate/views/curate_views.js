// apps/curate/views/curate_views.js

define(["app",
        "apps/common/utilities",
        "apps/curate/collections/banks",
        "apps/curate/collections/bank_objectives",
        "apps/curate/collections/objectives",
        "apps/dashboard/assets/models/assets",
        "apps/dashboard/compositions/models/composition",
        "text!apps/curate/templates/curate_facets.html",
        "text!apps/curate/templates/add_objective.html",
        "text!apps/curate/templates/objective_selector.html",
        "text!apps/curate/templates/objective_selector_none.html",
        "text!apps/curate/templates/objectives.html",
        "cookies",
        "jquery-ui",
        "bootstrap-drawer",
        "select2"],
       function(ProducerManager, Utils, BanksCollection, BankObjectivesCollection,
                ObjectivesCollection, AssetModel, CompositionModel,
                CurateFacetsTemplate,
                AddObjectiveTemplate, ObjectiveSelectorTemplate,
                ObjectiveSelectorNoneTemplate, ObjectivesTemplate, Cookies){
  ProducerManager.module("CurateApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.CurateView = Marionette.ItemView.extend({
        template: function () {
            return _.template(CurateFacetsTemplate)();
        }
    });

    View.LinkLearningObjectiveView = Marionette.ItemView.extend({
        template: function (serializedData) {
            var preselectedId = Utils.cookie('bankId');

            return _.template(AddObjectiveTemplate)({
                banks: serializedData.items,
                preselectedId: preselectedId
            });
        },
        onShow: function () {
            var preselectedId = Utils.cookie('bankId'),
                $e = $('#bank-selector');

            $e.select2({
                placeholder: 'Collections...'
            });

            if (preselectedId !== '-1') {
                $e.trigger('change');
            }
        },
        events: {
            'change #bank-selector': 'showBankObjectives',
            'change #objective-selector': 'previewObjective'
        },
        previewObjective: function (e) {
            var $e = $(e.currentTarget),
                $obj = $e.find('option:selected'),
                $displayName = this.$el.find('span.display-name'),
                $description = this.$el.find('span.description'),
                $wrapper = this.$el.find('div.hidden.objective-selector-preview');

            $wrapper.removeClass('hidden');
            $displayName.text($obj.text());
            $description.text($obj.attr('title'));
        },
        showBankObjectives: function (e) {
            var $e = $('#bank-selector'),
                bankId = $e.val(),
                $t = $('#objective-selector'),
                $w = $('.objective-selector-wrapper'),
                objectives = new BankObjectivesCollection([], {id: bankId}),
                objectivesPromise = objectives.fetch({
                    reset: true,
                    error: function (model, xhr, options) {
                        ProducerManager.vent.trigger('msg:error', xhr.responseText);
                        Utils.doneProcessing();
                    }
                });

            Utils.processing();

            objectivesPromise.done(function (data) {
                Cookies.set('bankId', bankId);
                data = data.data.results;
                $w.removeClass('hidden');
                if (data.length > 0) {
                    _.each(data, function (datum) {
                        $t.append(_.template(ObjectiveSelectorTemplate)({
                            obj: datum
                        }));
                    });
                } else {
                    $t.append(_.template(ObjectiveSelectorNoneTemplate)());
                }
                $t.select2({
                    placeholder: 'Objectives...'
                });
                Utils.doneProcessing();
            });
        }
    });

    View.ManageLearningObjectivesView = Marionette.ItemView.extend({
        template: function (serializedData) {
            return _.template(ObjectivesTemplate)({
                los: serializedData.items
            });
        },
        events: {
            'click .link-objective': 'linkObjective'
        },
        linkObjective: function (e) {
            var $e = $('.curate-search-result.active'),
                originalObjectId = $e.data('obj').id,
                banks = new BanksCollection([]),
                banksView = new View.LinkLearningObjectiveView({collection: banks}),
                banksPromise = banksView.collection.fetch({
                    reset: true,
                    error: function (model, xhr, options) {
                        ProducerManager.vent.trigger('msg:error', xhr.responseText);
                        Utils.doneProcessing();
                    }
                });

            Utils.processing();

            banksPromise.done(function (data) {
                ProducerManager.regions.dialog.show(banksView);
                ProducerManager.regions.dialog.$el.dialog({
                    modal: true,
                    width: 500,
                    height: 450,
                    title: 'Link objective to an asset / composition / item',
                    buttons: [
                        {
                            text: "Cancel",
                            class: 'btn btn-danger',
                            click: function () {
                                $(this).dialog("close");
                            }
                        },
                        {
                            text: "Link",
                            class: 'btn btn-success',
                            click: function () {
                                var objId = $('#objective-selector').val(),
                                    _this = this;

                                if (objId === '-1') {
                                    $(_this).dialog('close');
                                    console.log('No objective selected, no action taken.');
                                } else {
                                    if (objId.indexOf('repository.Composition') >= 0) {
                                        var objModel = new CompositionModel({id: originalObjectId});
                                    } else {
                                        // both assets and items are handled by the same model...
                                        var objModel = new AssetModel({id: originalObjectId});
                                    }
                                    var los = Utils.currentLearningObjectives();
                                    los = _.pluck(los, 'id');
                                    los.push(objId);

                                    objModel.set('learningObjectiveIds', los);
                                    objModel.save(null, {
                                        success: function (data) {
                                            console.log('saved');
                                        },
                                        error: function (xhr, status, msg) {
                                            ProducerManager.vent.trigger('msg:error', xhr.responseText);
                                        }
                                    });

                                    $(_this).dialog('close');
                                }
                            }
                        }
                    ]
                });
                Utils.patchSelect2();
                Utils.bindDialogCloseEvents();
                Utils.doneProcessing();
            });


        }
    });
  });

  return ProducerManager.CurateApp.View;
});