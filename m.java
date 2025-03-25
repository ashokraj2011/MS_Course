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

        boolean result = operator.equalsIgnoreCase("and");

        for (JsonNode term : terms) {
            if (term.has("op")) {
                boolean nestedResult = evaluateConditionFromJson(node, term);
                if (operator.equalsIgnoreCase("and") && !nestedResult) return false;
                if (operator.equalsIgnoreCase("or") && nestedResult) return true;
            } else {
                boolean simpleResult = evaluateSimpleConditionFromJson(node, term);
                if (operator.equalsIgnoreCase("and") && !simpleResult) return false;
                if (operator.equalsIgnoreCase("or") && simpleResult) return true;
            }
        }
        return result;
    }

    private static boolean evaluateSimpleConditionFromJson(JsonNode node, JsonNode term) {
        try {
            String namespace = term.path("field").path("namespace").asText();
            String field = term.path("field").path("name").asText();
            String fullFieldPath = namespace + "." + field;
            String comparison = term.path("comp").asText().toLowerCase();
            String value = term.path("value").asText().trim();

            if (comparison.equals("equal to")) {
                return node.path(fullFieldPath).asText().equals(value);
            } else if (comparison.equals("greater than")) {
                return node.path(fullFieldPath).asDouble() > Double.parseDouble(value);
            } else if (comparison.equals("less than")) {
                return node.path(fullFieldPath).asDouble() < Double.parseDouble(value);
            } else if (comparison.equals("not equal to")) {
                return !node.path(fullFieldPath).asText().equals(value);
            } else if (comparison.equals("greater than or equal to")) {
                return node.path(fullFieldPath).asDouble() >= Double.parseDouble(value);
            } else if (comparison.equals("less than or equal to")) {
                return node.path(fullFieldPath).asDouble() <= Double.parseDouble(value);
            } else if (comparison.equals("contains")) {
                return node.path(fullFieldPath).asText().contains(value);
            } else if (comparison.equals("date after")) {
                LocalDate nodeDate = LocalDate.parse(node.path(fullFieldPath).asText());
                LocalDate compareDate = parseDateCondition(value);
                return nodeDate.isAfter(compareDate);
            } else if (comparison.equals("date before")) {
                LocalDate nodeDate = LocalDate.parse(node.path(fullFieldPath).asText());
                LocalDate compareDate = parseDateCondition(value);
                return nodeDate.isBefore(compareDate);
            }
        } catch (Exception e) {
            return false;
        }
        return false;
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

            // Load JSON Data
            String jsonString = new String(Files.readAllBytes(new File(jsonDataPath).toPath()));
            JsonNode rootNode = objectMapper.readTree(jsonString);

            // Load Condition JSON
            String conditionString = new String(Files.readAllBytes(new File(conditionPath).toPath()));
            JsonNode conditionNode = objectMapper.readTree(conditionString);

            // Test condition
            boolean result = isConditionTrue(rootNode, conditionNode);

            System.out.println("Condition Evaluation Result: " + result);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
