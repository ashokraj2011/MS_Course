import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.io.File;
import java.io.IOException;

public class JsonRuleEngineTest {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    public void testTransformJson() throws IOException {
        JsonNode dataNode = objectMapper.readTree(new File("data.json"));
        JsonNode definitionNode = objectMapper.readTree(new File("definition2.json"));

        ObjectNode transformedData = JsonRuleEngine.transformJson(dataNode, definitionNode);

        assertNotNull(transformedData);
        assertTrue(transformedData.has("portsum"));
        assertTrue(transformedData.has("commonIdentifiers"));
    }

    @Test
    public void testMergeJson() throws IOException {
        JsonNode dataNode = objectMapper.readTree(new File("data.json"));
        JsonNode definitionNode = objectMapper.readTree(new File("definition2.json"));

        ObjectNode originalData = (ObjectNode) dataNode;
        ObjectNode transformedData = JsonRuleEngine.transformJson(dataNode, definitionNode);

        ObjectNode mergedData = JsonRuleEngine.mergeJson(originalData, transformedData);

        assertNotNull(mergedData);
        assertTrue(mergedData.has("application"));
        assertTrue(mergedData.has("session"));
    }

    @Test
    public void testConditionEvaluation() throws IOException {
        JsonNode dataNode = objectMapper.readTree(new File("data.json"));
        JsonNode definitionNode = objectMapper.readTree(new File("definition2.json"));
        JsonNode conditionNode = objectMapper.readTree(new File("condition.json"));

        ObjectNode transformedData = JsonRuleEngine.transformJson(dataNode, definitionNode);
        ObjectNode mergedData = JsonRuleEngine.mergeJson((ObjectNode) dataNode, transformedData);

        boolean evaluationResult = JsonRuleEngine.isConditionTrue(mergedData, conditionNode);

        assertTrue(evaluationResult, "Condition evaluation failed");
    }
}
