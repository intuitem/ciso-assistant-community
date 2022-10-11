const m = '{\
    "probability" : [\
     {"abbreviation": "L", "label": "Low", "description": "Unfrequent event"},\
     {"abbreviation": "M", "label": "Medium", "description": "Occasional event"},\
     {"abbreviation": "H", "label": "High", "description": "Frequent event"}\
    ],\
    "impact": [\
     {"abbreviation": "L", "label": "Low", "description": "<100k$"},\
     {"abbreviation": "M", "label": "Medium", "description": "between 100 to 1000k$"},\
     {"abbreviation": "H", "label": "High", "description": ">1000k$"}\
    ],\
    "risk": [\
     {"abbreviation": "L", "label": "Low", "description": "acceptable risk", "rgb": "#BBF7D0"},\
     {"abbreviation": "M", "label": "Medium", "description": "risk requiring mitigation within 2 years", "rgb": "#BEF264"},\
     {"abbreviation": "H", "label": "High", "description": "unacceptable risk", "rgb": "#F87171"}\
    ],\
    "grid": [\
            [0, 0, 1],\
            [0, 1, 2],\
            [1, 2, 2]\
        ]\
}'; // DEBUG, used to test the functions below

const m2 = '{\
    "probability" : [\
     {"abbreviation": "VL", "label": "Very Low", "description": "Unfrequent event"},\
     {"abbreviation": "L", "label": "Low", "description": "Unfrequent event"},\
     {"abbreviation": "M", "label": "Medium", "description": "Occasional event"},\
     {"abbreviation": "H", "label": "High", "description": "Frequent event"},\
     {"abbreviation": "VH", "label": "Very High", "description": "Frequent event"}\
    ],\
    "impact": [\
     {"abbreviation": "VL", "label": "Very Low", "description": "<100k$"},\
     {"abbreviation": "L", "label": "Low", "description": "<100k$"},\
     {"abbreviation": "M", "label": "Medium", "description": "between 100 to 1000k$"},\
     {"abbreviation": "H", "label": "High", "description": ">1000k$"},\
     {"abbreviation": "VH", "label": "Very High", "description": ">1000k$"}\
    ],\
    "risk": [\
     {"abbreviation": "VL", "label": "Very Low", "description": "acceptable risk", "rgb": "#BBF7D0"},\
     {"abbreviation": "L", "label": "Low", "description": "acceptable risk", "rgb": "#BEF264"},\
     {"abbreviation": "M", "label": "Medium", "description": "risk requiring mitigation within 2 years", "rgb": "#FEF08A"},\
     {"abbreviation": "H", "label": "High", "description": "unacceptable risk", "rgb": "#FBBF24"},\
     {"abbreviation": "VH", "label": "Very High", "description": "unacceptable risk", "rgb": "#F87171"}\
    ],\
    "grid": [\
        [0, 0, 1, 1, 2],\
        [0, 1, 1, 2, 2],\
        [1, 1, 2, 2, 3],\
        [1, 2, 2, 3, 4],\
        [2, 2, 3, 4, 4]\
    ]\
}'; // DEBUG, used to test the functions below

class RiskEngine {
    constructor(matrix) {
        this.matrix = JSON.parse(matrix);
    }
    get grid() {
        return this.matrix.grid;
    }
    getRiskIndex(probability, impact) {
        return this.grid[probability][impact];
    }
    getRisk(probability, impact) {
        return this.matrix.risk[this.getRiskIndex(probability, impact)];
    }
}

// function getMatrixFields(matrix) {
//     const parsed_matrix = JSON.parse(matrix);
//     var array = new Array();
//     for (var i = 0; i < parsed_matrix.probability.length; i++) {
//         array[i] = new Array();
//         for (var j = 0; j < parsed_matrix.impact.length; j++) {
//             var dict = new Object();
//             dict["probability"] = parsed_matrix.probability[i];
//             dict["impact"] = parsed_matrix.impact[j];
//             dict["risk"] = parsed_matrix.risk[parsed_matrix.grid[i][j]];
//             array[i][j] = dict;
//         }
//     }
//     return array;
// }

// function renderMatrix(matrix) {
//     const array = getMatrixFields(matrix);
//     var table = document.getElementById("matrix");
//     for (var i = 0; i < array.length; i++) {
//         var row = table.insertRow(i);
//         for (var j = 0; j < array[i].length; j++) {
//             var cell = row.insertCell(j);
//             cell.innerHTML = array[i][j].risk.abbreviation; // DEBUG
//         }
//     }
// }

function getScoringFromVector(matrix, vectorString) { // Consider splititng this function
    const parsed_matrix = JSON.parse(matrix);
    const vector = vectorString.replace(/[^0-9a-z]/gi, '').split("");

    // console.debug(vector); // DEBUG

    const probabilityVector = vector.slice(0, vector.length / 2);
    const impactVector = vector.slice(vector.length / 2, vector.length);
    
    // console.debug(impactVector); // DEBUG
    // console.debug(probabilityVector); // DEBUG

    var score = new Object();

    var probabilityScore = 0;
    var impactScore = 0;

    for (var i = 0; i < vector.length / 2; i++) {
        probabilityScore += parseInt(vector[i]);
    }
    probabilityScore /= 8;

    for (var i = vector.length / 2; i < vector.length; i++) {
        impactScore += parseInt(vector[i]);
    }
    if (impactVector.slice(0, 4).every(item => item == 0) || impactVector.slice(4, 8).every(item => item == 0)) {
        impactScore /= 4;
    } else {
        impactScore /= 8;
    }

    score['probabilityScore'] = probabilityScore; // DEBUG, will be used to determine which label to use
    score['impactScore'] = impactScore; // DEBUG, same as above

    return score;
}

function getFactorsValues() {
    // THREAT AGENT FACTORS
    const skill_level = document.getElementById("skill_level").value;
    const motive = document.getElementById("motive").value;
    const opportunity = document.getElementById("opportunity").value;
    const size = document.getElementById("size").value;

    // VULNERABILITY FACTORS
    const ease_of_discovery = document.getElementById("ease_of_discovery").value;
    const ease_of_exploit = document.getElementById("ease_of_exploit").value;
    const awareness = document.getElementById("awareness").value;
    const intrusion_detection = document.getElementById("intrusion_detection").value;

    // TECHNICAL IMPACT FACTORS
    const loss_of_confidentiality = document.getElementById("loss_of_confidentiality").value;
    const loss_of_integrity = document.getElementById("loss_of_integrity").value;
    const loss_of_availability = document.getElementById("loss_of_availability").value;
    const loss_of_accountability = document.getElementById("loss_of_accountability").value;

    // BUSINESS IMPACT FACTORS
    const financial_damage = document.getElementById("financial_damage").value;
    const reputation_damage = document.getElementById("reputation_damage").value;
    const non_compliance = document.getElementById("non_compliance").value;
    const privacy_violation = document.getElementById("privacy_violation").value;

    return [skill_level, motive, opportunity, size, ease_of_discovery, ease_of_exploit, awareness, intrusion_detection,
        loss_of_confidentiality, loss_of_integrity, loss_of_availability, loss_of_accountability, financial_damage,
        reputation_damage, non_compliance, privacy_violation];
}

function buildVector(factors) {
    var vector = "";
    // const factors = getFactorValues();
    // vector is of the form "xxxx-xxxx-xxxx-xxxx"
    for (var i = 0; i < factors.length; i++) {
        vector += factors[i];
        if (i == 3 || i == 7 || i == 11) {
            vector += "-";
        }
    }
    return vector;
}

function renderVector(vector) {
    // const vector = buildVector();
    document.getElementById("vector").innerHTML = vector;
}

function computeFactorsScores(factors, ignoreBusinessImpact) {
    var scores = new Object();
    var f = new Array();
    for (var i = 0; i < factors.length; i++) {
        f.push(parseInt(factors[i]));
    }
    scores['threat_agent'] = (f[0] + f[1] + f[2] + f[3]) / 4;
    scores['vulnerability'] = (f[4] + f[5] + f[6] + f[7]) / 4;
    scores['technical_impact'] = (f[8] + f[9] + f[10] + f[11]) / 4;
    scores['business_impact'] = (f[12] + f[13] + f[14] + f[15]) / 4;

    scores['probability'] = (scores['threat_agent'] + scores['vulnerability']) / 2;
    scores['impact'] = ignoreBusinessImpact ? scores['technical_impact'] : scores['business_impact'];

    scores['risk'] = (scores['probability'] + scores['impact']) / 2;

    // console.debug('scores: '); // DEBUG
    // console.debug(scores); // DEBUG

    return scores;
}

function renderScore(id, score) {
    score === 0 ? document.getElementById(id).innerHTML = "--" : document.getElementById(id).innerHTML = score;
}

function renderScores(scores, isBusinessImpactIgnored) {
    renderScore("threat_agent_score", scores['threat_agent']);
    renderScore("vulnerability_score", scores['vulnerability']);
    renderScore("technical_impact_score", isBusinessImpactIgnored ? scores['technical_impact'] : 0);
    renderScore("business_impact_score", isBusinessImpactIgnored ? 0 : scores['business_impact']);

    document.getElementById("probability_score").innerHTML = scores['probability'] === 0 ? '' : scores['probability'];
    document.getElementById("impact_score").innerHTML = scores['impact'] === 0 ? '' : scores['impact'];
}

function scoreToRating(matrix, score) {
    const parsedMatrix = JSON.parse(matrix);
    const probability = score['probability'];
    const impact = score['impact'];
    const risk = score['risk'];

    // console.debug(probability); // DEBUG
    // console.debug(impact); // DEBUG
    
    const probabilityPartitionSize = 10 / parsedMatrix['probability'].length;
    const impactPartitionSize = 10 / parsedMatrix['impact'].length;
    const riskPartitionSize = 10 / parsedMatrix['risk'].length;
    
    const probabilityIndex = Math.floor(probability / probabilityPartitionSize);
    const impactIndex = Math.floor(impact / impactPartitionSize);
    const riskIndex = Math.floor(risk / riskPartitionSize);
    
    var rating = new Object();
    rating['probability'] = score['probability'] === 0 ? -1 : parsedMatrix.probability[probabilityIndex];
    rating['impact'] = score['impact'] === 0 ? -1 : parsedMatrix.impact[impactIndex];
    rating['risk'] = score['risk'] === 0 ? -1 : parsedMatrix.risk[riskIndex];

    return rating;
}

function renderLabels(labels) {
    // console.debug('labels: '); // DEBUG
    // console.debug(labels); // DEBUG
    document.getElementById("probability_label").innerHTML = labels['probability'] === -1 ? '--' : labels['probability']['label'];
    document.getElementById("impact_label").innerHTML = labels['impact'] === -1 ? '--' : labels['impact']['label'];
    document.getElementById("risk_label").innerHTML = labels['risk'] === -1 ? '--' : labels['risk']['label'];
    document.getElementById("risk_label").style.backgroundColor = labels['risk'] === -1 ? 'white' : labels['risk']['rgb'];
}

function isBusinessImpactIgnored() {
    const scores = computeFactorsScores(getFactorsValues());

    if (document.getElementById("ignore_business_impact").checked) {
        return true;
    }
    // if (scores['technical_impact'] !== 0 && scores['business_impact'] === 0) {
    //     return true;
    // }

    return false;
}

function renderIgnoredFactors() {
    // TECHNICAL IMPACT FACTORS
    const loss_of_confidentiality = document.getElementById("loss_of_confidentiality");
    const loss_of_integrity = document.getElementById("loss_of_integrity");
    const loss_of_availability = document.getElementById("loss_of_availability");
    const loss_of_accountability = document.getElementById("loss_of_accountability");

    // BUSINESS IMPACT FACTORS
    const financial_damage = document.getElementById("financial_damage");
    const reputation_damage = document.getElementById("reputation_damage");
    const non_compliance = document.getElementById("non_compliance");
    const privacy_violation = document.getElementById("privacy_violation");

    const BI_div = document.getElementById("bi_div");
    const TI_div = document.getElementById("ti_div");

    if (isBusinessImpactIgnored()) {
        loss_of_confidentiality.disabled = false;
        loss_of_integrity.disabled = false;
        loss_of_availability.disabled = false;
        loss_of_accountability.disabled = false;

        TI_div.classList.remove("bg-gray-100");
        TI_div.classList.remove("text-gray-400");
        TI_div.classList.add("bg-white");
        TI_div.classList.add("text-black");

        financial_damage.disabled = true;
        reputation_damage.disabled = true;
        non_compliance.disabled = true;
        privacy_violation.disabled = true;

        BI_div.classList.remove("bg-white");
        BI_div.classList.remove("text-black");
        BI_div.classList.add("bg-gray-100");
        BI_div.classList.add("text-gray-400");

        document.getElementById("ignore_business_impact").checked = true;
    } else {
        loss_of_confidentiality.disabled = true;
        loss_of_integrity.disabled = true;
        loss_of_availability.disabled = true;
        loss_of_accountability.disabled = true;

        TI_div.classList.remove("bg-white");
        TI_div.classList.remove("text-black");
        TI_div.classList.add("bg-gray-100");
        TI_div.classList.add("text-gray-400");
        
        financial_damage.disabled = false;
        reputation_damage.disabled = false;
        non_compliance.disabled = false;
        privacy_violation.disabled = false;

        BI_div.classList.remove("bg-gray-100");
        BI_div.classList.remove("text-gray-400");
        BI_div.classList.add("bg-white");
        BI_div.classList.add("text-black");
    }
}

function refresh() {
    const ignoreBusinessImpact = isBusinessImpactIgnored();
    // console.debug(ignoreBusinessImpact); // DEBUG

    const factors = getFactorsValues();
    const vector = buildVector(factors);
    const scores = computeFactorsScores(factors, ignoreBusinessImpact);
    const labels = scoreToRating(m2, scores);


    renderVector(vector);
    renderScores(scores, ignoreBusinessImpact);
    renderLabels(labels);
    renderIgnoredFactors();
}
