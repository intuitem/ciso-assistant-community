const m = '{\
    "probability" : [\
     {"abbreviation": "L", "name": "Low", "description": "Unfrequent event"},\
     {"abbreviation": "M", "name": "Medium", "description": "Occasional event"},\
     {"abbreviation": "H", "name": "High", "description": "Frequent event"}\
    ],\
    "impact": [\
     {"abbreviation": "L", "name": "Low", "description": "<100k$"},\
     {"abbreviation": "M", "name": "Medium", "description": "between 100 to 1000k$"},\
     {"abbreviation": "H", "name": "High", "description": ">1000k$"}\
    ],\
    "risk": [\
     {"abbreviation": "L", "name": "Low", "description": "acceptable risk"},\
     {"abbreviation": "M", "name": "Medium", "description": "risk requiring mitigation within 2 years"},\
     {"abbreviation": "H", "name": "High", "description": "unacceptable risk"}\
    ],\
    "combine": {\
      "00": 0,\
      "01": 0,\
      "02": 1,\
      "10": 0,\
      "11": 1,\
      "12": 2,\
      "20": 1,\
      "21": 2,\
      "22": 2\
    },\
    "grid": [\
            [0, 0, 1],\
            [0, 1, 2],\
            [1, 2, 2]\
        ]\
}'; // DEBUG, used to test the functions below

function getArray(matrix) {
    const parsed_matrix = JSON.parse(matrix);
    var array = new Array();
    for (var i = 0; i < parsed_matrix.probability.length; i++) {
        array[i] = new Array();
        for (var j = 0; j < parsed_matrix.impact.length; j++) {
            array[i][j] = parsed_matrix.grid[i][j];
        }
    }
    return array;
}

function getLabel(matrix, index) {
    const parsed_matrix = JSON.parse(matrix);
    return parsed_matrix.risk[index].name;
}

function getLabelsArray(array) {
    var labels = new Array();
    for (var i = 0; i < array.length; i++) {
        labels[i] = new Array();
        for (var j = 0; j < array[i].length; j++) {
            labels[i][j] = getLabel(m, array[i][j]);
        }
    }
    return labels;
}

function getMatrixFields(matrix) {
    const parsed_matrix = JSON.parse(matrix);
    var array = new Array();
    for (var i = 0; i < parsed_matrix.probability.length; i++) {
        array[i] = new Array();
        for (var j = 0; j < parsed_matrix.impact.length; j++) {
            var dict = new Object();
            dict["probability"] = parsed_matrix.probability[i];
            dict["impact"] = parsed_matrix.impact[j];
            dict["risk"] = parsed_matrix.risk[parsed_matrix.grid[i][j]];
            array[i][j] = dict;
        }
    }
    return array;
}

function renderMatrix(matrix) {
    const array = getMatrixFields(matrix);
    var table = document.getElementById("matrix");
    for (var i = 0; i < array.length; i++) {
        var row = table.insertRow(i);
        for (var j = 0; j < array[i].length; j++) {
            var cell = row.insertCell(j);
            cell.innerHTML = array[i][j].risk.abbreviation; // DEBUG
        }
    }
}

function getRiskFromVector(matrix, vectorString) {
    const parsed_matrix = JSON.parse(matrix);

    var risk = new Object();

    var vectorStringTrimmed = vectorString.replace(/[^0-9a-z]/gi, '');
    var vector = new Array();
    for (var i = 0; i < vectorStringTrimmed.length; i++) {
        vector[i] = vectorStringTrimmed.charAt(i);
    }
    console.debug(vector);

    var probabilityScore = 0;
    var impactScore = 0;

    for (var i = 0; i < vector.length / 2; i++) {
        probabilityScore += parseInt(vector[i]);
    }
    probabilityScore /= 8;

    for (var i = vector.length / 2; i < vector.length; i++) {
        impactScore += parseInt(vector[i]);
    }
    impactScore /= 4;

    risk['probabilityScore'] = probabilityScore; // DEBUG, will be used to determine which label to use
    risk['impactScore'] = impactScore; // DEBUG, same as above

    return risk;
}

console.debug(getMatrixFields(m));
console.debug(getRiskFromVector(m, "1823-1239-1320-0000"));

// function drawMatrix(matrix) {
//     var table = document.getElementById("matrix");
//     for (var i = 0; i < matrix.length; i++) {
//         var row = table.insertRow(i);
//         for (var j = 0; j < matrix[i].length; j++) {
//             var cell = row.insertCell(j);
//             cell.innerHTML = matrix[i][j];
//         }
//     }
// }

// function buildMatrixFromJsonObject(json_matrix) {
//     var matrix = new Array();
//     for (var i = 0; i < json_matrix.length; i++) {
//         matrix[i] = new Array();
//         for (var j = 0; j < json_matrix[i].length; j++) {
//             matrix[i][j] = json_matrix[i][j];
//         }
//     }
// }

// function getObjectsFromJSON(json) {
//     var objects = JSON.parse(json);
//     return objects;
// }

