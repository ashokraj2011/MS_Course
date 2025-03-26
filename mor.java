import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class JsonRuleEngine {
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final Map<String, String> typeDefinition = new ConcurrentHashMap<>(); // Improved thread-safety
    private static final Map<String, JsonNode> evaluatedPathCache = new HashMap<>(); // Cache for evaluated paths

    public static void loadTypeDefinitionsFromFile(String filePath) {
        try (BufferedReader reader = Files.newBufferedReader(Path.of(filePath))) { // Improved file reading
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(":");
                if (parts.length == 2) {
                    typeDefinition.put(parts[0].trim(), parts[1].trim());
                }
            }
            System.out.println("[INFO] Type definitions loaded successfully from " + filePath);
        } catch (IOException e) {
            System.err.println("[ERROR] Failed to load type definitions: " + e.getMessage());
        }
    }

    public static void updateTypeDefinition(String field, String type) {
        typeDefinition.put(field, type);
    }

    public static boolean isConditionTrue(JsonNode rootNode, JsonNode conditionNode) {
        evaluatedPathCache.clear(); // Clear cache before each evaluation
        return evaluateConditionFromJson(rootNode, conditionNode);
    }

    public static boolean evaluateConditionFromJson(JsonNode node, JsonNode conditionNode) {
        String operator = conditionNode.path("op").asText();
        JsonNode terms = conditionNode.path("terms");
        boolean result = operator.equalsIgnoreCase("and"); // Proper initialization for AND logic

        for (JsonNode term : terms) {
            boolean currentResult;

            if (term.has("op")) {
                currentResult = evaluateConditionFromJson(node, term);
            } else {
                Rule rule = Rule.fromJson(term);
                if (rule == null || !rule.isValid()) continue;

                JsonNode targetNode = findNestedNode(node, rule.getNamespace(), rule.getName());
                currentResult = rule.evaluate(targetNode);
            }

            if (operator.equalsIgnoreCase("and") && !currentResult) {
                return false; // Short-circuit for AND logic
            }

            if (operator.equalsIgnoreCase("or") && currentResult) {
                return true; // Short-circuit for OR logic
            }

            if (operator.equalsIgnoreCase("and")) {
                result = result && currentResult;
            } else if (operator.equalsIgnoreCase("or")) {
                result = result || currentResult;
            }
        }
        return result;
    }

    private static JsonNode findNestedNode(JsonNode root, String namespace, String field) {
        String cacheKey = namespace + "." + field;
        if (evaluatedPathCache.containsKey(cacheKey)) return evaluatedPathCache.get(cacheKey); // Retrieve from cache if present

        String[] namespaceParts = namespace.split("\\.");
        JsonNode currentNode = root;

        for (String part : namespaceParts) {
            currentNode = currentNode.path(part);
            if (currentNode.isMissingNode()) return null;
        }

        JsonNode finalNode = currentNode.path(field);
        evaluatedPathCache.put(cacheKey, finalNode); // Cache the evaluated path
        return finalNode;
    }

    public static void main(String[] args) {
        try {
            loadTypeDefinitionsFromFile("type_definitions.txt");
            JsonNode rootNode = objectMapper.readTree(new File("customer_data.json"));
            JsonNode conditionNode = objectMapper.readTree(new File("condition.json"));

            System.out.println("\n[INFO] Starting Evaluation...");
            boolean result = isConditionTrue(rootNode, conditionNode);
            System.out.println("\n[INFO] Final Condition Evaluation Result: " + result);
        } catch (IOException e) {
            System.err.println("[ERROR] An error occurred during processing: " + e.getMessage());
        }
    }
}
