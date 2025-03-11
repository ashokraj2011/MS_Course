import json
import pandas as pd
from graphql import parse

def extract_type_name(field_type):
    """Recursively extract type name from GraphQL type structure."""
    if hasattr(field_type, "name"):
        return field_type.name.value
    elif hasattr(field_type, "type"):
        return extract_type_name(field_type.type)
    return "unknown"

def get_directive_value(directives, directive_name, arg_name):
    """Extracts the value of a specific directive argument."""
    for directive in directives:
        if directive.name.value == directive_name:
            for arg in directive.arguments:
                if arg.name.value == arg_name:
                    return arg.value.value
    return None

def traverse_entities(entity_name, data_source, ast, entity_to_datasource):
    """Recursively assign data sources to nested entities."""
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value == entity_name:
            for field in definition.fields:
                nested_entity = extract_type_name(field.type)
                if nested_entity and nested_entity not in entity_to_datasource:
                    entity_to_datasource[nested_entity] = data_source
                    traverse_entities(nested_entity, data_source, ast, entity_to_datasource)

def parse_graphql_schema(graphql_content):
    """Parses GraphQL schema and extracts data sources, entities, attributes, and root queries recursively."""
    try:
        ast = parse(graphql_content)
    except Exception as e:
        print("GraphQL Parsing Error:", e)
        raise
    
    data_sources = []
    entities = []
    entity_attributes = []
    entity_to_datasource = {}  # Store entity -> datasource mapping
    
    # Extract Data Sources from Query
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value == "Query":
            for field in definition.fields:
                field_name = field.name.value
                params = [arg.name.value for arg in field.arguments]
                return_type = extract_type_name(field.type)
                
                # Extract @datasource directive
                data_source = get_directive_value(field.directives, "datasource", "name")
                
                if data_source:
                    data_sources.append({
                        "DataSource": data_source,
                        "Name": data_source,
                        "RootQuery": f"{field_name}(${', '.join(params)})",
                        "Params": ', '.join(params)
                    })
                    
                    # Store the return type (entity) -> data source mapping
                    entity_to_datasource[return_type] = data_source
                    traverse_entities(return_type, data_source, ast, entity_to_datasource)  # Traverse nested entities
    
    # Extract entities and attributes recursively
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value != "Query":
            entity_name = definition.name.value
            data_source = entity_to_datasource.get(entity_name, None)
            
            # Only store entities that belong to known data sources
            if data_source:
                entity_graphql = f"type {entity_name} {{\n"
                for field in definition.fields:
                    attribute_name = field.name.value
                    attribute_type = extract_type_name(field.type)
                    table_name = get_directive_value(field.directives, "table", "name")  # Extract @table directive
                    
                    entity_attributes.append({
                        "DataSource": data_source,
                        "EntityName": entity_name,
                        "AttributeName": attribute_name,
                        "ParentAttributeName": None,
                        "Source": "GraphQL",
                        "RateLimit": None,
                        "Table": table_name
                    })
                    entity_graphql += f"  {attribute_name}: {attribute_type}\n"
                entity_graphql += "}"
                
                entities.append({"DataSource": data_source, "EntityName": entity_name, "GraphQL": entity_graphql})
    
    return data_sources, entities, entity_attributes

# Load GraphQL file
graphql_file_path = "schema.graphql"  # Change if necessary
with open(graphql_file_path, "r") as file:
    graphql_content = file.read().strip()

if not graphql_content:
    raise ValueError("GraphQL file is empty! Check the schema.graphql file.")

print("GraphQL file loaded successfully.")
print("GraphQL Content Preview:\n", graphql_content[:500])  # Print first 500 chars for debugging

# Parse GraphQL Schema
data_sources, entities, entity_attributes = parse_graphql_schema(graphql_content)

# Convert to DataFrames
df_data_sources = pd.DataFrame(data_sources)
df_entities = pd.DataFrame(entities)
df_entity_attributes = pd.DataFrame(entity_attributes)

print("GraphQL schema parsed successfully.")
