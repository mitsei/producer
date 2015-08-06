// apps/dashboard/assets/assets_view.js

// Filename: app.js

define([
  'app',
  'jquery',
  'underscore',
  'marionette',
  'apps/dashboard/assets/models/asset'
], function(ProducerManager, $, _, Backbone, Marionette, AssetModel){
    ProducerManager.AssetItemView = Marionette.ItemView.extend({
        initialize: function () {
            this.model.on('change', this.render, this);
        }
    })
});