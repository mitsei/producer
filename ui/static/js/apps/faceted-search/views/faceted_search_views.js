// apps/faceted-search/views/faceted_search_views.js

define(["app",
        "apps/common/utilities",
        "apps/preview/views/preview_views",
        "text!apps/faceted-search/templates/facets.html",
        "text!apps/faceted-search/templates/facet_results.html",
        "text!apps/faceted-search/templates/facet_pagination.html",
        "bootstrap",
        "bootstrap-drawer",
        "jquery-bootpag",
        "jquery-sortable"],
       function(ProducerManager, Utils, PreviewViews, FacetsTemplate, FacetResultsTemplate,
                FacetPaginationTemplate){
  ProducerManager.module("FacetedSearchApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){

    View.HeaderView = Marionette.ItemView.extend({
        template: false,
        el: '.faceted-search-header',
        events: {
            'click button.execute-keyword-search': 'keywordFilter',
            'click button.close-drawer': 'toggleDrawer',
            'keyup input.input-search': 'checkForEnterKey'
        },
        checkForEnterKey: function (e) {
            var $e = $(e.currentTarget),
                keywords = $e.val();

            if (e.keyCode === 13) {
                this.triggerQuery(keywords);
            }
        },
        getKeywordSearchResults: function (keywords) {
            var _this = this;
            $('#search-components-menu').unbind('shown.bs.drawer')
                .on('shown.bs.drawer', function () {
                _this.triggerQuery(keywords);
            });
        },
        keywordFilter: function (e) {
            var keywords = $('.input-search').val(),
                _this = this;

            $('#search-components-menu').unbind('shown.bs.drawer')
                .on('shown.bs.drawer', function () {
                _this.triggerQuery(keywords);
            });
        },
        toggleDrawer: function () {
            $('#search-components-menu').drawer('toggle');
            $('#add-new-components-btn').button('toggle');
        },
        triggerQuery: function (keywords) {
            // show spinner while searching
            $('.processing-spinner').removeClass('hidden');
            Utils.processing();
            $.ajax({
                url: '/api/v1/repository/repositories/' + Utils.selectedRepoId() + '/search/',
                data: {
                    q: keywords
                }
            }).fail(function (xhr, status, msg) {
                ProducerManager.vent.trigger('msg:error', xhr.responseText);
            }).done(function (data) {
                // pass the data on to the facet renderer region and the
                // facet results region
                ProducerManager.regions.facetedSearchFacets.show(new View.FacetsView(data));
            }).always(function () {
                // remove spinner
                $('.processing-spinner').addClass('hidden');
                Utils.doneProcessing();
            });
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
                facets: serializedModel.options.facets
            });
        },
        onRender: function () {
            this.passToPaginator(this.options);
        },
        events: {
            'change #items-per-page': 'updateFacetResults',
            // on click of a facet, update the results region
            // by passing it a filtered "objects" list
            'click .facet-checkbox': 'updateFacetResults'
        },
        passToPaginator: function (objects) {
            ProducerManager.regions.facetedSearchPagination.show(new View.PaginationView(objects));
        },
        updateBadgeNumbers: function (facetValues, items) {
            var counters = {};

            // set it up so that each valid facetValue has
            // its own counter
            _.each(facetValues, function (facet) {
                counters[facet] = 0;
                // now check each item and add to the counters
                _.each(items, function (item) {
                    if (item.runNames.indexOf(facet) >= 0 ||
                        Utils.parseGenusType(item) == facet) {
                        counters[facet]++;
                    }
                });

                $('input.facet-checkbox[value="' + facet + '"]').siblings('.badge')
                    .text(counters[facet]);
            });
        },
        updateFacetResults: function (e) {
            // check all facets for the checked ones
            // If none checked, unhide all objects
            // If some are checked, hide objects that do not meet filter requirements

            // make this an AND for all checked boxes...and update the
            // badge numbers in the OTHER facet categories accordingly...
            if ($('input.facet-checkbox:checked').length === 0) {
                var facetValues = [];

                _.each($('input.facet-checkbox'), function (box) {
                    facetValues.push($(box).val());
                });
                this.passToPaginator(this.options);
                this.updateBadgeNumbers(facetValues, this.options.objects);
            } else {
                var filteredObjects = [],
                    _this = this,
                    facetValues = [],
                    $facetPanels = $(e.currentTarget).parents('div.facet-panel')
                        .parent()
                        .children('div.facet-panel');

                _.each($facetPanels, function (facetPanel) {
                    var $thisPanelFacets = $(facetPanel).find('input.facet-checkbox:checked');

                    if ($thisPanelFacets.length === 0) {
                        // if no boxes checked in this panel, then
                        // use all values -- because not filtered
                        // on any of them.
                        _.each($(facetPanel).find('input.facet-checkbox'), function (box) {
                            facetValues.push($(box).val());
                        });
                    } else {
                        // add the checked boxes to facetValues
                        _.each($thisPanelFacets, function (box) {
                            facetValues.push($(box).val());
                        });
                    }
                });

                // now, iterate through the items and make sure they meet
                // all the requirements from facetValues
                _.each(_this.options.objects, function (obj) {
                    if (_.some(facetValues, function (facetValue) {
                        return obj.runNames.indexOf(facetValue) >= 0 &&
                            facetValues.indexOf(Utils.parseGenusType(obj)) >= 0;
                    })) {
                        filteredObjects.push(obj);
                    }
                });

                filteredObjects.sort(function (a, b) {
                    return a.id > b.id ? 1 : ((b.id > a.id) ? -1 : 0);
                });

                filteredObjects = _.uniq(filteredObjects, true);
                this.passToPaginator({
                    objects: filteredObjects
                });

                this.updateBadgeNumbers(facetValues, filteredObjects);
            }
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
                totalItems = this.options.objects.length,
                totalPages = Math.ceil(totalItems / numPerPage),
                pagesToShow = Math.min(5, totalPages),
                _this = this,
                paginatedObjects = this.options.objects.slice(0,
                    numPerPage);

            this.passToResults(paginatedObjects);

            $('.paginator').bootpag({
                total: totalPages,
                maxVisible: pagesToShow
            }).on('page', function (e, num) {
                paginatedObjects = _this.options.objects.slice((num - 1) * numPerPage,
                        num * numPerPage);
                _this.passToResults(paginatedObjects);
            });
        },
        passToResults: function (objects) {
            ProducerManager.regions.facetedSearchResults.show(new View.FacetResultsView({
                objects: objects
            }));
        }
    });

    View.FacetResultsView = Marionette.ItemView.extend({
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
            return _.template(FacetResultsTemplate)({
                objects: serializedModel.options.objects
            });
        },
        onShow: function () {
            // initialize the sortables here and connect to the course view
            $('ul.facet-results-list').sortable({
                group: 'producer',
                drop: false
            });
        },
        events: {
            'click .show-preview': 'togglePreview'
        },
        togglePreview: function (e) {
            // TODO: If is a composition, open preview in a dialog window
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
                    width: 800,
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