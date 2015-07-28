//Filename: views/project/manageGeneralAssets.js

define([
    'jquery',
    'underscore',
    'backbone',
    'admin-utils',
    'bootstrap-dialog',
    'text!templates/uploadNewAsset.html',
    'text!templates/manageGeneralAssets.html',
    'text!templates/noAssetsFound.html',
    'text!templates/assetName.html'
], function ($, _, Backbone, Admin, BootstrapDialog,
             UploadNewAssetTemplate, ManageGeneralAssetsTemplate,
             NoAssetsFoundTemplate, AssetNameTemplate) {


    var ManageGeneralAssetsContentView = Backbone.View.extend({
        className: 'my-subject-general-assets',
        initialize: function () {
            var compiledTemplate = _.template(ManageGeneralAssetsTemplate);
            this.$el.html(compiledTemplate);

            $('#dashboard_main_content').empty()
                .append(this.$el);

            return this;
        },
        render: function () {
            var $assetList = $('ul.asset-filenames');
            Admin.processing();
            $.ajax({
                url:    Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assets/'
            }).error( function (xhr, msg, status) {
                Admin.updateStatus('Server error: ' + xhr.responseText);
            }).success( function (data) {
                data = data['data']['results'];

                if (data.length > 0) {
                    _.each(data, function (datum) {
                        $assetList.append(_.template(AssetNameTemplate, {
                            displayName: datum['name'],
                            rawObject: Admin.rawObject(datum)
                        }));
                    });
                } else {
                    $assetList.append(_.template(NoAssetsFoundTemplate));
                }

                $assetList.append(_.template(UploadNewAssetTemplate));

                Admin.doneProcessing();
            });

            return this;
        },
        events: {
            'change input[name="fileSelector[]"]'   : 'uploadAsset',
            'click label.delete-asset'              : 'deleteAsset',
            'click label.download-asset'            : 'downloadAsset',
            'click li.asset-name'                   : 'showAssetDetails'
        },
        deleteAsset: function (e) {
            var $previewIframe = $('iframe.asset-preview-iframe'),
                $assetPreview = $('section.asset-preview'),
                $assetActions = $('section.asset-actions'),
                $selectedAsset = $('#dashboard_main_content').find('li.asset-name.active');

            $.ajax({
                url : Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                    '/assets/' + Admin.activeAssetId() + '/',
                type: 'DELETE'
            }).error(function (xhr, status, msg) {
                Admin.reportError(xhr);
            }).success(function (data) {
                // re-hide stuff
                $previewIframe.attr('src', '');
                $assetActions.addClass('hidden');
                $assetPreview.addClass('hidden');

                // remove the file from the list
                $selectedAsset.remove();
            });
        },
        downloadAsset: function (e) {
            var url = Admin.api() + 'subjects/' + Admin.activeSubjectId() +
                '/assets/' + Admin.activeAssetId() + '/';

            window.open(url, '_blank');
        },
        showAssetDetails: function (e) {
            var $previewIframe = $('iframe.asset-preview-iframe'),
                $e = $(e.currentTarget),
                rawObject = $e.data('raw-object'),
                url = rawObject.url,
                $assetPreview = $('section.asset-preview'),
                $assetActions = $('section.asset-actions');

            $e.siblings('.active')
                .removeClass('active');
            $e.addClass('active');
            $assetPreview.removeClass('hidden');
            $assetActions.removeClass('hidden');
            $previewIframe.attr('src', url);
        },
        uploadAsset: function (e) {
            var uploadAssetForm = new FormData(),
                assetFile = e.target.files[0],
                $assetList = $('ul.asset-filenames'),
                $addAssetBtn = $('li.upload-new-asset');

            uploadAssetForm.append(assetFile.name, assetFile);

            $.ajax({
                url         : Admin.api() + 'subjects/' + Admin.activeSubjectId() + '/assets/',
                type        : 'POST',
                data        : uploadAssetForm,
                contentType : false,
                processData : false
            }).error(function (xhr, status, msg) {
                Admin.reportError(xhr);
            }).success(function (data) {
                data = data[0];  // only adding one file, so it is first item in response

                $assetList.find('li.no-assets-found')
                    .remove();

                $addAssetBtn.before(_.template(AssetNameTemplate, {
                    displayName: data['name'],
                    rawObject: Admin.rawObject(data)
                }));
            });
        }
    });

    return ManageGeneralAssetsContentView;
});