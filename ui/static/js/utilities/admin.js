// Administrative utility methods
// File: utilities/admin.js

define(['jquery',
        'underscore',
        'text!templates/processing.html'],
    function ($, _, ProcessingTemplate) {

    var _admin = {};

    _admin.activeAsset = function () {
        return $('#dashboard_main_content').find('li.asset-name.active')
            .data("raw-object");
    };

    _admin.activeAssetId = function () {
        return _admin.activeAsset()['mecqbankId'];
    };


    _admin.activeAssignment = function () {
        return $('#dashboard_main_content').find('li.assignment-name.active')
            .data("raw-object");
    };

    _admin.activeAssignmentId = function () {
        return _admin.activeAssignment()['mecqbankId'];
    };

    _admin.activeItem = function () {
        return $('#dashboard_main_content').find('li.item-serial-number.active')
            .data("raw-object");
    };

    _admin.activeItemId = function () {
        return _admin.activeItem()['mecqbankId'];
    };

    _admin.activeItemRemoveFromUI = function () {
        $('#dashboard_main_content').find('li.item-serial-number.active')
            .remove();
    };

    _admin.activePublishedItem = function () {
        return $('#dashboard_main_content').find('tr.published-item-row.active')
            .data("raw-object");
    };

    _admin.activePublishedItemId = function () {
        return _admin.activePublishedItem()['mecqbankId'];
    };

    _admin.activeSubject = function () {
        return $('#dashboard_sidebar_content').find('li.active')
            .data("raw-object");
    };

    _admin.activeSubjectId = function () {
        return _admin.activeSubject()['id'];
    };

    _admin.api = function () {
        return _admin.root() + 'api/v1/';
    };

    _admin.bindDialogCloseEvents = function () {
        $('div[role="dialog"] button.ui-dialog-titlebar-close').text('x');

        $(document).on('click', '.ui-widget-overlay', function(){
            $(".ui-dialog-titlebar-close").trigger('click');
        });
    };

    _admin.blockBody = function (message) {
        $('body').block({
            message: '<h1>' + message + '</h1>',
            centerY: false,
            css: {
                border: '3px solid #a00',
                position: 'fixed',
                top: '100px',
                'z-index': '2010'
            },
            overlayCSS: {
                'z-index': '2000'
            }
        });
    };

    _admin.blockEle = function (ele) {
        $(ele).block({
            message: null
        });
    };

    _admin.blockNav = function () {
        $('.navbar').block({
            message: null
        });
    };

    _admin.blockPage = function (message) {
        _admin.blockBody(message);
        _admin.blockNav();
    };

    _admin.clearStatusBoxes = function () {
        $('.statusBox').text('');
    };

    _admin.doneProcessing = function () {
        _admin.updateStatus('');
    };

    _admin.download = function (url) {
        window.open(url);
    };

    _admin.encodeLatex = function (tex) {
        tex = tex.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
        return tex;
    };

    _admin.getCookie = function (name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    _admin.getNow = function () {
        var dateObj = new Date(),
            nowYear = dateObj.getFullYear(),
            nowMonth = dateObj.getMonth() + 1,
            termToMonth = {
                iap     : 1,
                spring  : 2,
                summer  : 6,
                fall    : 9
            };

        return {
            nowYear     : nowYear,
            nowMonth    : nowMonth,
            termToMonth : termToMonth
        };
    };

    _admin.json = function (obj) {
        // make sure this is a json object
        try {
            obj = $.parseJSON(obj);
        } catch (e) {
            // pass
        }
        return obj;
    };

    _admin.length = function (obj) {
        if ($.isArray(obj)) {
            return obj.length;
        } else {
            return Object.keys(obj).length;
        }
    };

    _admin.pluralize = function (string) {
        if (string === 'class') {
            return 'classes';
        } else {
            return string + 's';
        }
    };

    _admin.processing = function () {
        _admin.updateStatus(_.template(ProcessingTemplate));
    };

    _admin.questionType = function (obj) {
        var _lookupTable = {
            'question-type%3Amecqbank-long-question%40ODL.MIT.EDU'  : 'long',
            'question-type%3Amecqbank-concept-question%40ODL.MIT.EDU'  : 'concept',
            'question-type%3Amecqbank-mcq-question%40ODL.MIT.EDU'  : 'mcq',
            'question-type%3Amecqbank-tf-question%40ODL.MIT.EDU'  : 'true/false',
            'question-type%3Amecqbank-code-question%40ODL.MIT.EDU'  : 'code',
            'question-type%3Amecqbank-unknown-question%40ODL.MIT.EDU'  : 'unknown'
        };
        return _lookupTable[obj['genusTypeId']];
    };

    _admin.removeBRs = function ($ele) {
        $ele.find('br').remove();
    };

    _admin.resetUploadProgress = function () {
        $(".progress").show();
        $(".bar").width('0%');
        $(".percent").html("0%");
        $('#upload_status_text').text('');
    };

    _admin.rawObject = function (obj) {
        return JSON.stringify(obj).replace(/"/g, '&quot;');
    };

    _admin.reportError = function (xhr) {
        _admin.updateStatus('Server error: ' + xhr.responseText);
    };

    _admin.root = function () {
        var page, root;

        // Set the ROOT url, to access all other URLs
        page = document.location.href;

//        if (page.indexOf('/mecqbank/touchstone/dashboard/') >= 0) {
//            root = '/mecqbank/touchstone/dashboard/';
//        } else if (page.indexOf('/mecqbank/') >= 0) {
//            root = '/mecqbank/dashboard/';
//        } else if (page.indexOf('/touchstone/dashboard/') >= 0) {
//            root = '/touchstone/dashboard/';
//        } else if (page.indexOf('127.0.0.1') >= 0 ||
//                page.indexOf('localhost') >= 0){
//            root = '/';
//        } else {
//            root = '/';
//        }
        root = '/';  // for MecQBank, this should always point to the /api/v1

        return root;
    };

    _admin.sendAjax = function (params, on_success, on_fail, on_always) {
        var method = 'GET';
        on_fail = typeof on_fail !== 'undefined' ? on_fail : null;
        on_always = typeof on_always !== 'undefined' ? on_always : null;

        if (params.hasOwnProperty('method')) {
            method = params['method'];
        }
        var data = {};
        if (params.hasOwnProperty('data')) {
            data = params['data'];
        }
        $.ajax({
            data: data,
            type: method,
            url: params['url']
        }).done(function (results) {
            if (on_success) {on_success(results);}
        }).fail(function(xhr, status, error) {
            if(on_fail) {on_fail();}
            _admin.updateStatus('Server error: ' + error);
        }).always(function(xhr, status, error) {
            if (on_always) {on_always();}
        });
    };

    _admin.setCSRFCookie = function (formId) {
        if (typeof formId === 'string') {
            $('#' + formId).find('input[name="csrfmiddlewaretoken"]')
                .val(_admin.getCookie('csrftoken'));
        } else {
            $(formId).find('input[name="csrfmiddlewaretoken"]')
                .val(_admin.getCookie('csrftoken'));
        }
    };

    _admin.shortenName = function (string) {
        if (typeof string === 'string') {
            if (string.length > 25) {
                var short_name = string.substring(0, 20) + '...';
            } else {
                var short_name = string;
            }
        } else {
            var short_name = null;
        }
        return short_name;
    };

    _admin.singularize = function (string) {
        if (string === 'classes') {
            return 'class';
        } else {
            return string.slice(0, -1);
        }
    };

    _admin.termTimeFromNow  = function (term) {
        // returns number of years the term is from now

        var termYear = term.split(' ')[1],
            termName = term.split(' ')[0],
            now = _admin.getNow(),
            nowYear = now.nowYear,
            nowMonth = now.nowMonth,
            termToMonth = now.termToMonth,
            termMonth = termToMonth[termName.toLowerCase()],
            yearsAgo, rolloverDifference;

        yearsAgo = nowYear - termYear;
        if (yearsAgo > 0) {
            if (termMonth < nowMonth) {
                if (nowMonth - termMonth > 6) {
                    yearsAgo++;
                } else {
                    yearsAgo += 0.5;
                }
                // if nowMonth == termMonth, then don't need to adjust the year
                // i.e. 2-2015 to 2-2013, is only 2 years ago, which is already
                // accounted for in the year calculation
            } else if (termMonth != nowMonth) {
                // i.e. 2-2015 to 9-2013 should be 1.5 years
                rolloverDifference = nowMonth + (12 - termMonth);
                if (rolloverDifference > 6) {
                    yearsAgo++;
                } else {
                    yearsAgo += 0.5;
                }
            }
        }
        return yearsAgo;
    };

    // http://stackoverflow.com/questions/1026069/capitalize-the-first-letter-of-string-in-javascript
    _admin.toTitle = function (string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    };

    _admin.unbindContentNavbar = function () {
        $('#dashboard_content_navbar').unbind();
    };

    _admin.unbindMainContent = function () {
        $('#dashboard_main_content').unbind();
    };

    _admin.unblockBody = function () {
        $('body').unblock();
    };

    _admin.unblockEle = function (ele) {
        $(ele).unblock();
    };

    _admin.unblockNav = function () {
        $('.navbar').unblock();
    };

    _admin.unblockPage = function () {
        _admin.unblockBody();
        _admin.unblockNav();
    };

    _admin.updateStatus = function (msg, time) {
//        time = typeof time !== 'undefined' ? time : 150000;
        $('.statusBox').html(msg)
            .addClass('red');
//        setTimeout(_admin.clearStatusBoxes, time);
    };

    return _admin;
});