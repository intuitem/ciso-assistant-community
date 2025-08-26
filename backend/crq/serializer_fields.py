import decimal
import json
from rest_framework import serializers

from crq.models import QuantitativeRiskHypothesis


class ProbabilityField(serializers.Field):
    """
    A custom field to serialize and deserialize the probability,
    which can be a decimal, a frequency, or a proportion.
    """

    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                # Attempt to parse the string as JSON
                data = json.loads(data)
            except json.JSONDecodeError:
                # If it's not a valid JSON string, check if it's a simple number
                try:
                    data = float(data)
                except (ValueError, TypeError):
                    raise serializers.ValidationError(
                        "Input is not valid JSON or a number."
                    )
        # Case 1: Simple decimal probability
        if isinstance(data, (float, int, decimal.Decimal)):
            if not (0 <= data <= 1):
                raise serializers.ValidationError(
                    "Decimal probability must be between 0 and 1."
                )
            return {"type": "decimal", "value": float(data)}

        # Case 2: Structured dictionary for frequency or proportion
        if isinstance(data, dict):
            prob_type = data.get("type")

            if prob_type == "frequency":
                x = data.get("x")
                y_unit = data.get("y_unit")

                if x is None or y_unit is None:
                    raise serializers.ValidationError(
                        "Frequency requires 'x' and 'y_unit' keys."
                    )
                if not isinstance(x, (int, float, decimal.Decimal)) or x < 0:
                    raise serializers.ValidationError(
                        "'x' must be a non-negative number."
                    )
                if y_unit not in [
                    choice[0]
                    for choice in QuantitativeRiskHypothesis.ReferencePeriod.choices
                ]:
                    raise serializers.ValidationError(
                        f"'y_unit' must be one of: {[c[0] for c in QuantitativeRiskHypothesis.ReferencePeriod.choices]}"
                    )

                return data

            elif prob_type == "proportion":
                x = data.get("x")
                y = data.get("y")

                if x is None or y is None:
                    raise serializers.ValidationError(
                        "Proportion requires 'x' and 'y' keys."
                    )
                if not (isinstance(x, int) and isinstance(y, int)):
                    raise serializers.ValidationError("'x' and 'y' must be integers.")
                if x < 0 or y <= 0:
                    raise serializers.ValidationError(
                        "'x' must be non-negative and 'y' must be positive."
                    )
                if x > y:
                    raise serializers.ValidationError(
                        "In a proportion, 'x' cannot be greater than 'y'."
                    )

                return data

            else:
                raise serializers.ValidationError(
                    "Invalid 'type' for probability. Must be 'frequency' or 'proportion'."
                )

        raise serializers.ValidationError(
            "Probability must be a decimal or a dictionary with a valid 'type'."
        )


class ImpactField(serializers.Field):
    """
    A custom field to serialize and deserialize the impact, which includes
    the distribution type and confidence interval bounds.
    """

    def to_representation(self, value):
        return value

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    "Impact field must be a valid JSON object."
                )
        if not isinstance(data, dict):
            raise serializers.ValidationError("Impact must be a dictionary.")

        distribution = data.get("distribution")
        lb = data.get("lb")
        ub = data.get("ub")

        if not all([distribution, lb, ub]):
            raise serializers.ValidationError(
                "Impact requires 'distribution', 'lb', and 'ub' keys."
            )

        if distribution != "LOGNORMAL":
            raise serializers.ValidationError(
                "Currently, only 'LOGNORMAL' distribution is supported."
            )

        if not all(isinstance(val, (int, float, decimal.Decimal)) for val in [lb, ub]):
            raise serializers.ValidationError("'lb' and 'ub' must be numeric values.")

        if lb is None or lb <= 0:
            raise serializers.ValidationError("The lower bound 'lb' must be positive.")

        if ub <= lb:
            raise serializers.ValidationError(
                "The upper bound 'ub' must be greater than the lower bound 'lb'."
            )

        return data
