// apps/faceted-search/views/faceted_search_views.js

define(["app",
        "apps/common/utilities",
        "text!apps/faceted-search/templates/facets.html",
        "text!apps/faceted-search/templates/facet_results.html",
        "bootstrap",
        "bootstrap-drawer"],
       function(ProducerManager, Utils, FacetsTemplate, FacetResultsTemplate){
  ProducerManager.module("FacetedSearchApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    function wrapText (textBlob) {
        if ($(textBlob).find('html').length > 0) {
            var wrapper = $(textBlob);
            if (wrapper.find('head').length > 0) {
                wrapper.find('head').append(
                        '<script type="text/javascript" src="https://edx-static.s3.amazonaws.com/mathjax-MathJax-727332c/MathJax.js?config=TeX-MML-AM_HTMLorMML-full">' +
                        '</script>');
            } else {
                var head = $('<head></head>');
                head.append('<script type="text/javascript" src="https://edx-static.s3.amazonaws.com/mathjax-MathJax-727332c/MathJax.js?config=TeX-MML-AM_HTMLorMML-full">' +
                '</script>');
                wrapper.prepend(head);
            }
        } else {
            var wrapper = $('<html></html>'),
                head = $('<head></head>'),
                body = $('<body></body>');
            body.append(textBlob);
            head.append('<script type="text/javascript" src="https://edx-static.s3.amazonaws.com/mathjax-MathJax-727332c/MathJax.js?config=TeX-MML-AM_HTMLorMML-full">' +
                '</script>');
            wrapper.append(head);
            wrapper.append(body);
        }
        return wrapper.prop('outerHTML');
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
                this.getKeywordSearchResults(keywords);
            }
        },
        getKeywordSearchResults: function (keywords) {
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
        },
        keywordFilter: function (e) {
            var keywords = $('.input-search').val();

            this.getKeywordSearchResults(keywords);
        },
        toggleDrawer: function () {
            $('#search-components-menu').drawer('toggle');
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
            // show the facets results view
            ProducerManager.regions.facetedSearchResults.show(new View.FacetResultsView(this.options));
        },
        events: {
            // on click of a facet, update the results region
            // by passing it a filtered "objects" list

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
                    $target.toggleClass('hidden');
                    $e.toggleClass('collapsed');

                    if (objId.indexOf('assessment.Item') >= 0) {
                        $target.attr('srcdoc', wrapText(data['texts']['edxml']));
                    } else {
                        $target.attr('srcdoc', wrapText(data['assetContents'][0]['text']['text']));
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
    });
  });

  return ProducerManager.FacetedSearchApp.View;
});