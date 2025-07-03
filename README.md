# Amazon SP-API MCP

🚀 **Comprehensive Model Context Protocol (MCP) for Amazon Selling Partner API**

This MCP provides a complete solution for managing Amazon seller operations through the SP-API, specifically optimized for European marketplaces and third-party applications.

## ✨ Features

### 🔐 Authentication & Security
- **Login with Amazon (LWA)** token management
- **AWS IAM** credential handling with automatic signing
- **Automatic token refresh** before expiration
- **Credential rotation** support (180-day cycle)
- **Restricted Data Token (RDT)** for PII operations

### 📦 Core Functionalities

#### 🛒 Orders Management
- Retrieve orders by date range, status, marketplace
- Get detailed order information and line items
- Update shipment status and tracking information
- Support for FBA and FBM fulfillment channels

#### 📊 Inventory Management
- Real-time FBA inventory summaries
- Inventory health monitoring and alerts
- Restock recommendations based on sales velocity
- Stranded inventory identification and management

#### 📈 Reports & Analytics
- Business reports (sales, traffic, conversion metrics)
- Financial reports and settlement data
- FBA reports (fees, storage, shipment details)
- Custom date range reports with automated parsing

#### 🏷️ Product & Listings Management
- Catalog item search and detailed product information
- Listing management (create, update, delete)
- Price and inventory updates
- Product restrictions and compliance checking

#### 📤 Bulk Operations (Feeds)
- Mass data updates via Amazon feeds
- Feed processing status monitoring
- Error handling and result parsing
- Support for all major feed types

#### 💰 Financial Data
- Transaction history and financial events
- Settlement reports and payment details
- Fee breakdowns and cost analysis

## 🌍 Regional Support

**Primary Focus: Europe**
- 🇪🇸 Spain (Amazon.es)
- 🇬🇧 United Kingdom (Amazon.co.uk) 
- 🇩🇪 Germany (Amazon.de)
- 🇮🇹 Italy (Amazon.it)
- 🇫🇷 France (Amazon.fr)
- 🇳🇱 Netherlands (Amazon.nl)
- 🇸🇪 Sweden (Amazon.se)
- 🇵🇱 Poland (Amazon.pl)

## 🚀 Quick Start

### 1. Installation

```bash
# Install via pip
pip install amazon-sp-api-mcp

# Or install from source
git clone https://github.com/WeplTechnology/amazon-sp-api-mcp.git
cd amazon-sp-api-mcp
pip install -e .
```

### 2. Configuration

Set up your environment variables:

```bash
# LWA Credentials
export AMAZON_SP_CLIENT_ID="amzn1.application-oa2-client.xxxxx"
export AMAZON_SP_CLIENT_SECRET="xxxxx"
export AMAZON_SP_REFRESH_TOKEN="Atzr|xxxxx"

# AWS Credentials  
export AWS_ACCESS_KEY_ID="AKIAxxxxx"
export AWS_SECRET_ACCESS_KEY="xxxxx"
export AWS_REGION="eu-west-1"
export AWS_ROLE_ARN="arn:aws:iam::123456789012:role/SP-API-Role"

# SP-API Configuration
export AMAZON_SP_REGION="EU"
export AMAZON_SP_MARKETPLACE_IDS="A1RKKUPIHCS9HS,A13V1IB3VIYZZH"
```

### 3. Usage with MCP Client

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client(["amazon-sp-api-mcp"]) as (read, write):
        async with ClientSession(read, write) as session:
            # Get available tools
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")
            
            # Get recent orders
            result = await session.call_tool(
                "get_orders", 
                {
                    "marketplace_ids": ["A1RKKUPIHCS9HS"],
                    "created_after": "2024-01-01T00:00:00Z",
                    "order_statuses": ["Unshipped"]
                }
            )
            print(f"Orders: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🛠️ Available Tools

### Authentication (3 tools)
- `validate_credentials` - Validate all configured credentials
- `refresh_access_token` - Manually refresh LWA access token
- `get_marketplace_participation` - Get authorized marketplaces

### Orders (4 tools)  
- `get_orders` - Retrieve orders with filtering
- `get_order_details` - Get specific order details
- `get_order_items` - Get order line items
- `update_shipment_status` - Update shipping information

### Inventory (4 tools)
- `get_inventory_summaries` - FBA inventory summaries
- `get_inventory_details` - Detailed inventory by SKU
- `get_restock_inventory` - Restock recommendations  
- `get_stranded_inventory` - Identify stranded inventory

### Reports (4 tools)
- `request_report` - Request report generation
- `get_report_status` - Check report processing status
- `download_report` - Download completed reports
- `get_report_schedules` - Get scheduled reports

### Catalog (3 tools)
- `search_catalog_items` - Search Amazon catalog
- `get_catalog_item` - Get product details
- `get_catalog_item_variations` - Get product variations

### Listings (3 tools)  
- `get_listings_item` - Get listing details
- `patch_listings_item` - Update listing information
- `get_listings_restrictions` - Check listing restrictions

### Feeds (3 tools)
- `create_feed` - Submit bulk data feeds
- `get_feed_status` - Monitor feed processing
- `get_feed_result` - Get feed processing results

### Financial (3 tools)
- `get_financial_events` - Get financial transactions
- `get_financial_events_by_group` - Get events by group
- `get_financial_event_groups` - List financial event groups

## 🔧 Advanced Configuration

### Custom Rate Limiting

```bash
export AMAZON_SP_RATE_LIMIT_BUFFER=0.1
export AMAZON_SP_RETRY_ATTEMPTS=3
export AMAZON_SP_TIMEOUT=30
```

### Sandbox Testing

```bash
export AMAZON_SP_SANDBOX=true
export AMAZON_SP_BASE_URL="https://sandbox.sellingpartnerapi-eu.amazon.com"
```

### Debug Mode

```bash
export AMAZON_SP_DEBUG=true
export AMAZON_SP_LOG_LEVEL="DEBUG"
```

## 📚 Documentation

For detailed documentation on each tool and parameter, check:

- [API Reference](docs/api-reference.md)
- [Authentication Guide](docs/authentication.md)
- [Error Handling](docs/error-handling.md)
- [Rate Limiting](docs/rate-limiting.md)
- [Examples](examples/)

## 🚨 Prerequisites

### Amazon SP-API Application

Before using this MCP, you need:

1. **Developer Account**: Register as an SP-API developer
2. **Application**: Create a public application for third parties
3. **Credentials**: Obtain LWA and AWS IAM credentials
4. **Authorization**: Get refresh tokens from sellers

### Required Permissions

Your application must have these roles:
- Product Listing
- Inventory and Order Tracking  
- Pricing
- Amazon Fulfillment
- Tax Invoicing (for restricted data)

## ⚡ Performance & Reliability

- **Rate Limiting**: Intelligent rate limiting per endpoint
- **Auto-Retry**: Exponential backoff for transient errors
- **Token Management**: Automatic token refresh before expiration
- **Connection Pooling**: Efficient HTTP connection reuse
- **Error Recovery**: Graceful handling of API errors

## 🔒 Security

- **Environment Variables**: All credentials via env vars
- **No Hardcoding**: Zero hardcoded secrets
- **Secure Logging**: No credential exposure in logs
- **PII Protection**: Proper RDT handling for sensitive data
- **HTTPS Only**: Encrypted communication

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=amazon_sp_api_mcp

# Test specific functionality
pytest tests/test_orders.py -v
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
- 📝 [GitHub Issues](https://github.com/WeplTechnology/amazon-sp-api-mcp/issues)
- 📧 Email: [email protected]
- 📖 [Documentation](docs/)

## 🌟 Acknowledgments

- Amazon SP-API team for the comprehensive API
- MCP community for the protocol specifications
- Contributors and testers

---

**Made with ❤️ for Amazon sellers and developers**