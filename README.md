# Raphtory GraphQL Schema Explorer

This Python module provides a FastMCP server that exposes GraphQL schema information for Raphtory graphs through a set of HTTP resources. It allows LLMs to explore and understand the structure of graphs, including node properties and relationship types.

## Features

### 1. Graph Schema Querying
- Query the schema of specific graphs by name
- Retrieve detailed property information for nodes
- Get unique relationship types and their metadata
- Optional inclusion of property variants

### 2. Resources

#### `schema://database`
Returns the complete GraphQL schema for the database, including:
- All available types
- Fields for each type
- Field descriptions
- Arguments and their default values

#### `schema://graph_exists/{graph_name}`
Verifies if a specific graph exists in the database by checking for the presence of nodes.

#### `schema://{graph_name}/{include_variants}`
Returns detailed schema information for a specific graph:
- Node Properties:
  - Property keys
  - Property types (e.g., "Str")
  - Optional property variants
- Relationships:
  - Unique relationship types (e.g., "edge_type_1", "edge_type_2", "edge_type_3")

### 3. Implementation Details

The module uses:
- An executing Raphtory GraphQL server (this needs to be running)
- `httpx` for async HTTP requests with HTTP/2 support
- FastMCP for resource management
- Persistent connections through a global async client
- Context management for proper resource cleanup

## Example Usage

Query a graph schema:
```graphql
{
  graph(path: "your_graph_name") {
    schema {
      nodes {
        properties {
          key
          propertyType
        }
      }
    }
    edges {
      list {
        properties {
          keys
          values {
            value
          }
        }
      }
    }
  }
}
```

## Response Format

The schema response includes values like:

```json
{
  "data": {
    "graph": {
      "schema": {
        "nodes": [{
          "properties": [
            {"key": "name", "propertyType": "Str"},
            {"key": "type", "propertyType": "Str"}
            // ... other properties
          ]
        }]
      },
      "relationships": [
        "edge_type_1",
        "edge_type_2",
        "edge_type_3"
      ]
    }
  }
}
```

## Error Handling

The module includes error handling for:
- Non-existent graphs
- Invalid queries
- Connection issues
- Malformed responses

## Dependencies

- FastMCP
- httpx
- Python 3.x
- a running Raphtory GraphQL endpoint (default: http://localhost:1736/)

## Configuration

The module uses default configuration:
- HTTP/2 enabled
- 10-second timeout
- Content-Type: application/json

Additional configuration (like authentication) can be added through environment variables.