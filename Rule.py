import json
from py_expression_eval import Parser  # You'll need to install this library

# Rule definition in JSON format
rule_json = """
{
  "version": "3.1",
  "metadata": {
    "rule_name": "Combined Eligibility Rule"
  },
  "actions": [
    {
      "type": "post_to_queue",
      "queue_name": "eligible_customers"
    },
    {
      "type": "log",
      "message": "Rule triggered for eligibility"
    }
  ],
  "extensions": {
    "custom_functions": [
      {
        "name": "myCustomFunction",
        "description": "A custom function"
      }
    ]
  },
  "parameters": {
    "customerId": {
      "value": "$customerId",
      "mandatory": true
    },
    "accountNumber": {
      "value": "$accountNumber",
      "mandatory": false
    },
    "branchId": {
      "value": "$branchId",
      "mandatory": false
    },
    "customerStatus": {
      "value": "$customerStatus",
      "mandatory": true
    }
  },
  "conditions": [
    {
      "entity": "customer",
      "filters": [
        {
          "field": "customer_id",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "$customerId"
        },
        {
          "field": "status",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "$customerStatus"
        }
      ],
      "op": "and",
      "terms": [
        {
          "field": "age",
          "type": "integer",
          "function": "comp",
          "operator": "gt",
          "value": {
            "expr": {
              "language": "juel",
              "expression": "${18 + 80}"
            }
          }
        }
      ]
    },
    {
      "entity": "account",
      "filters": [
        {
          "field": "customer_id",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "$customerId"
        }
      ],
      "op": "and",
      "terms": [
        {
          "field": "account_type",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "SB"
        },
        {
          "field": "balance",
          "type": "number",
          "function": "comp",
          "operator": "gt",
          "value": 1000
        },
        {
          "field": "balance",
          "type": "number",
          "function": "sum",
          "filters": [
            {
              "field": "flag",
              "type": "string",
              "function": "comp",
              "operator": "equals",
              "value": {
                "expr": {
                  "language": "juel",
                  "expression": "${'open'}"
                }
              }
            }
          ],
          "operator": "equals",
          "value": 20000
        }
      ]
    },
    {
      "entity": "audienceSegments",
      "filters": [
        {
          "field": "customer_id",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "$customerId"
        }
      ],
      "op": "or",
      "terms": [
        {
          "op": "and",
          "terms": [
            {
              "field": "flow_id",
              "type": "integer",
              "function": "comp",
              "operator": "equals",
              "value": 30
            },
            {
              "field": "var_id",
              "type": "integer",
              "function": "comp",
              "operator": "equals",
              "value": 40
            }
          ]
        },
        {
          "op": "and",
          "terms": [
            {
              "field": "flow_id",
              "type": "integer",
              "function": "comp",
              "operator": "equals",
              "value": 30
            },
            {
              "field": "var_id",
              "type": "integer",
              "function": "comp",
              "operator": "equals",
              "value": 45
            }
          ]
        }
      ]
    },
    {
      "entity": "branch",
      "filters": [
        {
          "field": "branch_id",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "$branchId",
          "optional": true
        }
      ],
      "op": "and",
      "terms": [
        {
          "field": "location",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "Bengaluru"
        },
        {
          "entity": "suppliers",
          "op": "and",
          "terms": [
            {
              "field": "supplier_type",
              "type": "string",
              "function": "comp",
              "operator": "equals",
              "value": "Gold"
            },
            {
              "field": "supplier_status",
              "type": "string",
              "function": "comp",
              "operator": "equals",
              "value": "approved"
            }
          ]
        }
      ]
    },
    {
      "entity": "calendar",
      "filters":,
      "op": "and",
      "terms": [
        {
          "field": "day_of_week",
          "type": "string",
          "function": "comp",
          "operator": "equals",
          "value": "Friday"
        }
      ]
    }
  ]
}
"""

# Mock data for the GraphQL response
data = {
    "customer": {
        "customer_id": 123,
        "age": 105,
        "status": "active",
        "active_days": 200
    },
    "account": [
        {
            "customer_id": 123,
            "account_number": "ACC123",
            "account_type": "SB",
            "balance": 1500,
            "flag": "open"
        },
        {
            "customer_id": 123,
            "account_number": "ACC456",
            "account_type": "CA",
            "balance": 5000,
            "flag": "open"
        }
    ],
    "audienceSegments": [
        {
            "customer_id": 123,
            "flow_id": 30,
            "var_id": 40
        }
    ],
    "branch": {
        "branch_id": "BR123",
        "location": "Bengaluru",
        "suppliers": [
            {
                "supplier_type": "Gold",
                "supplier_status": "approved"
            }
        ]
    },
    "day_of_week": "Friday"
}

# Provide input variables
variables = {
    "customerId": 123,
    "accountNumber": "ACC123",
    "branchId": "BR123",
    "customerStatus": "active"
}

# Initialize JUEL expression parser
parser = Parser()

def evaluate_rule(rule, data, variables):
    conditions = rule["conditions"]

    def evaluate_condition(condition, data):
        if "filters" in condition:
            filter_results = [evaluate_filter(filter, data) for filter in condition["filters"]]
            if not all(filter_results):
                return False

        if "op" in condition:
            results = [evaluate_condition(term, data) for term in condition["terms"]]
            if condition["op"] == "and":
                return all(results)
            elif condition["op"] == "or":
                return any(results)
        else:
            return evaluate_term(condition, data)

    def evaluate_filter(filter, data):
        field = filter["field"]
        comp = filter["operator"]
        value = filter["value"]
        optional = filter.get("optional", False)

        if isinstance(value, dict) and "expr" in value:
            value = evaluate_expression(value["expr"], data)

        if value.startswith("$"):
            value = variables.get(value[1:])
            if value is None and optional:
                return True

        actual_value = get_field_value(data, field)
        if comp == "equals":
            return actual_value == value
        elif comp == "gt":
            return actual_value > value
        # Add other comparison operators as needed

    def evaluate_term(term, data):
        field = term["field"]
        func = term["function"]
        comp = term["operator"]
        value = term["value"]

        if isinstance(value, dict) and "expr" in value:
            value = evaluate_expression(value["expr"], data)

        if func == "comp":
            actual_value = get_field_value(data, field)
            if comp == "equals":
                return actual_value == value
            elif comp == "gt":
                return actual_value > value
            # Add other comparison operators as needed
        elif func == "sum":
            # Apply filters before sum
            filtered_data = data
            if "filters" in term:
                for filter in term["filters"]:
                    filtered_data = [item for item in filtered_data if evaluate_filter(filter, item)]
            values_to_sum = [get_field_value(item, field) for item in filtered_data]
            sum_value = sum(values_to_sum)
            return eval(f"{sum_value} {comp} {value}")

    def get_field_value(data, field_path):
        fields = field_path.split(".")
        value = data
        for field in fields:
            if isinstance(value, list):
                value = value  # Assuming single element in list for now
            value = value.get(field)
            if value is None:
                return None
        return value

    def evaluate_expression(expr, data):
        if expr["language"] == "juel":
            expression = expr["expression"][2:-1]  # Remove ${} from JUEL expression
            return parser.parse(expression).evaluate(create_juel_context(data))

    def create_juel_context(data):
        # Create a JUEL context with data
        context = SimpleContext()
        for key, value in data.items():
            context.setVariable(key, expressionFactory.createValueExpression(value, Object.class))
        return context

    results = [evaluate_condition(condition, data) for condition in conditions]
    return all(results)  # Assuming overall "and" condition

# Load the rule from JSON
rule = json.loads(rule_json)

# Evaluate the rule
result = evaluate_rule(rule, data, variables)

# Print the result
if result:
    print("Rule evaluated to TRUE")
    # You can add logic here to perform the action specified in the metadata
else:
    print("Rule evaluated to FALSE")