import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.function.Predicate;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.Scanner;

public class GenericJsonUtility {
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final Map<String, String> typeDefinition = new HashMap<>();

    public static void loadTypeDefinitionsFromFile(String filePath) {
        try {
            List<String> lines = Files.readAllLines(new File(filePath).toPath());
            for (String line : lines) {
                String[] parts = line.split(":");
                if (parts.length == 2) {
                    typeDefinition.put(parts[0].trim(), parts[1].trim());
                }
            }
            System.out.println("Type definitions loaded successfully.");
        } catch (IOException e) {
            System.err.println("Failed to load type definitions: " + e.getMessage());
        }
    }

    public static void updateTypeDefinition(String field, String type) {
        typeDefinition.put(field, type);
    }

    public static boolean evaluateConditionFromJson(JsonNode node, JsonNode conditionNode) {
        String operator = conditionNode.path("op").asText();
        JsonNode terms = conditionNode.path("terms");

        // Group conditions by evaluation_group
        Map<String, List<JsonNode>> groupedConditions = new HashMap<>();

        for (JsonNode term : terms) {
            if (term.has("op")) { // Nested condition
                boolean nestedResult = evaluateConditionFromJson(node, term);
                if (operator.equalsIgnoreCase("and") && !nestedResult) return false;
                if (operator.equalsIgnoreCase("or") && nestedResult) return true;
            } else {
                String group = term.path("field").path("evaluation_group").asText();
                groupedConditions.putIfAbsent(group, new ArrayList<>());
                groupedConditions.get(group).add(term);
            }
        }

        // Evaluate each group independently
        boolean result = operator.equalsIgnoreCase("and");
        for (Map.Entry<String, List<JsonNode>> entry : groupedConditions.entrySet()) {
            boolean groupResult = evaluateGroup(node, entry.getValue());

            if (operator.equalsIgnoreCase("and") && !groupResult) return false;
            if (operator.equalsIgnoreCase("or") && groupResult) return true;
        }

        return result;
    }

    private static boolean evaluateGroup(JsonNode node, List<JsonNode> groupConditions) {
        for (JsonNode condition : groupConditions) {
            if (!evaluateSimpleConditionFromJson(node, condition)) {
                return false; // All conditions in a group must be true
            }
        }
        return true; // All conditions in the group were true
    }

    private static boolean evaluateSimpleConditionFromJson(JsonNode node, JsonNode term) {
        try {
            String namespace = term.path("field").path("namespace").asText();
            String field = term.path("field").path("name").asText();
            String fullFieldPath = namespace + "." + field;
            String comparison = term.path("comp").asText().toLowerCase();
            String value = term.path("value").asText().trim();

            JsonNode targetNode = findNestedNode(node, namespace, field);

            if (targetNode == null) return false;

            if (comparison.equals("equal to")) {
                return targetNode.asText().equals(value);
            } else if (comparison.equals("greater than")) {
                return targetNode.asDouble() > Double.parseDouble(value);
            } else if (comparison.equals("less than")) {
                return targetNode.asDouble() < Double.parseDouble(value);
            } else if (comparison.equals("not equal to")) {
                return !targetNode.asText().equals(value);
            } else if (comparison.equals("greater than or equal to")) {
                return targetNode.asDouble() >= Double.parseDouble(value);
            } else if (comparison.equals("less than or equal to")) {
                return targetNode.asDouble() <= Double.parseDouble(value);
            } else if (comparison.equals("contains")) {
                return targetNode.asText().contains(value);
            } else if (comparison.equals("date after")) {
                LocalDate nodeDate = LocalDate.parse(targetNode.asText());
                LocalDate compareDate = parseDateCondition(value);
                return nodeDate.isAfter(compareDate);
            } else if (comparison.equals("date before")) {
                LocalDate nodeDate = LocalDate.parse(targetNode.asText());
                LocalDate compareDate = parseDateCondition(value);
                return nodeDate.isBefore(compareDate);
            }
        } catch (Exception e) {
            return false;
        }
        return false;
    }

    private static JsonNode findNestedNode(JsonNode root, String namespace, String field) {
        String[] namespaceParts = namespace.split("\\.");
        JsonNode currentNode = root;

        for (String part : namespaceParts) {
            currentNode = currentNode.path(part);
            if (currentNode.isMissingNode()) return null;
        }

        return currentNode.path(field);
    }

    public static LocalDate parseDateCondition(String condition) {
        if (condition.contains("CURRENT DATE")) {
            String[] parts = condition.split("-");
            int daysAgo = Integer.parseInt(parts[1].trim().split(" ")[0]);
            return LocalDate.now().minusDays(daysAgo);
        }
        return LocalDate.parse(condition, DateTimeFormatter.ISO_LOCAL_DATE);
    }

    public static boolean isConditionTrue(JsonNode rootNode, JsonNode conditionNode) {
        return evaluateConditionFromJson(rootNode, conditionNode);
    }

    public static void main(String[] args) {
        try {
            Scanner scanner = new Scanner(System.in);

            System.out.print("Enter JSON Data File Path: ");
            String jsonDataPath = scanner.nextLine();

            System.out.print("Enter Condition File Path: ");
            String conditionPath = scanner.nextLine();

            String jsonString = new String(Files.readAllBytes(new File(jsonDataPath).toPath()));
            JsonNode rootNode = objectMapper.readTree(jsonString);

            String conditionString = new String(Files.readAllBytes(new File(conditionPath).toPath()));
            JsonNode conditionNode = objectMapper.readTree(conditionString);

            boolean result = isConditionTrue(rootNode, conditionNode);

            System.out.println("Condition Evaluation Result: " + result);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
