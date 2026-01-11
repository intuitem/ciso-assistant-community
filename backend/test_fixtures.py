# Shared test fixtures and constants

# Valid minimal risk matrix json_definition for tests
RISK_MATRIX_JSON_DEFINITION = {
    "probability": [
        {
            "abbreviation": "L",
            "name": "Low",
            "description": "Low probability",
            "hexcolor": "#00FF00",
        },
        {
            "abbreviation": "M",
            "name": "Medium",
            "description": "Medium probability",
            "hexcolor": "#FFFF00",
        },
        {
            "abbreviation": "H",
            "name": "High",
            "description": "High probability",
            "hexcolor": "#FF0000",
        },
    ],
    "impact": [
        {
            "abbreviation": "L",
            "name": "Low",
            "description": "Low impact",
            "hexcolor": "#00FF00",
        },
        {
            "abbreviation": "M",
            "name": "Medium",
            "description": "Medium impact",
            "hexcolor": "#FFFF00",
        },
        {
            "abbreviation": "H",
            "name": "High",
            "description": "High impact",
            "hexcolor": "#FF0000",
        },
    ],
    "risk": [
        {
            "abbreviation": "L",
            "name": "Low",
            "description": "Low risk",
            "hexcolor": "#00FF00",
        },
        {
            "abbreviation": "M",
            "name": "Medium",
            "description": "Medium risk",
            "hexcolor": "#FFFF00",
        },
        {
            "abbreviation": "H",
            "name": "High",
            "description": "High risk",
            "hexcolor": "#FF0000",
        },
    ],
    "grid": [
        [0, 0, 1],
        [0, 1, 2],
        [1, 2, 2],
    ],
}
