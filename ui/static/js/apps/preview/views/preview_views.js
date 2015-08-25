// apps/preview/views/preview_views.js

define(["app",
        "apps/common/utilities",
        "apps/dashboard/assets/models/assets",
        "apps/dashboard/compositions/models/composition",
        "text!apps/preview/templates/resource_preview.html",
        "text!apps/preview/templates/composition_preview.html",
        "text!apps/preview/templates/unit_button.html",
        "bootstrap"],
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
                sidebars, contents, sourceDoc;

            Utils.processing();

            promise.done(function (data) {
                Utils.doneProcessing();

                $sidebarHeader.text(data.displayName.text);
                sidebars = data.children;
                contents = data.assets;

                _this.updateButtons($sidebarList, sidebars, 'sidebar');
                _this.updateContents(contents);
            });
        },
        events: {
            'click button.sidebar-btn': 'showChildrenCompositions'
        },
        setActiveState: function ($e) {
            $e.siblings().removeClass('active');
        },
        showChildrenCompositions: function (e) {
            var $e = $(e.currentTarget),
                $obj = $e.data('obj'),
                $children = $obj.children,
                $verticalList = $('.vertical-list'),
                contents = $obj.assets,
                numContents = contents.length,
                renderableContents = [],
                _this = this;

            _this.setActiveState($e);
            _this.updateButtons($verticalList, $children, 'vertical');

            Utils.processing();

            _.each(contents, function (content) {
                var resource = new AssetModel({
                        id: content.id,
                        renderable: true
                    }),
                    promise = resource.fetch();

                promise.done(function (data) {
                    renderableContents.push(data);
                    if (--numContents === 0) {
                        Utils.doneProcessing();
                        _this.updateContents(renderableContents);
                    }
                });
            });
        },
        updateButtons: function ($list, $items, tag) {
            if ($items.length === 0) {
                $list.addClass('hidden');
            } else {
                $list.removeClass('hidden');
                $list.empty();
                _.each($items, function (item) {
                    $list.append(_.template(UnitButtonTemplate)({
                        buttonType: tag,
                        displayName: item.displayName.text,
                        rawObj: JSON.stringify(item)
                    }));
                })
            }
        },
        updateContents: function (contents) {
            var $contentList = $('.content-list');

            if (contents.length > 0) {
                $contentList.empty();
                _.each(contents, function (content) {
                    if (content.type === 'Asset') {
                        sourceDoc = Utils.wrapText(content.assetContents[0].text.text);
                    } else {
                        sourceDoc = Utils.wrapText(content.texts.edxml);
                    }
                    $contentList.append(_.template(ResourceTemplate)({
                        displayName: content.displayName.text,
                        resource: sourceDoc
                    }));
                });

                $contentList.find('iframe').each(function () {
                    $(this).load(function () {
                        $(this).css('height', $(this).contents().height());
                    });
                });
            }
        }
    });

  });

  return ProducerManager.PreviewApp.View;
});