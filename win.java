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

    public static void updateTypeDefinition(String field, String type) {
        if (isValidType(type)) {
            typeDefinition.put(field, type);
        } else {
            System.err.println("[ERROR] Attempted to add invalid type: " + type);
        }
    }

    public static boolean isConditionTrue(JsonNode rootNode, JsonNode conditionNode) {
        evaluatedPathCache.clear();
        return evaluateConditionFromJson(rootNode, conditionNode);
    }

    public static boolean evaluateConditionFromJson(JsonNode node, JsonNode conditionNode) {
        String operator = conditionNode.path("op").asText();
        JsonNode terms = conditionNode.path("terms");
        boolean isAndOperation = operator.equalsIgnoreCase("and");
        boolean result = isAndOperation;

        for (JsonNode term : terms) {
            boolean currentResult = false;

            if (term.has("op")) {  // Recursive case for nested conditions
                currentResult = evaluateConditionFromJson(node, term);
            } else {  // Base case for evaluating individual rules
                Rule rule = Rule.fromJson(term);
                if (rule == null || !rule.isValid()) {
                    System.err.println("[ERROR] Invalid or malformed rule detected: " + term);
                    continue;
                }

                JsonNode targetNode = findNestedNode(node, rule.getNamespace(), rule.getName());
                currentResult = rule.evaluate(targetNode);

                if (currentResult) {
                    System.out.println("[SUCCESS] Rule Matched: " + rule);
                } else {
                    System.err.println("[FAILURE] Rule Failed: " + rule);
                }
            }

            if (isAndOperation && !currentResult) return false;  // Short-circuit for AND
            if (!isAndOperation && currentResult) return true;  // Short-circuit for OR

            result = isAndOperation ? result && currentResult : result || currentResult;
        }

        return result;
    }

    private static JsonNode findNestedNode(JsonNode root, String namespace, String field) {
        String cacheKey = namespace + "." + field;
        if (evaluatedPathCache.containsKey(cacheKey)) return evaluatedPathCache.get(cacheKey);

        String[] namespaceParts = namespace.split("\\.");
        JsonNode currentNode = root;

        for (String part : namespaceParts) {
            currentNode = currentNode.path(part);
            if (currentNode.isMissingNode()) {
                System.err.println("[ERROR] Namespace part not found: " + part);
                return null;
            }
        }

        JsonNode finalNode = currentNode.path(field);
        evaluatedPathCache.put(cacheKey, finalNode);

        if (finalNode.isMissingNode()) {
            System.err.println("[ERROR] Field not found: " + field + " in namespace " + namespace);
        }

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
