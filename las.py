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

def parse_data_sources(ast):
    """Extract data sources from the Query type."""
    data_sources = []
    entity_to_datasource = {}
    
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value == "Query":
            for field in definition.fields:
                field_name = field.name.value
                params = [arg.name.value for arg in field.arguments]
                return_type = extract_type_name(field.type)
                data_source = get_directive_value(field.directives, "datasource", "name")
                
                if data_source and return_type:
                    data_sources.append({
                        "DataSource": data_source,
                        "Name": data_source,
                        "RootQuery": f"{field_name}(${', '.join(params)})",
                        "Params": ', '.join(params)
                    })
                    entity_to_datasource[return_type] = data_source
    
    return data_sources, entity_to_datasource

def parse_entities(ast, entity_to_datasource):
    """Extract entities and assign them to their respective data sources."""
    entities = []
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value != "Query":
            entity_name = definition.name.value
            data_source = entity_to_datasource.get(entity_name, None)
            
            if data_source:
                entity_graphql = f"type {entity_name} {{\n"
                for field in definition.fields:
                    entity_graphql += f"  {field.name.value}: {extract_type_name(field.type)}\n"
                entity_graphql += "}"
                
                entities.append({"DataSource": data_source, "EntityName": entity_name, "GraphQL": entity_graphql})
    
    return entities

def parse_entity_attributes(ast, entity_to_datasource):
    """Extract attributes for each entity and assign to the respective data source."""
    entity_attributes = []
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value != "Query":
            entity_name = definition.name.value
            data_source = entity_to_datasource.get(entity_name, None)
            
            if data_source:
                for field in definition.fields:
                    attribute_name = field.name.value
                    attribute_type = extract_type_name(field.type)
                    parent_entity = entity_name  # Fix: EntityName should match actual type, not CAS
                    table_name = get_directive_value(field.directives, "table", "name")
                    
                    entity_attributes.append({
                        "DataSource": data_source,
                        "EntityName": parent_entity,
                        "AttributeName": attribute_name,
                        "ParentAttributeName": None,
                        "Source": "GraphQL",
                        "RateLimit": None,
                        "Table": table_name
                    })
    
    return entity_attributes

# Load GraphQL file
graphql_file_path = "schema.graphql"  # Change if necessary
with open(graphql_file_path, "r") as file:
    graphql_content = file.read().strip()

if not graphql_content:
    raise ValueError("GraphQL file is empty! Check the schema.graphql file.")

print("GraphQL file loaded successfully.")

# Parse GraphQL Schema
try:
    ast = parse(graphql_content)
except Exception as e:
    print("GraphQL Parsing Error:", e)
    raise

data_sources, entity_to_datasource = parse_data_sources(ast)
df_data_sources = pd.DataFrame(data_sources)

entities = parse_entities(ast, entity_to_datasource)
df_entities = pd.DataFrame(entities)

entity_attributes = parse_entity_attributes(ast, entity_to_datasource)
df_entity_attributes = pd.DataFrame(entity_attributes)

print("GraphQL schema parsed successfully.")
