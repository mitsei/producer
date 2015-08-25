// apps/preview/views/preview_views.js

define(["app",
        "apps/common/utilities",
        "apps/dashboard/assets/models/assets",
        "apps/dashboard/compositions/models/composition",
        "text!apps/preview/templates/resource_preview.html",
        "text!apps/preview/templates/composition_preview.html",
        "text!apps/preview/templates/unit_button.html"],
       function(ProducerManager, Utils, AssetModel, CompositionModel,
                ResourceTemplate, CompositionTemplate, UnitButtonTemplate){
  ProducerManager.module("PreviewApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    View.ResourceView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;
            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        template: false,
        onRender: function (e) {
            var serializedData = this.options,
                resource = new AssetModel({
                    id: serializedData.objId,
                    renderable: true
                }),
                promise = resource.fetch(),
                _this = this,
                resource,
                sourceDoc;

            Utils.processing();

            promise.done(function (data) {
                Utils.doneProcessing();
                if (data.type === 'Asset') {
                    sourceDoc = Utils.wrapText(data.assetContents[0].text.text);
                } else {
                    sourceDoc = Utils.wrapText(data.texts.edxml);
                }
                _this.$el.html(_.template(ResourceTemplate) ({
                    displayName: data.displayName.text,
                    resource: sourceDoc
                }));
            });
        },
        events: {
        }
    });

    View.CompositionView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;
            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        tagName: 'div',
        className: 'composition-preview-wrapper',
        template: function () {
            return _.template(CompositionTemplate)();
        },
        onShow: function (e) {
            var serializedData = this.options,
                composition = new CompositionModel({
                    id: serializedData.objId,
                    renderable: true
                }),
                promise = composition.fetch(),
                _this = this,
                $sidebarHeader = $('.sidebar-header'),
                $sidebarList = $('.sidebar-list'),
                $verticalList = $('.vertical-list'),
                $contentList = $('.content-list'),
                sidebars, verticals, contents, sourceDoc;

            Utils.processing();

            promise.done(function (data) {
                Utils.doneProcessing();

                $sidebarHeader.text(data.displayName.text);
                sidebars = data.children;
                contents = data.assets;

                if (sidebars.length === 0) {
                    $sidebarList.addClass('hidden');
                } else {
                    $sidebarList.removeClass('hidden');
                    _.each(sidebars, function (sidebar) {
                        $sidebarList.append(_.template(UnitButtonTemplate)({
                            buttonType: 'sidebar',
                            displayName: sidebar.displayName.text,
                            rawObj: JSON.stringify(sidebar)
                        }));
                    })
                }

                if (contents.length > 0) {
                    $contentList.empty();
                    _.each(contents, function (content) {
                        if (content.type === 'Asset') {
                            sourceDoc = Utils.wrapText(content.assetContents[0].text.text);
                        } else {
                            sourceDoc = Utils.wrapText(content.texts.edxml);
                        }
                        $contentList.append(_.template(ResourceTemplate) ({
                            displayName: content.displayName.text,
                            resource: sourceDoc
                        }));
                    });

                    $contentList.find('iframe').each(function() {
                        $(this).load(function () {
                            $(this).css('height', $(this).contents().height());
                        });
                    });
                }
            });
        },
        events: {

        }
    });

  });

  return ProducerManager.PreviewApp.View;
});