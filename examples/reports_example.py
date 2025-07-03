#!/usr/bin/env python3
"""
Reports example for Amazon SP-API MCP.
"""

import asyncio
import json
import time
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    """Demonstrate reports functionality."""
    
    async with stdio_client(["amazon-sp-api-mcp"]) as (read, write):
        async with ClientSession(read, write) as session:
            
            print("📊 Amazon SP-API Reports Example")
            print("=" * 50)
            
            # 1. Request a report
            print("\n1️⃣ Requesting inventory report...")
            try:
                result = await session.call_tool(
                    "request_report",
                    {
                        "report_type": "GET_MERCHANT_LISTINGS_ALL_DATA",
                        "marketplace_ids": ["A1RKKUPIHCS9HS"]
                    }
                )
                data = json.loads(result[0].text)
                if data['success']:
                    report_id = data['report_id']
                    print(f"✅ Report requested: {report_id}")
                    print(f"📅 Date range: {data['data_start_time']} to {data['data_end_time']}")
                else:
                    print(f"❌ Failed to request report: {data.get('error')}")
                    return
            except Exception as e:
                print(f"❌ Error requesting report: {e}")
                return
            
            # 2. Check report status
            print("\n2️⃣ Checking report status...")
            max_checks = 10
            check_count = 0
            
            while check_count < max_checks:
                try:
                    result = await session.call_tool(
                        "get_report_status",
                        {"report_id": report_id}
                    )
                    data = json.loads(result[0].text)
                    
                    if data['success']:
                        status = data['processing_status']
                        print(f"🔄 Status check {check_count + 1}: {status}")
                        
                        if data['ready_for_download']:
                            print("✅ Report is ready for download!")
                            document_id = data['report_document_id']
                            break
                        elif status in ['CANCELLED', 'FATAL']:
                            print(f"❌ Report processing failed: {status}")
                            return
                        else:
                            print("⏳ Report still processing, waiting...")
                            await asyncio.sleep(30)  # Wait 30 seconds
                    else:
                        print(f"❌ Error checking status: {data.get('error')}")
                        return
                        
                except Exception as e:
                    print(f"❌ Error checking report status: {e}")
                    return
                
                check_count += 1
            
            if check_count >= max_checks:
                print("⚠️ Report is taking longer than expected. You can check status later.")
                return
            
            # 3. Download report
            print("\n3️⃣ Downloading report...")
            try:
                result = await session.call_tool(
                    "download_report",
                    {
                        "report_document_id": document_id,
                        "parse_content": True
                    }
                )
                data = json.loads(result[0].text)
                
                if data['success']:
                    print(f"✅ Report downloaded successfully!")
                    print(f"📄 Content type: {data['content_type']}")
                    print(f"📊 Size: {data['content_size']} bytes")
                    
                    if 'parsed_data' in data and data['parsed_data']:
                        parsed_data = data['parsed_data']
                        if isinstance(parsed_data, list) and parsed_data:
                            print(f"📊 Total records: {len(parsed_data)}")
                            print("\n🔍 Sample data (first 3 records):")
                            for i, record in enumerate(parsed_data[:3]):
                                print(f"   Record {i+1}: {record}")
                        else:
                            print("📜 Report content:")
                            print(str(parsed_data)[:500] + "..." if len(str(parsed_data)) > 500 else str(parsed_data))
                    
                else:
                    print(f"❌ Failed to download report: {data.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error downloading report: {e}")
            
            # 4. Get report schedules
            print("\n4️⃣ Getting report schedules...")
            try:
                result = await session.call_tool("get_report_schedules", {})
                data = json.loads(result[0].text)
                
                if data['success']:
                    schedules = data['report_schedules']
                    print(f"📅 Found {len(schedules)} scheduled reports")
                    
                    for schedule in schedules[:5]:  # Show first 5
                        print(f"   - {schedule['report_type']}: {schedule['period']}")
                        print(f"     Next: {schedule.get('next_report_creation_time', 'N/A')}")
                else:
                    print(f"❌ Failed to get schedules: {data.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error getting schedules: {e}")
            
            print("\n✅ Reports example completed!")

if __name__ == "__main__":
    asyncio.run(main())