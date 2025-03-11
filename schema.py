import json
import pandas as pd
from sqlalchemy import create_engine
from graphql import parse

# Database Configuration (Change as needed)
DATABASE_URL = "postgresql://user:password@localhost:5432/mydatabase"
gine = create_engine(DATABASE_URL)

def parse_graphql_schema(graphql_content):
    """Parses GraphQL schema and extracts entities, attributes, and data sources."""
    ast = parse(graphql_content)
    data_sources = []
    entities = []
    entity_attributes = []
    
    current_datasource = None
    
    for definition in ast.definitions:
        if definition.kind == "object_type_definition":
            entity_name = definition.name.value
            
            # Extract @datasource and @table directives
            for directive in definition.directives:
                if directive.name.value == "datasource":
                    for arg in directive.arguments:
                        if arg.name.value == "name":
                            current_datasource = arg.value.value
                            data_sources.append({"DataSource": current_datasource})
                
            # Add entity to SchemaEntity
            if current_datasource:
                entities.append({"DataSource": current_datasource, "EntityName": entity_name})
            
            # Extract entity attributes
            for field in definition.fields:
                attribute_name = field.name.value
                entity_attributes.append({
                    "DataSource": current_datasource,
                    "EntityName": entity_name,
                    "AttributeName": attribute_name,
                    "ParentAttributeName": None,
                    "Source": "GraphQL",
                    "RateLimit": None
                })
    
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

# Store Data in Database
df_data_sources.to_sql('SchemaDataSource', con=engine, if_exists='append', index=False)
df_entities.to_sql('SchemaEntity', con=engine, if_exists='append', index=False)
df_entity_attributes.to_sql('SchemaEntityAttributes', con=engine, if_exists='append', index=False)

print("GraphQL schema parsed and stored successfully using GraphQL parsing.")
