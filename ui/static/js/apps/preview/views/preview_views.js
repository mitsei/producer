// apps/preview/views/preview_views.js

define(["app",
        "apps/common/utilities",
        "apps/dashboard/assets/models/assets",
        "apps/dashboard/compositions/models/composition",
        "text!apps/preview/templates/resource_preview.html"],
       function(ProducerManager, Utils, AssetModel, CompositionModel, ResourceTemplate){
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
    });

  });

  return ProducerManager.PreviewApp.View;
});