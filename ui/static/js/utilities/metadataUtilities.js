// Metadata utility methods
// File: utilities/metadataUtilities.js

define(['jquery',
        'underscore',
        'text!templates/itemMetadataNonEditable.html'],
    function ($, _, ItemMetadataNonEditableTemplate) {
        var _metadata = {};

        function getProperty(obj, prop) {
            // This method is from here:
            // http://stackoverflow.com/questions/6491463/accessing-nested-javascript-objects-with-string-key
            var parts = prop.split('.'),
                last = parts.pop(),
                l = parts.length,
                i = 1,
                current = parts[0];

            while((obj = obj[current]) && i < l) {
                current = parts[i];
                i++;
            }

            if(obj) {
                return obj[last];
            }
        }

        _metadata.render = function ($target, data) {
            var metadataMap = [['Branches','branches'],
                               ['Keywords', 'description.text'],
                               ['Difficulty','texts.difficulty.text'],
                               ['Source','texts.source.text'],
                               ['Subbranches','subbranches'],
                               ['Type','genusTypeId'],
                               ['Terms', 'terms']];

            _.each(metadataMap, function (metadataItem) {
                var fieldName = metadataItem[0],
                    fieldMap = metadataItem[1],
                    label = fieldName,
                    value = getProperty(data, fieldMap);
                if (['Difficulty', 'Source'].indexOf(fieldName) >= 0) {
                    // do nothing, keep value the same
                } else if (fieldName == 'Type') {
                    value = data[fieldMap];
                    if (value.indexOf('long') >= 0) {
                        value = 'long';
                    } else if (value.indexOf('concept') >= 0) {
                        value = 'conceptual';
                    } else if (value.indexOf('tf') >= 0) {
                        value = 'true / false';
                    } else if (value.indexOf('code') >= 0) {
                        value = 'code';
                    } else if (value.indexOf('mcq') >= 0) {
                        value = 'multiple choice';
                    } else {
                        value = 'unknown';
                    }
                } else if (fieldName == 'Branches') {
                    value = data[fieldMap].join('; ');
                } else if (fieldName == 'Subbranches') {  // subbranches
                    value = data[fieldMap].join('; ');
                } else if (fieldName == 'Terms') {
                    value = data[fieldMap].join(', ');
                }

                $target.append(_.template(ItemMetadataNonEditableTemplate, {
                    metadataField: label,
                    metadataValue: value
                }));
            });
        };

        return _metadata;
});
