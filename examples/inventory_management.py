#!/usr/bin/env python3
"""
Inventory management example for Amazon SP-API MCP.
"""

import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    """Demonstrate inventory management functionality."""
    
    async with stdio_client(["amazon-sp-api-mcp"]) as (read, write):
        async with ClientSession(read, write) as session:
            
            print("📊 Amazon SP-API Inventory Management Example")
            print("=" * 60)
            
            # 1. Get inventory summaries
            print("\n1️⃣ Getting FBA inventory summaries...")
            try:
                result = await session.call_tool(
                    "get_inventory_summaries",
                    {
                        "marketplace_ids": ["A1RKKUPIHCS9HS"],  # Spain
                        "details": True,
                        "max_results": 20
                    }
                )
                data = json.loads(result[0].text)
                
                if data['success']:
                    summaries = data['inventory_summaries']
                    print(f"✅ Found inventory for {len(summaries)} items")
                    print(f"📍 Marketplace: {data['summary']['marketplace_ids']}")
                    
                    # Show inventory health overview
                    total_fulfillable = 0
                    total_reserved = 0
                    total_unfulfillable = 0
                    
                    print("\n📈 Inventory Overview:")
                    for summary in summaries[:10]:  # Show first 10
                        details = summary['inventory_details']
                        fulfillable = details['fulfillable_quantity']
                        reserved = details['reserved_quantity']['total']
                        unfulfillable = details['unfulfillable_quantity']['total']
                        
                        total_fulfillable += fulfillable
                        total_reserved += reserved
                        total_unfulfillable += unfulfillable
                        
                        status = "🟢" if fulfillable > 10 else "🟡" if fulfillable > 0 else "🔴"
                        print(f"   {status} {summary['seller_sku'][:20]:20} | Fulfillable: {fulfillable:4d} | Reserved: {reserved:3d} | Issues: {unfulfillable:2d}")
                    
                    print(f"\n📊 Totals: Fulfillable: {total_fulfillable}, Reserved: {total_reserved}, Issues: {total_unfulfillable}")
                else:
                    print(f"❌ Failed to get inventory: {data.get('error')}")
                    return
                    
            except Exception as e:
                print(f"❌ Error getting inventory: {e}")
                return
            
            # 2. Get detailed inventory for a specific SKU (if any exist)
            if summaries:
                sample_sku = summaries[0]['seller_sku']
                print(f"\n2️⃣ Getting detailed inventory for SKU: {sample_sku}...")
                
                try:
                    result = await session.call_tool(
                        "get_inventory_details",
                        {
                            "seller_sku": sample_sku,
                            "marketplace_id": "A1RKKUPIHCS9HS"
                        }
                    )
                    data = json.loads(result[0].text)
                    
                    if data['success']:
                        inventory = data['inventory']
                        analytics = data['analytics']
                        
                        print(f"✅ Detailed inventory for {sample_sku}:")
                        print(f"   🏷️ Product: {inventory.get('product_name', 'N/A')}")
                        print(f"   📊 Total Quantity: {inventory['total_quantity']}")
                        print(f"   ✅ Fulfillable: {inventory['inventory_details']['fulfillable_quantity']}")
                        print(f"   🔄 Inbound: {inventory['inventory_details']['inbound_working_quantity']}")
                        print(f"   💵 Reserved: {inventory['inventory_details']['reserved_quantity']['total']}")
                        print(f"   ⚠️ Issues: {inventory['inventory_details']['unfulfillable_quantity']['total']}")
                        
                        print(f"\n📈 Analytics:")
                        print(f"   🟢 Availability: {analytics['availability_status']}")
                        print(f"   🎩 Health Score: {analytics['stock_health']}")
                        print(f"   📝 Recommendations:")
                        for rec in analytics['recommended_actions']:
                            print(f"      - {rec}")
                    else:
                        print(f"❌ Failed to get detailed inventory: {data.get('error')}")
                        
                except Exception as e:
                    print(f"❌ Error getting detailed inventory: {e}")
            
            # 3. Get restock recommendations
            print("\n3️⃣ Getting restock recommendations...")
            try:
                result = await session.call_tool(
                    "get_restock_inventory",
                    {
                        "marketplace_ids": ["A1RKKUPIHCS9HS"],
                        "max_results": 10
                    }
                )
                data = json.loads(result[0].text)
                
                if data['success']:
                    recommendations = data['restock_recommendations']
                    print(f"✅ Found {len(recommendations)} restock recommendations")
                    
                    if recommendations:
                        print("\n📦 Top Restock Recommendations:")
                        for rec in recommendations[:5]:  # Show top 5
                            recommended_qty = rec.get('recommended_restock_quantity', 0)
                            available_qty = rec.get('available_quantity', 0)
                            days_supply = rec.get('days_of_supply', 0)
                            alert = rec.get('alert', 'None')
                            
                            urgency = "🔴" if alert else "🟡" if days_supply < 30 else "🟢"
                            print(f"   {urgency} {rec['seller_sku'][:20]:20} | Available: {available_qty:4d} | Recommended: {recommended_qty:4d} | Days: {days_supply:3d} | Alert: {alert}")
                    else:
                        print("✅ No restock recommendations at this time")
                else:
                    print(f"❌ Failed to get restock recommendations: {data.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error getting restock recommendations: {e}")
            
            # 4. Check for stranded inventory
            print("\n4️⃣ Checking for stranded inventory...")
            try:
                result = await session.call_tool(
                    "get_stranded_inventory",
                    {
                        "marketplace_ids": ["A1RKKUPIHCS9HS"],
                        "max_results": 10
                    }
                )
                data = json.loads(result[0].text)
                
                if data['success']:
                    stranded_items = data['stranded_inventory']
                    print(f"✅ Found {len(stranded_items)} potentially stranded items")
                    
                    if stranded_items:
                        print("\n⚠️ Stranded Inventory Issues:")
                        for item in stranded_items[:5]:  # Show first 5
                            total_qty = item['total_quantity']
                            fulfillable_qty = item['fulfillable_quantity']
                            stranded_qty = item['stranded_quantity']
                            issues = item['potential_issues']
                            
                            print(f"   🔴 {item['seller_sku'][:20]:20} | Total: {total_qty:4d} | Stranded: {stranded_qty:4d} | Issues: {', '.join(issues) if issues else 'Unknown'}")
                    else:
                        print("✅ No stranded inventory detected")
                else:
                    print(f"❌ Failed to check stranded inventory: {data.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error checking stranded inventory: {e}")
            
            print("\n✅ Inventory management example completed!")
            print("\n📝 Summary:")
            print("   - Use inventory summaries for daily monitoring")
            print("   - Check restock recommendations regularly")
            print("   - Address stranded inventory issues promptly")
            print("   - Monitor inventory health scores for optimization")

if __name__ == "__main__":
    asyncio.run(main())