from mcp.server.fastmcp import FastMCP, Context
import httpx

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

# Global async client for all GraphQL requests (persistent connections & HTTP/2)
@dataclass
class AppContext:
    graphql_client: httpx.AsyncClient

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    graphql_client = httpx.AsyncClient(http2=True, timeout=10.0)
    try:
        yield AppContext(graphql_client=graphql_client)
    finally:
        await graphql_client.aclose()

# Initialize MCP server with lifespan
mcp = FastMCP("Raphtory MCP", lifespan=app_lifespan)

# Define a tool to execute GraphQL queries
@mcp.tool()
async def query_db(ctx: Context, query: str, endpoint: str = "http://localhost:1736/", variables: dict = None) -> str:

    ctx.info("query_db: %s" % query)
    """reuse the graphqlclient """
    graphql_client: httpx.AsyncClient = ctx.request_context.lifespan_context.graphql_client
    # Form a cache key if attempting to cache responses (could include user, tool, query, and variables)
    # Prepare headers (e.g., authorization) for the request
    headers = {"Content-Type": "application/json"}
    # if auth_token: # get this from an env variable
    #     headers["Authorization"] = f"Bearer {auth_token}"
    try:
        # Send GraphQL query (HTTP POST)
        response = await graphql_client.post(endpoint, json={"query": query, "variables": variables or {}}, headers=headers)
        data = response.json()
        # optionally add returned data to a cache
        # Optionally handle errors: check response.status_code and data for GraphQL errors
        return data
    except Exception as e:
        return f"Error: {str(e)}"

# Define a resource to provide the GraphQL schema for the complete database
@mcp.resource("schema://database")
async def get_schema() -> str:
    """Provide the GraphQL schema as a resource"""
    query = """
    {
      __schema {
        types {
          name
          fields(includeDeprecated: false) {
            name
            description
            args {
              name 
              defaultValue
            }
          }
        }
      }
    }
    """
    result = await query_db(mcp.get_context(), query)
    return result

# check if a graph exists
@mcp.resource("schema://graph_exists/{graph_name}")
async def check_graph_exists(graph_name: str) -> bool:

    """check for the existance for a specific graph"""
    # First verify the graph exists by querying its nodes
    verify_query = """
    {
      graph(path: "%s") {
        nodes {
          list {
            name
          }
        }
      }
    }""" % graph_name

    result = await query_db(mcp.get_context(), verify_query)
    
    # Check if graph exists by looking for errors in response
    if "errors" in result:
        return False
    return True


# get the schema for a specific graph
@mcp.resource("schema://{graph_name}/{include_variants}")
async def get_graph_schema(graph_name: str, include_variants: bool = False) -> str:
    # Check if graph exists first
    exists = await check_graph_exists(graph_name)
    if not exists:
        return {"errors": [{"message": f"Graph {graph_name} does not exist"}]}

    # Query both node and edge schemas
    schema_query = """
    {
      graph(path: "%s") {
        schema {
          nodes {
            properties {
              key
              propertyType
              %s
            }
          }
        }
        edgeTypes: edges {
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
    }""" % (graph_name, 
            "variants" if include_variants == "true" else "")

    schema_result = await query_db(mcp.get_context(), schema_query)
    
    # Check if we have a valid result before processing
    if isinstance(schema_result, dict) and "data" in schema_result and schema_result["data"]:
        graph_data = schema_result["data"].get("graph", {})
        if graph_data and "edgeTypes" in graph_data:
            edges = graph_data["edgeTypes"].get("list", [])
            # Extract unique relationship types
            unique_relationships = set()
            for edge in edges:
                if "properties" in edge and "values" in edge["properties"]:
                    for value in edge["properties"]["values"]:
                        if "value" in value:
                            unique_relationships.add(value["value"])
            
            # Create a new schema structure with unique relationships
            graph_data["relationships"] = sorted(list(unique_relationships))
            # Remove the full edge list to keep response clean
            del graph_data["edgeTypes"]
    
    return schema_result


@mcp.prompt()
def raphtory_prompt(message: str) -> str:
    """Create a prompt that helps the LLM understand and use the GraphQL schema and query_db tool"""
    return """You are an expert at writing GraphQL queries. You have access to a GraphQL database through the query_db tool.
    
Before writing any queries, you should examine the schema using the schema://main resource to understand the available types, fields and arguments.

When a user asks a question, you should:
1. First check if you need specific graph schema details by using the schema://graph/{graphName} resource to understand:
   - Available node types and their properties (including property variants if needed)
   - Edge types and their properties
   - Relationships between nodes
2. Analyze the overall database schema using schema://main to identify other relevant types and fields
3. Construct an appropriate GraphQL query using proper syntax
4. Use the query_db tool to execute the query
5. Format and explain the results in a helpful way

The user's request is: {message}

Please write a valid GraphQL query to answer their question.""".format(message=message)