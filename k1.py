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
    if directives:
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
def parse_entities(ast, df_data_sources, entity_to_datasource):
    """Extract entities by iterating through data sources and scanning the GraphQL schema."""
    entities = []
    for _, row in df_data_sources.iterrows():
        data_source = row["DataSource"]
        for definition in ast.definitions:
            if definition.kind == "object_type_definition" and definition.name.value != "Query":
                entity_name = definition.name.value
                if entity_name in entity_to_datasource and entity_to_datasource[entity_name] == data_source:
                    entity_graphql = f"type {entity_name} {{\n"
                    for field in definition.fields:
                        entity_graphql += f"  {field.name.value}: {extract_type_name(field.type)}\n"
                    entity_graphql += "}"
                    entities.append({"DataSource": data_source, "EntityName": entity_name, "GraphQL": entity_graphql})
                else:
                    for field in definition.fields:
                        field_type = extract_type_name(field.type)
                        if field_type in entity_to_datasource and entity_to_datasource[field_type] == data_source:
                            entity_to_datasource[entity_name] = data_source
                            entity_graphql = f"type {entity_name} {{\n"
                            for field in definition.fields:
                                entity_graphql += f"  {field.name.value}: {extract_type_name(field.type)}\n"
                            entity_graphql += "}"
                            entities.append({"DataSource": data_source, "EntityName": entity_name, "GraphQL": entity_graphql})
                            break

    # Recursively find child entities
    child_entities = []
    for entity in entities:
        for definition in ast.definitions:
            if definition.kind == "object_type_definition" and definition.name.value == entity["EntityName"]:
                for field in definition.fields:
                    field_type = extract_type_name(field.type)
                    if field_type in entity_to_datasource and entity_to_datasource[field_type] == entity["DataSource"]:
                        child_entity_graphql = f"type {field_type} {{\n"
                        for child_field in next(d for d in ast.definitions if d.kind == "object_type_definition" and d.name.value == field_type).fields:
                            child_entity_graphql += f"  {child_field.name.value}: {extract_type_name(child_field.type)}\n"
                        child_entity_graphql += "}"
                        child_entities.append({"DataSource": entity["DataSource"], "EntityName": field_type, "GraphQL": child_entity_graphql})

    entities.extend(child_entities)
    return entities
def parse_entity_attributes(ast, df_entities):
    """Extract attributes by iterating through entities and scanning the GraphQL schema."""
    entity_attributes = []
    for _, row in df_entities.iterrows():
        data_source = row["DataSource"]
        entity_name = row["EntityName"]

        for definition in ast.definitions:
            if definition.kind == "object_type_definition" and definition.name.value == entity_name:
                for field in definition.fields:
                    attribute_name = field.name.value
                    attribute_type = extract_type_name(field.type)
                    parent_entity = entity_name
                    table_name = get_directive_value(field.directives if hasattr(field, 'directives') else None, "table", "name")

                    entity_attributes.append({
                        "DataSource": data_source,
                        "EntityName": parent_entity,
                        "AttributeName": attribute_name,
                        "ParentAttributeName": None,
                        "Source": "GraphQL",
                        "RateLimit": None,
                        "Table": table_name if table_name else "N/A"
                    })

    return entity_attributes

# Load GraphQL file
graphql_file_path = "schema.graphql"
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

entities = parse_entities(ast, df_data_sources, entity_to_datasource)
df_entities = pd.DataFrame(entities)

entity_attributes = parse_entity_attributes(ast, df_entities)
df_entity_attributes = pd.DataFrame(entity_attributes)

print("GraphQL schema parsed successfully.")
print(df_entities)
print(df_entity_attributes)
