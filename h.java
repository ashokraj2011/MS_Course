    private static final ObjectMapper objectMapper = new ObjectMapper();

    public static JsonNode getEntityData(String jsonString, String entityName) throws IOException {
        JsonNode rootNode = objectMapper.readTree(jsonString);
        
        // Check if the entity is present in 'data' node
        JsonNode dataNode = rootNode.path("data").path(entityName);
        if (!dataNode.isMissingNode()) {
            return dataNode;
        }

        // Check if the entity is present at the root level
        JsonNode rootLevelNode = rootNode.path(entityName);
        if (!rootLevelNode.isMissingNode()) {
            return rootLevelNode;
        }

        // Check if the entity is present in 'params' array
        JsonNode paramsNode = rootNode.path("params");
        if (paramsNode.isArray()) {
            for (JsonNode node : paramsNode) {
                if (node.path("paramType").asText().equals(entityName)) {
                    return node;
                }
            }
        }

        return null; // Return null if entity not found
    }

    public static void main(String[] args) {
        String json = """
{
  "data": {
    "customer": {
      "id": "cust_001",
      "name": "Alice Johnson",
      "email": "alice.johnson@example.com",
      "accounts": [
        {
          "accountId": "acc_001",
          "accountType": "savings",
          "balance": 1520.75,
          "currency": "USD"
        },
        {
          "accountId": "acc_002",
          "accountType": "checking",
          "balance": 430.00,
          "currency": "USD"
        }
      ]
    },
    "branch":{
      "name":"kerala",
      "email":"h@h.com"
    }
  },
  "application": {
    "name":"app1"
  },
  "params": [
    {
      "paramType": "ff",
      "paramValue": "iiii"
    },
    {
      "paramType": "fdf",
      "paramValue": "iidii"
    }
  ]
}
""";

        try {
            JsonNode customerNode = getEntityData(json, "customer");
            System.out.println("Customer Node: " + customerNode);

            JsonNode branchNode = getEntityData(json, "branch");
            System.out.println("Branch Node: " + branchNode);

            JsonNode applicationNode = getEntityData(json, "application");
            System.out.println("Application Node: " + applicationNode);

            JsonNode paramNode = getEntityData(json, "ff");
            System.out.println("Param Node: " + paramNode);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
