// apps/faceted-search/views/faceted_search_views.js

define(["app",
        "apps/common/utilities",
        "apps/preview/views/preview_views",
        "apps/dashboard/domains/collections/domains",
        "text!apps/faceted-search/templates/facets.html",
        "text!apps/faceted-search/templates/facet_results.html",
        "text!apps/faceted-search/templates/curate_facet_results.html",
        "text!apps/faceted-search/templates/facet_pagination.html",
        "text!apps/faceted-search/templates/domain_selector.html",
        "text!apps/faceted-search/templates/lo_facet.html",
        "cookies",
        "bootstrap",
        "bootstrap-drawer",
        "jquery-bootpag",
        "jquery-sortable",
        "select2"],
       function(ProducerManager, Utils, PreviewViews, DomainsCollection,
                FacetsTemplate, FacetResultsTemplate, CurateFacetResultsTemplate,
                FacetPaginationTemplate, DomainSelectorTemplate, LOFacetTemplate,
                Cookies){
  ProducerManager.module("FacetedSearchApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    var selectedFacets = [],
        selectedItemsPerPage = 10,
        currentFacetsPromise,
        currentResultsPromise;

    function cancel (promise) {
        try {
            promise.abort();
        } catch (e) {
            // pass
        }
    }

    function getFacetTerms () {
        var $facetClusters = $('div.facet-items'),
            facetTerms = [];

        _.each($facetClusters, function (cluster) {
            var prefix = $(cluster).data('facet-prefix') + '_exact',
                $checkedFacets = $(cluster).find('input.facet-checkbox:checked');
            if ($checkedFacets.length > 0) {
                _.each($checkedFacets, function (checkedFacet) {
                    facetTerms.push(prefix + ':' + $(checkedFacet).val());
                });
            }

            if (prefix == 'learning_objective_exact') {
                var $selectedLos = $(cluster).find('select.learning-objective-selector option:selected');

                if ($selectedLos.length > 0) {
                    _.each($selectedLos, function (selectedLo) {
                        facetTerms.push(prefix + ':' + $(selectedLo).val());
                    });
                }
            }
        });

        return facetTerms;
    }

    function saveItemsPerPage () {
        selectedItemsPerPage = parseInt($('#items-per-page').val());
    }

    function saveSelectedFacets () {
        selectedFacets = [];

        _.each(getFacetTerms(), function (facetText) {
            var facetId = facetText.split(':')[1];
            if (selectedFacets.indexOf(facetId) < 0) {
                selectedFacets.push(facetId);
            }
        });
    }

    function updateFacets (keywords) {
        saveItemsPerPage();

        // save the selected facets
        saveSelectedFacets();

        // cancel current promises, if they exist
        cancel(currentFacetsPromise);

        if (Utils.selectedDomainId() !== null) {
            return $.ajax({
                url: '/api/v1/repository/repositories/' + Utils.selectedDomainId() + '/queryplans/',
                data: {
                    q: keywords,
                    selected_facets: getFacetTerms()
                }
            }).fail(function (xhr, status, msg) {
                ProducerManager.vent.trigger('msg:error', xhr.responseText);
            }).done(function (data) {
                // pass the data on to the facet renderer region and the
                // facet results region
                // first, order the facets alphabetically
                console.log('done with facets');
                var totalObjects = _.sum(data.facets.course, function (obj) {
                    return obj[1];
                });
                if (Utils.isCurating()) {
                    ProducerManager.regions.curateFacetedSearchPagination.show(new View.PaginationView({
                        total: totalObjects
                    }));
                    ProducerManager.regions.curateFacetedSearchFacets.show(new View.FacetsView(data));
                } else {
                    ProducerManager.regions.facetedSearchPagination.show(new View.PaginationView({
                        total: totalObjects
                    }));
                    ProducerManager.regions.facetedSearchFacets.show(new View.FacetsView(data));
                }
            }).always(function () {
            });
        }
    }

    function updateFacetsAndResults () {
        var keywords = $('.input-search').val();

        if (Utils.selectedDomainId() !== "-1" &&
            Utils.selectedDomainId() !== null) {
            // show spinner while searching
            $('.processing-spinner').removeClass('hidden');
            Utils.processing();
            console.log('starting to update facets and results');
            currentFacetsPromise = updateFacets(keywords);
            currentResultsPromise = updateResults(keywords);
            $.when(currentFacetsPromise, currentResultsPromise).done(function (facets, objects) {
                Utils.doneProcessing();
                console.log('done with both facets and results');
                $('.processing-spinner').addClass('hidden');
                selectedFacets = [];
            });
        }
    }

    function updateResults (keywords, page) {
        var itemsPerPage = $('#items-per-page').val();

        keywords = typeof keywords === 'undefined' ? $('.input-search').val() : keywords;
        page = typeof page === 'undefined' ? 1 : page;

        // cancel current promises, if they exist
        cancel(currentResultsPromise);

        // save the selected facets
        saveSelectedFacets();

        // hide learning objectives, if present on screen
        $('#curate-learning-objectives').addClass('hidden');

        if (Utils.selectedDomainId() !== null) {
            return $.ajax({
                url: '/api/v1/repository/repositories/' + Utils.selectedDomainId() + '/search/',
                data: {
                    q: keywords,
                    selected_facets: getFacetTerms(),
                    limit: itemsPerPage,
                    page: page
                }
            }).fail(function (xhr, status, msg) {
                ProducerManager.vent.trigger('msg:error', xhr.responseText);
            }).done(function (data) {
                // pass the data on to the facet results region
                console.log('done with results');
                if (Utils.isCurating()) {
                    ProducerManager.regions.curateFacetedSearchResults.show(new View.FacetResultsView(data));
                } else {
                    ProducerManager.regions.facetedSearchResults.show(new View.FacetResultsView(data));
                }
            });
        }
    }

    View.HeaderView = Marionette.ItemView.extend({
        initialize: function () {
            selectedFacets = [];
        },
        template: false,
        el: '.faceted-search-header',
        onShow: function () {
            var $t = $('select.domain-selector'),
                domains = new DomainsCollection(),
                promise = domains.fetch(),
                preselectedDomainId = Utils.cookie('domainId');

            promise.done(function (data) {
                $t.append(_.template(DomainSelectorTemplate)({
                    preselectedDomainId: preselectedDomainId,
                    repos: data.data.results
                }));

                if (Utils.isCurating() && preselectedDomainId != '-1') {
                    $('button.curate-execute-keyword-search').trigger('click');
                }
            });
        },
        events: {
            'change select.domain-selector': 'setNewDomain',
            'click button.curate-execute-keyword-search': 'curateKeywordFilter',
            'click button.execute-keyword-search': 'keywordFilter',
            'click button.close-drawer': 'toggleDrawer',
            'keyup input.input-search': 'checkForEnterKey'
        },
        checkForEnterKey: function (e) {
            var $e = $(e.currentTarget);
            if (e.keyCode === 13) {
                updateFacetsAndResults();
            }
        },
        curateKeywordFilter: function (e) {
            updateFacetsAndResults();
        },
        keywordFilter: function (e) {
            var $drawer = $('#search-components-menu');

            $('#search-components-menu').unbind('shown.bs.drawer')
                .on('shown.bs.drawer', function () {
                updateFacetsAndResults();
            });

            if ($drawer.hasClass('open')) {
                updateFacetsAndResults();
            }
        },
        setNewDomain: function (e) {
            var $domain = $(e.currentTarget),
                domainId = $domain.val();

            Cookies.set('domainId', domainId);
            updateFacetsAndResults();
        },
        toggleDrawer: function () {
            $('#search-components-menu').drawer('toggle');
            $('#add-new-components-btn').button('toggle');
        }
    });

    View.FacetsView = Marionette.ItemView.extend({
        // on render this should also render the results region
        initialize: function (options) {
            this.options = options;

            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        template: function (serializedModel) {
            return _.template(FacetsTemplate)({
                facets: serializedModel.options.facets,
                selectedFacets: selectedFacets,
                selectedItemsPerPage: selectedItemsPerPage
            });
        },
        onRender: function () {
//            this.passToPaginator(this.options);
        },
        onShow: function () {
            $('select.learning-objective-selector').select2({
                placeholder: 'Objectives...',
                templateResult: function (lo) {
                    if ($(lo.element).data('counts') != null) {
                        return $(_.template(LOFacetTemplate)({
                            displayName: lo.text,
                            counts: $(lo.element).data('counts')
                        }));
                    } else {
                        return lo.text;
                    }
                }
            });
        },
        events: {
            'change #items-per-page': 'updateFacetResults',
            // on click of a facet, update the results region
            // by passing it a filtered "objects" list
            'change .learning-objective-selector': 'updateFacetsAndResults',
            'click .facet-checkbox': 'updateFacetsAndResults'
        },
        updateFacetsAndResults: function (e) {
            updateFacetsAndResults();
        },
        updateFacetResults: function (e) {
            var totalObjects = _.sum($('#collapse-course span.badge'), function (obj) {
                return parseInt($(obj).text());
            });
            ProducerManager.regions.facetedSearchPagination.show(new View.PaginationView({
                total: totalObjects
            }));
            updateResults();
        }
    });

    View.PaginationView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;

            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        template: function (serializedModel) {
            return _.template(FacetPaginationTemplate)();
        },
        onShow: function () {
            var numPerPage = parseInt($('#items-per-page').val()) || 10,
                totalItems = this.options.total,
                totalPages = Math.ceil(totalItems / numPerPage),
                pagesToShow = Math.min(5, totalPages),
                _this = this;

            $('.paginator').bootpag({
                total: totalPages,
                maxVisible: pagesToShow
            }).on('page', function (e, num) {
                _this.updateResults(num);
            });
        },
        updateResults: function (pageNum) {
            updateResults(null, pageNum);
        }
    });

    View.FacetResultsView = Marionette.ItemView.extend({
        initialize: function (options) {
            var _this = this;
            this.options = options;

            // compute runNames here and add them to each object in this.options.objects
            _.each(_this.options.objects, function (obj) {
                if (obj.type === 'Composition' || obj.type === 'Asset') {
                    var runIds = [obj.repositoryId];
                    if (obj.hasOwnProperty('assignedRepositoryIds')) {
                        runIds = runIds.concat(obj.assignedRepositoryIds);
                    }
                } else {
                    var runIds = [obj.bankId].concat(obj.assignedBankIds);
                }
                var runNames = [];
                _.each(runIds, function (runId) {
                    var runIdentifier = Utils.parseGenusType(runId);
                    _.each(_this.options.runMap, function (runName, runRepoId) {
                        if (runRepoId.indexOf(runIdentifier) >= 0) {
                            runNames.push(runName);
                            return;
                        }
                    });
                });

                runNames = runNames.join('; ');
                obj.runNames = runNames;
            });

            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        template: function (serializedModel) {
            if (Utils.isCurating()) {
                return _.template(CurateFacetResultsTemplate)({
                    objects: serializedModel.options.objects,
                    runMap: serializedModel.options.runMap
                });
            } else {
                return _.template(FacetResultsTemplate)({
                    objects: serializedModel.options.objects,
                    runMap: serializedModel.options.runMap
                });
            }
        },
        onShow: function () {
            if (!Utils.isCurating()) {
                // initialize the sortables here and connect to the course view
                $('ul.facet-results-list').sortable({
                    group: 'producer',
                    drop: false
                });
            }
        },
        events: {
            'click .curate-search-result': 'manageLearningObjectives',
            'click .show-preview': 'togglePreview'
        },
        manageLearningObjectives: function (e) {
            if (!$(e.originalEvent.target).hasClass('show-preview')) {
                var $e = $(e.currentTarget);

                $('.curate-search-result.active').removeClass('active');
                $e.addClass('active');
                $('#curate-learning-objectives').removeClass('hidden');
                require(["apps/curate/curate_controller"], function(CurateController){
                    CurateController.showLearningObjectives($e.data('obj').id);
                });
            }
        },
        togglePreview: function (e) {
            // If is a composition, open preview in a dialog window
            var $e = $(e.currentTarget),
                $target = $e.siblings('iframe.preview-frame'),
                $spinner = $e.siblings('.preview-processing'),
                $resource = $e.closest('li.resource, li.composition'),
                obj = $resource.data('obj'),
                objId = obj.id,
                url;

            if (obj.type === 'Composition') {
                ProducerManager.regions.dialog.show(new PreviewViews.CompositionView({
                    objId: objId
                }));
                ProducerManager.regions.dialog.$el.dialog({
                    modal: true,
                    width: 1200,
                    height: 600,
                    title: 'Preview of ' + obj.displayName.text,
                    buttons: [
                        {
                            text: "Close",
                            class: 'btn btn-danger',
                            click: function () {
                                $(this).dialog("close");
                            }
                        }
                    ]
                });
                Utils.bindDialogCloseEvents();
            } else {
                if ($e.hasClass('collapsed') && !$e.hasClass('cached')) {
                    if (objId.indexOf('assessment.Item') >= 0) {
                        url = '/api/v1/assessment/items/' + objId + '/?renderable_edxml';
                    } else {
                        url = '/api/v1/repository/assets/' + objId + '/?renderable_edxml';
                    }

                    // show spinner while searching
                    $spinner.removeClass('hidden');
                    $.ajax({
                        url: url
                    }).fail(function (xhr, status, msg) {
                        ProducerManager.vent.trigger('msg:error', xhr.responseText);
                    }).done(function (data) {
                        var assetText, youtubeIds, youtubeId;

                        $target.toggleClass('hidden');
                        $e.toggleClass('collapsed');
                        $resource.data('obj', data);

                        if (objId.indexOf('assessment.Item') >= 0) {
                            $target.attr('srcdoc', Utils.wrapText(data['texts']['edxml']));
                        } else {
                            assetText = data['assetContents'][0]['text']['text'];
                            if (assetText.indexOf('youtube=') >= 0) {
                                youtubeIds = $(assetText).attr('youtube')
                                    .split(',');
                                youtubeId = _.filter(youtubeIds, function (speedIdPair) {
                                    return speedIdPair.indexOf('1.0:') >= 0;
                                })[0].split(':')[1];
                                $target[0].removeAttribute('srcdoc');
                                $target.attr('src', '//www.youtube.com/embed/' + youtubeId);
                            } else {
                                $target.attr('srcdoc', Utils.wrapText(assetText));
                            }
                        }
                    }).always(function () {
                        // remove spinner
                        $spinner.addClass('hidden');
                    });
                } else {
                    $target.toggleClass('hidden');
                    $e.toggleClass('collapsed');
                    $e.addClass('cached');
                }
            }
        }
    });
  });

  return ProducerManager.FacetedSearchApp.View;
});