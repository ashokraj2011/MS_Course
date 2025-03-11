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

def parse_graphql_schema(graphql_content):
    """Parses GraphQL schema and extracts data sources, entities, attributes, and root queries recursively."""
    ast = parse(graphql_content)
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
                
                data_source = None
                for directive in field.directives:
                    if directive.name.value == "datasource":
                        for arg in directive.arguments:
                            if arg.name.value == "name":
                                data_source = arg.value.value
                                
                if data_source:
                    data_sources.append({
                        "DataSource": data_source,
                        "Name": data_source,
                        "RootQuery": f"{field_name}(${', '.join(params)})",
                        "Params": ', '.join(params)
                    })
                    
                    # Store the return type (entity) -> data source mapping
                    entity_name = extract_type_name(field.type)
                    entity_to_datasource[entity_name] = data_source
    
    # Extract entities and attributes recursively
    for definition in ast.definitions:
        if definition.kind == "object_type_definition" and definition.name.value != "Query":
            entity_name = definition.name.value
            data_source = entity_to_datasource.get(entity_name, None)
            entity_graphql = f"type {entity_name} {{\n"
            
            for field in definition.fields:
                attribute_name = field.name.value
                attribute_type = extract_type_name(field.type)
                
                entity_attributes.append({
                    "DataSource": data_source,
                    "EntityName": entity_name,
                    "AttributeName": attribute_name,
                    "ParentAttributeName": None,
                    "Source": "GraphQL",
                    "RateLimit": None
                })
                entity_graphql += f"  {attribute_name}: {attribute_type}\n"
            
            entity_graphql += "}"
            
            if data_source:
                entities.append({"DataSource": data_source, "EntityName": entity_name, "GraphQL": entity_graphql})
    
    return data_sources, entities, entity_attributes

# Load GraphQL file
graphql_file_path = "schema.graphql"  # Change if necessary
with open(graphql_file_path, "r") as file:
    graphql_content = file.read()

# Parse GraphQL Schema
data_sources, entities, entity_attributes = parse_graphql_schema(graphql_content)

# Convert to DataFrames
df_data_sources = pd.DataFrame(data_sources)
df_entities = pd.DataFrame(entities)
df_entity_attributes = pd.DataFrame(entity_attributes)

print("GraphQL schema parsed successfully.")
