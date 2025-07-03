"""
Reports management tools for Amazon SP-API MCP.
"""

from typing import Dict, Any, List, Optional
import csv
import json
import gzip
import io
from datetime import datetime, timedelta
import logging

from ..client.http_client import SPAPIClient
from ..config import SPAPIConfig

logger = logging.getLogger(__name__)

class ReportsTools:
    """Tools for managing reports through SP-API."""
    
    def __init__(self, client: SPAPIClient, config: SPAPIConfig):
        self.client = client
        self.config = config
    
    async def request_report(
        self,
        report_type: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        marketplace_ids: Optional[List[str]] = None,
        report_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request a report to be generated."""
        try:
            if not marketplace_ids:
                marketplace_ids = self.config.marketplace_ids
            
            # Set default date range if not specified
            if not start_time:
                start_time = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            if not end_time:
                end_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Prepare request data
            request_data = {
                'reportType': report_type,
                'dataStartTime': start_time,
                'dataEndTime': end_time,
                'marketplaceIds': marketplace_ids
            }
            
            if report_options:
                request_data['reportOptions'] = report_options
            
            # Make API call
            response = await self.client.post(
                endpoint='reports',
                path='/reports/2021-06-30/reports',
                data=request_data
            )
            
            # Process response
            report_id = response.get('reportId')
            
            result = {
                'success': True,
                'report_id': report_id,
                'report_type': report_type,
                'status': 'IN_QUEUE',
                'data_start_time': start_time,
                'data_end_time': end_time,
                'marketplace_ids': marketplace_ids,
                'message': f'Report {report_id} has been queued for generation'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Request report error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to request report of type {report_type}'
            }
    
    async def get_report_status(
        self,
        report_id: str
    ) -> Dict[str, Any]:
        """Get the processing status of a report."""
        try:
            # Make API call
            response = await self.client.get(
                endpoint='reports',
                path=f'/reports/2021-06-30/reports/{report_id}'
            )
            
            # Process response
            result = {
                'success': True,
                'report_id': report_id,
                'report_type': response.get('reportType'),
                'processing_status': response.get('processingStatus'),
                'data_start_time': response.get('dataStartTime'),
                'data_end_time': response.get('dataEndTime'),
                'created_time': response.get('createdTime'),
                'processing_start_time': response.get('processingStartTime'),
                'processing_end_time': response.get('processingEndTime'),
                'report_document_id': response.get('reportDocumentId'),
                'marketplace_ids': response.get('marketplaceIds', [])
            }
            
            # Add status interpretation
            status = response.get('processingStatus', 'UNKNOWN')
            if status == 'DONE':
                result['message'] = 'Report is ready for download'
                result['ready_for_download'] = True
            elif status == 'IN_PROGRESS':
                result['message'] = 'Report is being processed'
                result['ready_for_download'] = False
            elif status == 'IN_QUEUE':
                result['message'] = 'Report is queued for processing'
                result['ready_for_download'] = False
            elif status == 'CANCELLED':
                result['message'] = 'Report processing was cancelled'
                result['ready_for_download'] = False
            elif status == 'FATAL':
                result['message'] = 'Report processing failed'
                result['ready_for_download'] = False
            else:
                result['message'] = f'Report status: {status}'
                result['ready_for_download'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Get report status error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to get status for report {report_id}'
            }
    
    async def download_report(
        self,
        report_document_id: str,
        parse_content: bool = True,
        compression: Optional[str] = None
    ) -> Dict[str, Any]:
        """Download and optionally parse a completed report."""
        try:
            # Get report document details
            doc_response = await self.client.get(
                endpoint='reports',
                path=f'/reports/2021-06-30/documents/{report_document_id}'
            )
            
            report_document_url = doc_response.get('url')
            if not report_document_url:
                return {
                    'success': False,
                    'error': 'No download URL found',
                    'message': f'No download URL for document {report_document_id}'
                }
            
            # Download the report content
            import requests
            download_response = requests.get(report_document_url, timeout=self.config.timeout)
            download_response.raise_for_status()
            
            content = download_response.content
            
            # Handle compression
            if compression == 'GZIP' or doc_response.get('compressionAlgorithm') == 'GZIP':
                content = gzip.decompress(content)
            
            # Convert to text
            text_content = content.decode('utf-8')
            
            result = {
                'success': True,
                'report_document_id': report_document_id,
                'content_type': doc_response.get('contentType', 'text/plain'),
                'compression': doc_response.get('compressionAlgorithm'),
                'raw_content': text_content,
                'content_size': len(text_content)
            }
            
            # Parse content if requested
            if parse_content:
                parsed_data = self._parse_report_content(
                    text_content, 
                    doc_response.get('contentType', 'text/plain')
                )
                result['parsed_data'] = parsed_data
                result['total_records'] = len(parsed_data) if isinstance(parsed_data, list) else 1
            
            return result
            
        except Exception as e:
            logger.error(f"Download report error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to download report document {report_document_id}'
            }
    
    async def get_report_schedules(
        self,
        report_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get scheduled reports."""
        try:
            # Build query parameters
            params = {}
            if report_types:
                params['reportTypes'] = ','.join(report_types)
            
            # Make API call
            response = await self.client.get(
                endpoint='reports',
                path='/reports/2021-06-30/schedules',
                params=params
            )
            
            # Process response
            schedules = response.get('reportSchedules', [])
            
            result = {
                'success': True,
                'report_schedules': [],
                'summary': {
                    'total_schedules': len(schedules),
                    'filtered_by_types': report_types or []
                }
            }
            
            # Process each schedule
            for schedule in schedules:
                schedule_info = {
                    'report_schedule_id': schedule.get('reportScheduleId'),
                    'report_type': schedule.get('reportType'),
                    'marketplace_ids': schedule.get('marketplaceIds', []),
                    'report_options': schedule.get('reportOptions', {}),
                    'period': schedule.get('period'),
                    'next_report_creation_time': schedule.get('nextReportCreationTime')
                }
                
                result['report_schedules'].append(schedule_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Get report schedules error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve report schedules'
            }
    
    def _parse_report_content(self, content: str, content_type: str) -> Any:
        """Parse report content based on content type."""
        try:
            if 'json' in content_type.lower():
                return json.loads(content)
            elif 'csv' in content_type.lower() or 'tab' in content_type.lower():
                # Determine delimiter
                delimiter = '\t' if 'tab' in content_type.lower() else ','
                
                # Parse CSV
                csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
                return list(csv_reader)
            else:
                # Return as lines for other text formats
                return content.strip().split('\n')
                
        except Exception as e:
            logger.warning(f"Failed to parse report content: {e}")
            return content.strip().split('\n')
    
    def get_available_report_types(self) -> Dict[str, List[str]]:
        """Get list of available report types by category."""
        return {
            'inventory': [
                'GET_MERCHANT_LISTINGS_ALL_DATA',
                'GET_MERCHANT_LISTINGS_DATA',
                'GET_MERCHANT_LISTINGS_INACTIVE_DATA',
                'GET_MERCHANT_LISTINGS_DATA_BACK_COMPAT',
                'GET_MERCHANT_CANCELLED_LISTINGS_DATA',
                'GET_MERCHANT_LISTINGS_DEFECT_DATA',
                'GET_AFN_INVENTORY_DATA',
                'GET_FBA_FULFILLMENT_INVENTORY_HEALTH_DATA',
                'GET_FBA_FULFILLMENT_INVENTORY_RECEIPTS_DATA',
                'GET_RESERVED_INVENTORY_DATA',
                'GET_FBA_INVENTORY_PLANNING_DATA',
                'GET_FBA_INVENTORY_AGED_DATA'
            ],
            'orders': [
                'GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL',
                'GET_FLAT_FILE_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL',
                'GET_FLAT_FILE_ARCHIVED_ORDERS_DATA_BY_ORDER_DATE',
                'GET_XML_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL',
                'GET_XML_ALL_ORDERS_DATA_BY_ORDER_DATE_GENERAL'
            ],
            'financial': [
                'GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE',
                'GET_V2_SETTLEMENT_REPORT_DATA_XML',
                'GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2'
            ],
            'fba': [
                'GET_AMAZON_FULFILLED_SHIPMENTS_DATA_GENERAL',
                'GET_FBA_FULFILLMENT_CUSTOMER_SHIPMENT_SALES_DATA',
                'GET_FBA_FULFILLMENT_CUSTOMER_SHIPMENT_PROMOTION_DATA',
                'GET_FBA_FULFILLMENT_CUSTOMER_TAXES_DATA',
                'GET_REMOTE_FULFILLMENT_ELIGIBILITY',
                'GET_FBA_FULFILLMENT_CUSTOMER_RETURNS_DATA',
                'GET_FBA_FULFILLMENT_CUSTOMER_SHIPMENT_REPLACEMENT_DATA',
                'GET_FBA_RECOMMENDED_REMOVAL_DATA',
                'GET_FBA_FULFILLMENT_REMOVAL_ORDER_DETAIL_DATA',
                'GET_FBA_FULFILLMENT_REMOVAL_SHIPMENT_DETAIL_DATA'
            ],
            'performance': [
                'GET_SELLER_FEEDBACK_DATA',
                'GET_V1_SELLER_PERFORMANCE_REPORT'
            ],
            'advertising': [
                'GET_BRAND_ANALYTICS_MARKET_BASKET_REPORT',
                'GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT',
                'GET_BRAND_ANALYTICS_REPEAT_PURCHASE_REPORT'
            ],
            'tax': [
                'GET_GST_MTR_B2B_CUSTOM',
                'GET_GST_MTR_B2C_CUSTOM',
                'SC_VAT_TAX_REPORT'
            ]
        }