import json
import pandas as pd
from sqlalchemy import create_engine
from graphql import parse

# Database Configuration (Change as needed)
DATABASE_URL = "postgresql://user:password@localhost:5432/mydatabase"
gine = create_engine(DATABASE_URL)

def parse_graphql_schema(graphql_content):
    """Parses GraphQL schema and extracts data sources, entities, attributes, and root queries."""
    ast = parse(graphql_content)
    data_sources = []
    entities = []
    entity_attributes = []
    
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
    
    return data_sources

# Load GraphQL file
graphql_file_path = "schema.graphql"  # Change if necessary
with open(graphql_file_path, "r") as file:
    graphql_content = file.read()

# Parse GraphQL Schema
data_sources = parse_graphql_schema(graphql_content)

# Convert to DataFrame
df_data_sources = pd.DataFrame(data_sources)

# Store Data in Database
df_data_sources.to_sql('SchemaDataSource', con=engine, if_exists='append', index=False)

print("GraphQL data sources parsed and stored successfully.")
