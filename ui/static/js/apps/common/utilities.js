// apps/common/utilities.js

define(["jquery", "underscore"],
    function ($, _) {

        var utils = {};
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
            $('.repository-menu').data('id', $(domainMatch).data('id'));
            $("ul.repository-navbar li").removeClass('hidden');
        };

        utils.selectedRepoId = function (path) {
            var domainMatch = utils.getMatchingDomainOption('#repos/' + path);
            return $(domainMatch).data('id');
        };

        return utils;
 });