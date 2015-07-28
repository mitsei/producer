// LaTeX utility methods
// File: utilities/texUtilities.js

define(['jquery',
        'underscore'],
    function ($, _) {
        var _tex = {};

        function extractFigureName (text) {
            var initialAttempt = extractTextBetweenCurlyBraces(text);
            if (initialAttempt.indexOf('.pdf') < 0) {
                return initialAttempt + '.pdf';
            } else {
                return initialAttempt;
            }
        }

        function extractTextBetweenCurlyBraces (text) {
            return text.substring(text.indexOf('{') + 1, text.indexOf('}'));
        }

        _tex.extractImageFileNames = function (fileObjects, _callback) {
            var figureNames = [],
                reader, counter;

            counter = fileObjects.length;

            _.each(fileObjects, function (fileObject) {
                reader = new FileReader();
                reader.onload = function (e) {
                    var lines = e.target.result.split('\n'),
                        figureName;
                    _.each(lines, function (line) {
                        if (line.indexOf('includegraphics') >= 0) {
                            figureName = extractFigureName(line);
                            figureNames.push(figureName);
                        }
                    });

                    --counter;
                    if (counter === 0) {
                        _callback(figureNames);
                    }
                };
                reader.readAsText(fileObject);
            });
        };

        return _tex;
});
