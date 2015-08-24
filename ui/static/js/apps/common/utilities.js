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
        };

        utils.parseGenusType = function (genusTypeStr) {
            return genusTypeStr.slice(genusTypeStr.indexOf('%3A') + 3,
                                      genusTypeStr.indexOf('%40'));
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

        return utils;
 });