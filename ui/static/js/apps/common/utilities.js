// apps/common/utilities.js

define(["jquery", "underscore", "cookies"],
    function ($, _, Cookies) {

        var utils = {};

        utils.activeUser = $('span.active-user').text().trim();

        utils.assetExportUrl = function (obj) {
            return window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : '') + '/api/v1/repository/assets/' + obj.id + '/download/';
        };

        utils.bindDialogCloseEvents = function () {
            $('div[role="dialog"] button.ui-dialog-titlebar-close').text('x');

            $(document).on('click', '.ui-widget-overlay', function(){
                $(".ui-dialog-titlebar-close").trigger('click');
            });
        };

        utils.cleanUp = function (text) {
            return text;
        };

        utils.compositionExportUrl = function (obj) {
            return window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : '') + '/api/v1/repository/compositions/' + obj.id + '/download/';
        };

        utils.cookie = function (name) {
            var cookieValue = typeof Cookies.get(name) === 'undefined' ? '-1' : Cookies.get(name);

            if (cookieValue.indexOf('@') >= 0) {
                return encodeURIComponent(cookieValue);
            } else {
                return cookieValue;
            }
        };

        utils.currentLearningObjectives = function () {
            // grab the learning objectives off the Curate UI
            var $los = $('ul.lo-list').find('li.learning-objective'),
                loList = [];
            _.each($los, function (lo) {
                loList.push($(lo).data('obj'));
            });

            return loList;
        };

        utils.domainGenus = function () {
            return 'repository-genus-type%3Adomain-repo%40ODL.MIT.EDU';
        };

        utils.doneProcessing = function () {
            $('.nav > .processing-spinner').addClass('hidden');
            $('body').removeClass('processing');
        };

        utils.exportUrl = function (obj) {
            if (obj.type === 'Composition') {
                return utils.compositionExportUrl(obj);
            } else if (obj.type === 'Asset') {
                return utils.assetExportUrl(obj);
            } else {
                return utils.itemExportUrl(obj);
            }
        };

        utils.genusType = function (identifier) {
            return utils.id('edx-composition',
                identifier,
                'EDX.ORG');
        };

        utils.getMatchingDomainOption = function (path) {
            var domainRepoOptions = $('.repositories-menu li a'),
                domainMatch;

            domainMatch = _.filter(domainRepoOptions, function (opt) {
                return $(opt).attr('href') === path;
            })[0];

            return domainMatch;
        };

        utils.fixDomainSelector = function (expectedPath) {
            var domainMatch = utils.getMatchingDomainOption(expectedPath),
                $repoBtn = $('.dropdown-toggle');

            $repoBtn.find('span.repository-placeholder').text($(domainMatch).text());
            $('.repositories-menu').data('id', $(domainMatch).data('id'));
            $("ul.repository-navbar li").removeClass('hidden');
            $('#notifications-region').html('');
        };

        utils.id = function (namespace, identifier, authority) {
            return namespace + '%3A' + identifier + '%40' + authority;
        };

        utils.isCurating = function () {
            return $('.curate-objects.active').length > 0;
        };

        utils.itemExportUrl = function (obj) {
            return window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : '') + '/api/v1/assessment/items/' + obj.id + '/download/';
        };

        utils.parseGenusType = function (genusTypeStr) {
            try {
                var genusType;
                if (genusTypeStr.type === 'Asset') {
                    genusType = genusTypeStr.assetContents[0].genusTypeId;
                } else {
                    genusType = genusTypeStr.genusTypeId;
                }
                return genusType.slice(genusType.indexOf('%3A') + 3,
                    genusType.indexOf('%40'));
            } catch (e) {
                return genusTypeStr.slice(genusTypeStr.indexOf('%3A') + 3,
                    genusTypeStr.indexOf('%40'));
            }
        };

        utils.patchSelect2 = function () {
            // from https://github.com/select2/select2/issues/1246#issuecomment-71710835
            if ($.ui && $.ui.dialog && $.ui.dialog.prototype._allowInteraction) {
                var ui_dialog_interaction = $.ui.dialog.prototype._allowInteraction;
                $.ui.dialog.prototype._allowInteraction = function(e) {
                    if ($(e.target).closest('.select2-dropdown').length) return true;
                    return ui_dialog_interaction.apply(this, arguments);
                };
            }
        };

        utils.processing = function () {
            $('.nav > .processing-spinner').removeClass('hidden');
            $('body').addClass('processing');
        };

        utils.runId = function () {
            return $('select.run-selector').val();
        };

        utils.selectedDomainId = function (path) {
            if ($("#search-components-menu").hasClass('open')) {
                return $('#search-components-menu select.domain-selector').val();
            } else if (utils.isCurating()) {
                return $('select.curate-domain-selector').val();
            } else {
                return $('.ui-dialog select.domain-selector').val();
            }
        };

        utils.slugify = function (str) {
            // From
            // http://dense13.com/blog/2009/05/03/converting-string-to-slug-javascript/
            str = str.replace(/^\s+|\s+$/g, ''); // trim
            str = str.toLowerCase();

            // remove accents, swap ñ for n, etc
            var from = "àáäâèéëêìíïîòóöôùúüûñç·/_,:;";
            var to   = "aaaaeeeeiiiioooouuuunc------";
            for (var i=0, l=from.length ; i<l ; i++) {
                str = str.replace(new RegExp(from.charAt(i), 'g'), to.charAt(i));
            }

            str = str.replace(/[^a-z0-9 -]/g, '') // remove invalid chars
                .replace(/\s+/g, '-') // collapse whitespace and replace by -
                .replace(/-+/g, '-'); // collapse dashes

            return str;
        };

        utils.userRepoId = function () {
            return $('span.active-user').data('repo-id');
        };

        utils.wrapText = function (textBlob) {
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

            try {
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
                        if (textBlob.indexOf('<body') < 0 && textBlob.indexOf('<html') < 0) {
                            wrapper = $('<html></html>').append(head)
                                .append('<body>' + textBlob + '</body>');
                        } else if (textBlob.indexOf('<body') < 0) {
                            wrapper = $('<html></html>').append(head)
                                .append('<body>' + wrapper.find('html').html() + '</body>');
                        } else {
                            wrapper.find('html').prepend(head);
                        }
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
                }

                if ($.isXMLDoc(wrapper[0])) {
                    return utils.cleanUp(wrapper.contents().prop('outerHTML'));
                } else {
                    return utils.cleanUp(wrapper.prop('outerHTML'));
                }
            } catch (e) {
                // return the textBlob if all else fails
                return $('<html></html>').append(textBlob)[0].outerHTML;
            }
        };

        return utils;
 });