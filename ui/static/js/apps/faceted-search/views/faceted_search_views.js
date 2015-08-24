// apps/faceted-search/views/faceted_search_views.js

define(["app",
        "apps/common/utilities",
        "text!apps/faceted-search/templates/facets.html",
        "text!apps/faceted-search/templates/facet_results.html",
        "text!apps/faceted-search/templates/facet_pagination.html",
        "bootstrap",
        "bootstrap-drawer",
        "jquery-bootpag"],
       function(ProducerManager, Utils, FacetsTemplate, FacetResultsTemplate,
                FacetPaginationTemplate){
  ProducerManager.module("FacetedSearchApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    function cleanUp (text) {
        return text;
    }

    function wrapText (textBlob) {
        var mathjaxScript = $('<script type="text/javascript" src="https://cdn.mathjax.org/mathjax/2.4-latest/MathJax.js?config=TeX-MML-AM_HTMLorMML-full">' +
                '</script>'),
            configMathjax = $('<script type="text/x-mathjax-config">' +
                'MathJax.Hub.Config({' +
                'tex2jax: {' +
                  'inlineMath: [' +
                    "['\\(','\\)']," +
                    "['[mathjaxinline]','[/mathjaxinline]']" +
                  '],' +
                  'displayMath: [' +
                    '["\\[","\\]"],' +
                    "['[mathjax]','[/mathjax]']" +
                  ']' +
                '}' +
              '});' +
              'MathJax.Hub.Configured();</script>');


        if (textBlob.indexOf('<html') >= 0 && (textBlob.indexOf('<video') === -1)) {
            try {
                var wrapper = $(textBlob);
                if (typeof wrapper.attr('outerHTML') === 'undefined') {
                    throw 'InvalidText';
                }
            } catch (e) {
                var wrapper = $($.parseXML(textBlob));
            }

            if (wrapper.find('head').length > 0) {
                if (textBlob.indexOf('[mathjax') >= 0) {
                    wrapper.find('head').append(configMathjax);
                }
                wrapper.find('head').append(mathjaxScript);
            } else {
                var head = $('<head></head>');
                if (textBlob.indexOf('[mathjax') >= 0) {
                    head.append(configMathjax);
                }
                head.append(mathjaxScript);
                wrapper.prepend(head);
            }
        } else if (textBlob.indexOf('<problem') >= 0) {
            var wrapper = $('<html></html>'),
                head = $('<head></head>'),
                body = $('<body></body>');
            body.append(textBlob);
            if (textBlob.indexOf('[mathjax') >= 0) {
                head.append(configMathjax);
            }
            head.append(mathjaxScript);
            wrapper.append(head);
            wrapper.append(body);
        } else if (textBlob.indexOf('<video') >= 0) {
            wrapper = $(textBlob);
        } else {
            wrapper = $(textBlob);
        }

        if ($.isXMLDoc(wrapper[0])) {
            return cleanUp(wrapper.contents().prop('outerHTML'));
        } else {
            return cleanUp(wrapper.prop('outerHTML'));
        }
    }

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
            var keywords = $('.input-search').val();

            this.triggerQuery(keywords);
        },
        toggleDrawer: function () {
            $('#search-components-menu').drawer('toggle');
        },
        triggerQuery: function (keywords) {
            // show spinner while searching
            $('.processing-spinner').removeClass('hidden');
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
        updateFacetResults: function (e) {
            // check all facets for the checked ones
            // If none checked, unhide all objects
            // If some are checked, hide objects that do not meet filter requirements
            if ($('input.facet-checkbox:checked').length === 0) {
                this.passToPaginator(this.options);
            } else {
                var filteredObjects = [],
                    _this = this;
                _.each($('input.facet-checkbox:checked'), function (box) {
                    var facetValue = $(box).val();
                    _.each(_this.options.objects, function (obj) {
                        if (obj.id.indexOf('assessment.Item') >= 0) {
                            var genusTypeStr = obj.genusTypeId;
                        } else {
                            var genusTypeStr = obj.assetContents[0].genusTypeId;
                        }
                        if (obj.runNames.indexOf(facetValue) >= 0 ||
                            Utils.parseGenusType(genusTypeStr) == facetValue) {
                            filteredObjects.push(obj);
                        }
                    });
                });

                filteredObjects.sort(function (a, b) {
                    return a.id > b.id ? 1 : ((b.id > a.id) ? -1 : 0);
                });

                filteredObjects = _.uniq(filteredObjects, true);
                this.passToPaginator({
                    objects: filteredObjects
                });
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
            $('div.resource').draggable({
                handle: 'div.drag-handles',
                helper: 'clone',
                revert: 'invalid',
                connectToSortable: '#composition-region'
            });
        },
        events: {
            'click .show-preview': 'togglePreview'
        },
        togglePreview: function (e) {
            var $e = $(e.currentTarget),
                $target = $e.siblings('iframe.preview-frame'),
                $spinner = $e.siblings('.preview-processing'),
                objId = $e.parents('div.resource').data('obj').id,
                url;

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

                    if (objId.indexOf('assessment.Item') >= 0) {
//                        $target.attr('srcdoc', data['texts']['edxml']);
                        $target.attr('srcdoc', wrapText(data['texts']['edxml']));
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
//                            $target.attr('srcdoc', assetText);
                            $target.attr('srcdoc', wrapText(assetText));
                        }
                    }

//                    var mathjaxScript = $('<script type="text/javascript" src="https://cdn.mathjax.org/mathjax/2.4-latest/MathJax.js?config=TeX-MML-AM_HTMLorMML-full">' +
//                        '</script>');
//                    $target.contents()[0].head.appendChild(mathjaxScript[0]);
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
    });
  });

  return ProducerManager.FacetedSearchApp.View;
});