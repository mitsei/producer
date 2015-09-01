// apps/common/utilities.js

define(["jquery", "underscore"],
    function ($, _) {

        var utils = {};

        utils.activeUser = $('span.active-user').text().trim();

        utils.bindDialogCloseEvents = function () {
            $('div[role="dialog"] button.ui-dialog-titlebar-close').text('x');

            $(document).on('click', '.ui-widget-overlay', function(){
                $(".ui-dialog-titlebar-close").trigger('click');
            });
        };

        utils.cleanUp = function (text) {
            return text;
        };

        utils.doneProcessing = function () {
            $('.nav > .processing-spinner').addClass('hidden');
            $('body').removeClass('processing');
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

        utils.processing = function () {
            $('.nav > .processing-spinner').removeClass('hidden');
            $('body').addClass('processing');
        };

        utils.selectedRepoId = function (path) {
            if (typeof path !== 'undefined') {
                var domainMatch = utils.getMatchingDomainOption('#repos/' + path);
                return $(domainMatch).data('id');
            } else {
                return $('.repositories-menu').data('id');
            }
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
//                if (textBlob.indexOf('<script') >= 0) {
//                    var scripts = $('<html></html>').append(textBlob)
//                        .find('script'),
//                        $head = $('<head></head>').append(scripts),
//                        $body = $('<body></body>').append(textBlob);
//                    return $('<html></html>').append(head).append(body);
//                } else {
//                    return $('<html></html>').append(textBlob)[0].outerHTML;
//                }
            }
        };

        return utils;
 });