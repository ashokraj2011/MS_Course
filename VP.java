import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.jayway.jsonpath.JsonPath;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class JsonRuleEngine {
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final Map<String, String> typeDefinition = new ConcurrentHashMap<>();
    private static final Map<String, JsonNode> evaluatedPathCache = new HashMap<>();

    public static void loadTypeDefinitionsFromFile(String filePath) {
        try (BufferedReader reader = Files.newBufferedReader(Path.of(filePath))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(":");
                if (parts.length == 2) {
                    String field = parts[0].trim();
                    String type = parts[1].trim();
                    if (isValidType(type)) {
                        typeDefinition.put(field, type);
                    } else {
                        System.err.println("[ERROR] Invalid type definition for: " + field);
                    }
                }
            }
            System.out.println("[INFO] Type definitions loaded successfully from " + filePath);
        } catch (IOException e) {
            System.err.println("[ERROR] Failed to load type definitions: " + e.getMessage());
        }
    }

    private static boolean isValidType(String type) {
        return type.equals("Integer") || type.equals("Double") || type.equals("String") || type.equals("DateTime") || type.endsWith("[]");
    }

    public static ObjectNode transformJson(JsonNode dataNode, JsonNode definitionNode) {
        ObjectNode sessionNode = JsonNodeFactory.instance.objectNode();

        for (JsonNode registeredAttribute : definitionNode.path("registeredAttributes")) {
            String namespace = registeredAttribute.path("namespace").asText();
            ObjectNode namespaceNode = JsonNodeFactory.instance.objectNode();

            for (JsonNode attribute : registeredAttribute.path("attributeList")) {
                String attributeName = attribute.path("attributeName").asText();
                String jsonPath = attribute.path("jsonPath").asText();

                try {
                    Object extractedValue = JsonPath.read(dataNode.toString(), jsonPath);
                    if (extractedValue != null) {
                        namespaceNode.putPOJO(attributeName, extractedValue);
                    }
                } catch (Exception e) {
                    System.err.println("[ERROR] Failed to extract data for " + attributeName + " using path " + jsonPath);
                }
            }

            for (JsonNode propertyGroup : registeredAttribute.path("propertygroups")) {
                String groupName = propertyGroup.path("name").asText();
                String groupJsonPath = propertyGroup.path("jsonPath").asText();

                try {
                    Object extractedGroup = JsonPath.read(dataNode.toString(), groupJsonPath);
                    if (extractedGroup != null) {
                        namespaceNode.putPOJO(groupName, extractedGroup);
                    }
                } catch (Exception e) {
                    System.err.println("[ERROR] Failed to extract data for group " + groupName + " using path " + groupJsonPath);
                }
            }

            sessionNode.set(namespace, namespaceNode);
        }
        return sessionNode;
    }

    public static ObjectNode mergeJson(ObjectNode originalData, ObjectNode transformedData) {
        originalData.setAll(transformedData);
        return originalData;
    }

    public static void main(String[] args) {
        try {
            JsonNode dataNode = objectMapper.readTree(new File("data.json"));
            JsonNode definitionNode1 = objectMapper.readTree(new File("definition1.json")); // Without transformation
            JsonNode definitionNode2 = objectMapper.readTree(new File("definition2.json")); // Requires transformation
            JsonNode conditionNode = objectMapper.readTree(new File("condition.json"));

            ObjectNode originalData = (ObjectNode) dataNode;
            ObjectNode transformedData = transformJson(dataNode, definitionNode2);
            ObjectNode mergedData = mergeJson(originalData, transformedData);

            System.out.println("\n[INFO] Merged Data:\n" + objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(mergedData));

            boolean evaluationResult = isConditionTrue(mergedData, conditionNode);
            System.out.println("\n[INFO] Final Condition Evaluation Result: " + evaluationResult);

        } catch (IOException e) {
            System.err.println("[ERROR] An error occurred during processing: " + e.getMessage());
        }
    }
}
