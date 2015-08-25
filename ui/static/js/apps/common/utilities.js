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


            if (textBlob.indexOf('<html') >= 0 && (textBlob.indexOf('<video') === -1)) {
                try {
                    var wrapper = $(textBlob);
                    if (typeof wrapper.attr('outerHTML') === 'undefined') {
                        throw 'InvalidText';
                    }
                } catch (e) {
                    try {
                        var wrapper = $($.parseXML(textBlob));
                    } catch (e) {
                        return textBlob;
                    }
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
                return utils.cleanUp(wrapper.contents().prop('outerHTML'));
            } else {
                return utils.cleanUp(wrapper.prop('outerHTML'));
            }
        };

        return utils;
 });