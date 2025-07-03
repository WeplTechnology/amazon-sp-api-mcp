"""
Main MCP server for Amazon SP-API.
"""

import asyncio
import sys
from typing import Any, Dict, List
import logging

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LogLevel
)
from pydantic import AnyUrl

from .config import load_config, SPAPIConfig
from .client.http_client import SPAPIClient
from .tools.auth_tools import AuthTools
from .tools.orders_tools import OrdersTools
from .tools.inventory_tools import InventoryTools
from .tools.reports_tools import ReportsTools
from .tools.catalog_tools import CatalogTools
from .tools.listings_tools import ListingsTools
from .tools.feeds_tools import FeedsTools
from .tools.financial_tools import FinancialTools

# Setup logging
logger = logging.getLogger(__name__)

class AmazonSPAPIMCPServer:
    """Amazon SP-API MCP Server."""
    
    def __init__(self):
        self.server = Server("amazon-sp-api-mcp")
        self.config: SPAPIConfig = None
        self.client: SPAPIClient = None
        self.tools = {}
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            tools = [
                # Authentication Tools
                Tool(
                    name="validate_credentials",
                    description="Validate all SP-API credentials and configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="refresh_access_token",
                    description="Manually refresh the LWA access token",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_marketplace_participation",
                    description="Get marketplace participation information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                
                # Orders Tools
                Tool(
                    name="get_orders",
                    description="Get orders with filtering options",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            },
                            "created_after": {
                                "type": "string",
                                "description": "ISO 8601 date string (e.g., 2024-01-01T00:00:00Z)"
                            },
                            "created_before": {
                                "type": "string",
                                "description": "ISO 8601 date string"
                            },
                            "order_statuses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by order statuses (Unshipped, PartiallyShipped, Shipped, etc.)"
                            },
                            "fulfillment_channels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by fulfillment channels (FBA, FBM)"
                            },
                            "max_results_per_page": {
                                "type": "integer",
                                "default": 100,
                                "maximum": 100,
                                "description": "Maximum results per page"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_order_details",
                    description="Get detailed information for a specific order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Amazon Order ID"
                            }
                        },
                        "required": ["order_id"]
                    }
                ),
                Tool(
                    name="get_order_items",
                    description="Get line items for a specific order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Amazon Order ID"
                            }
                        },
                        "required": ["order_id"]
                    }
                ),
                Tool(
                    name="update_shipment_status",
                    description="Update shipment status for an order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "order_id": {
                                "type": "string",
                                "description": "Amazon Order ID"
                            },
                            "shipment_date": {
                                "type": "string",
                                "description": "ISO 8601 date string"
                            },
                            "carrier_name": {
                                "type": "string",
                                "description": "Carrier name"
                            },
                            "carrier_code": {
                                "type": "string",
                                "description": "Carrier code (optional)"
                            },
                            "tracking_number": {
                                "type": "string",
                                "description": "Tracking number (optional)"
                            }
                        },
                        "required": ["order_id", "shipment_date", "carrier_name"]
                    }
                ),
                
                # Inventory Tools
                Tool(
                    name="get_inventory_summaries",
                    description="Get FBA inventory summaries",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            },
                            "seller_skus": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by specific SKUs"
                            },
                            "details": {
                                "type": "boolean",
                                "default": True,
                                "description": "Include detailed inventory breakdown"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_inventory_details",
                    description="Get detailed inventory information for a specific SKU",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "seller_sku": {
                                "type": "string",
                                "description": "Seller SKU"
                            },
                            "marketplace_id": {
                                "type": "string",
                                "description": "Marketplace ID (optional)"
                            }
                        },
                        "required": ["seller_sku"]
                    }
                ),
                Tool(
                    name="get_restock_inventory",
                    description="Get restock recommendations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_stranded_inventory",
                    description="Get stranded inventory information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": []
                    }
                ),
                
                # Reports Tools
                Tool(
                    name="request_report",
                    description="Request a report to be generated",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "report_type": {
                                "type": "string",
                                "description": "Type of report to generate"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time for report data (ISO 8601)"
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time for report data (ISO 8601)"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": ["report_type"]
                    }
                ),
                Tool(
                    name="get_report_status",
                    description="Get the processing status of a report",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "report_id": {
                                "type": "string",
                                "description": "Report ID"
                            }
                        },
                        "required": ["report_id"]
                    }
                ),
                Tool(
                    name="download_report",
                    description="Download and parse a completed report",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "report_document_id": {
                                "type": "string",
                                "description": "Report document ID"
                            },
                            "parse_content": {
                                "type": "boolean",
                                "default": True,
                                "description": "Parse report content"
                            }
                        },
                        "required": ["report_document_id"]
                    }
                ),
                Tool(
                    name="get_report_schedules",
                    description="Get scheduled reports",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "report_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by report types"
                            }
                        },
                        "required": []
                    }
                ),
                
                # Catalog Tools
                Tool(
                    name="search_catalog_items",
                    description="Search for catalog items",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "string",
                                "description": "Search keywords"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            },
                            "brand_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by brand names"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_catalog_item",
                    description="Get detailed information about a specific catalog item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "asin": {
                                "type": "string",
                                "description": "Product ASIN"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": ["asin"]
                    }
                ),
                Tool(
                    name="get_catalog_item_variations",
                    description="Get variations of a parent catalog item",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "asin": {
                                "type": "string",
                                "description": "Parent ASIN"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": ["asin"]
                    }
                ),
                
                # Listings Tools
                Tool(
                    name="get_listings_item",
                    description="Get details of a specific listing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "seller_id": {
                                "type": "string",
                                "description": "Seller ID"
                            },
                            "sku": {
                                "type": "string",
                                "description": "Seller SKU"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": ["seller_id", "sku"]
                    }
                ),
                Tool(
                    name="patch_listings_item",
                    description="Update a listing using JSON Patch operations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "seller_id": {
                                "type": "string",
                                "description": "Seller ID"
                            },
                            "sku": {
                                "type": "string",
                                "description": "Seller SKU"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            },
                            "patches": {
                                "type": "array",
                                "description": "JSON Patch operations"
                            }
                        },
                        "required": ["seller_id", "sku", "marketplace_ids", "patches"]
                    }
                ),
                Tool(
                    name="get_listings_restrictions",
                    description="Get listing restrictions for a product",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "asin": {
                                "type": "string",
                                "description": "Product ASIN"
                            },
                            "seller_id": {
                                "type": "string",
                                "description": "Seller ID"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            }
                        },
                        "required": ["asin", "seller_id", "marketplace_ids"]
                    }
                ),
                
                # Feeds Tools
                Tool(
                    name="create_feed",
                    description="Create a feed for bulk data operations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_type": {
                                "type": "string",
                                "description": "Type of feed"
                            },
                            "marketplace_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of marketplace IDs"
                            },
                            "input_feed_document_id": {
                                "type": "string",
                                "description": "Feed document ID"
                            }
                        },
                        "required": ["feed_type", "marketplace_ids", "input_feed_document_id"]
                    }
                ),
                Tool(
                    name="get_feed_status",
                    description="Get the processing status of a feed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {
                                "type": "string",
                                "description": "Feed ID"
                            }
                        },
                        "required": ["feed_id"]
                    }
                ),
                Tool(
                    name="get_feed_result",
                    description="Get the processing result of a completed feed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "feed_id": {
                                "type": "string",
                                "description": "Feed ID"
                            }
                        },
                        "required": ["feed_id"]
                    }
                ),
                
                # Financial Tools
                Tool(
                    name="get_financial_events",
                    description="Get financial events and transactions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "posted_after": {
                                "type": "string",
                                "description": "Filter events posted after this date (ISO 8601)"
                            },
                            "posted_before": {
                                "type": "string",
                                "description": "Filter events posted before this date (ISO 8601)"
                            },
                            "max_results_per_page": {
                                "type": "integer",
                                "default": 100,
                                "description": "Maximum results per page"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_financial_events_by_group",
                    description="Get financial events for a specific group",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "event_group_id": {
                                "type": "string",
                                "description": "Financial event group ID"
                            }
                        },
                        "required": ["event_group_id"]
                    }
                ),
                Tool(
                    name="get_financial_event_groups",
                    description="Get financial event groups",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "financial_event_group_started_after": {
                                "type": "string",
                                "description": "Filter groups started after this date (ISO 8601)"
                            },
                            "financial_event_group_started_before": {
                                "type": "string",
                                "description": "Filter groups started before this date (ISO 8601)"
                            }
                        },
                        "required": []
                    }
                )
            ]
            
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                # Ensure client is initialized
                if not self.client:
                    await self._initialize_client()
                
                # Route to appropriate tool handler
                result = await self._route_tool_call(name, arguments)
                
                # Format result as JSON
                import json
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
                
            except Exception as e:
                logger.error(f"Tool call error: {e}")
                error_result = {
                    "success": False,
                    "error": str(e),
                    "tool": name,
                    "message": f"Failed to execute tool {name}"
                }
                import json
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    async def _initialize_client(self):
        """Initialize the SP-API client."""
        if not self.config:
            self.config = load_config()
        
        if not self.client:
            self.client = SPAPIClient(self.config)
            
            # Initialize tool instances
            self.tools = {
                'auth': AuthTools(self.client, self.config),
                'orders': OrdersTools(self.client, self.config),
                'inventory': InventoryTools(self.client, self.config),
                'reports': ReportsTools(self.client, self.config),
                'catalog': CatalogTools(self.client, self.config),
                'listings': ListingsTools(self.client, self.config),
                'feeds': FeedsTools(self.client, self.config),
                'financial': FinancialTools(self.client, self.config)
            }
    
    async def _route_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool calls to appropriate handlers."""
        
        # Authentication tools
        if name == "validate_credentials":
            return await self.tools['auth'].validate_credentials()
        elif name == "refresh_access_token":
            return await self.tools['auth'].refresh_access_token()
        elif name == "get_marketplace_participation":
            return await self.tools['auth'].get_marketplace_participation()
        
        # Orders tools
        elif name == "get_orders":
            return await self.tools['orders'].get_orders(**arguments)
        elif name == "get_order_details":
            return await self.tools['orders'].get_order_details(**arguments)
        elif name == "get_order_items":
            return await self.tools['orders'].get_order_items(**arguments)
        elif name == "update_shipment_status":
            return await self.tools['orders'].update_shipment_status(**arguments)
        
        # Inventory tools
        elif name == "get_inventory_summaries":
            return await self.tools['inventory'].get_inventory_summaries(**arguments)
        elif name == "get_inventory_details":
            return await self.tools['inventory'].get_inventory_details(**arguments)
        elif name == "get_restock_inventory":
            return await self.tools['inventory'].get_restock_inventory(**arguments)
        elif name == "get_stranded_inventory":
            return await self.tools['inventory'].get_stranded_inventory(**arguments)
        
        # Reports tools
        elif name == "request_report":
            return await self.tools['reports'].request_report(**arguments)
        elif name == "get_report_status":
            return await self.tools['reports'].get_report_status(**arguments)
        elif name == "download_report":
            return await self.tools['reports'].download_report(**arguments)
        elif name == "get_report_schedules":
            return await self.tools['reports'].get_report_schedules(**arguments)
        
        # Catalog tools
        elif name == "search_catalog_items":
            return await self.tools['catalog'].search_catalog_items(**arguments)
        elif name == "get_catalog_item":
            return await self.tools['catalog'].get_catalog_item(**arguments)
        elif name == "get_catalog_item_variations":
            return await self.tools['catalog'].get_catalog_item_variations(**arguments)
        
        # Listings tools
        elif name == "get_listings_item":
            return await self.tools['listings'].get_listings_item(**arguments)
        elif name == "patch_listings_item":
            return await self.tools['listings'].patch_listings_item(**arguments)
        elif name == "get_listings_restrictions":
            return await self.tools['listings'].get_listings_restrictions(**arguments)
        
        # Feeds tools
        elif name == "create_feed":
            return await self.tools['feeds'].create_feed(**arguments)
        elif name == "get_feed_status":
            return await self.tools['feeds'].get_feed_status(**arguments)
        elif name == "get_feed_result":
            return await self.tools['feeds'].get_feed_result(**arguments)
        
        # Financial tools
        elif name == "get_financial_events":
            return await self.tools['financial'].get_financial_events(**arguments)
        elif name == "get_financial_events_by_group":
            return await self.tools['financial'].get_financial_events_by_group(**arguments)
        elif name == "get_financial_event_groups":
            return await self.tools['financial'].get_financial_event_groups(**arguments)
        
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {name}",
                "message": f"Tool {name} is not implemented"
            }
    
    async def run(self):
        """Run the MCP server."""
        # Initialize client before starting server
        await self._initialize_client()
        
        # Log server start
        logger.info("Starting Amazon SP-API MCP Server")
        logger.info(f"Configuration: Region={self.config.region}, Marketplaces={self.config.marketplace_ids}")
        
        # Run server
        async with self.server.run_session() as session:
            await session.wait_for_completion()

def main():
    """Main entry point."""
    server = AmazonSPAPIMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()