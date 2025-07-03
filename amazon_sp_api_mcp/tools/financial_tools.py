"""
Financial data tools for Amazon SP-API MCP.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from ..client.http_client import SPAPIClient
from ..config import SPAPIConfig

logger = logging.getLogger(__name__)

class FinancialTools:
    """Tools for managing financial data through SP-API."""
    
    def __init__(self, client: SPAPIClient, config: SPAPIConfig):
        self.client = client
        self.config = config
    
    async def get_financial_events(
        self,
        max_results_per_page: int = 100,
        posted_after: Optional[str] = None,
        posted_before: Optional[str] = None,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get financial events and transactions."""
        try:
            # Set default date range if not specified
            if not posted_after:
                posted_after = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Build query parameters
            params = {
                'MaxResultsPerPage': min(max_results_per_page, 100)
            }
            
            if posted_after:
                params['PostedAfter'] = posted_after
            if posted_before:
                params['PostedBefore'] = posted_before
            if next_token:
                params['NextToken'] = next_token
            
            # Make API call
            response = await self.client.get(
                endpoint='finances',
                path='/finances/v0/financialEvents',
                params=params
            )
            
            # Process response
            payload = response.get('payload', {})
            financial_events = payload.get('FinancialEvents', {})
            
            result = {
                'success': True,
                'financial_events': self._format_financial_events(financial_events),
                'pagination': {
                    'next_token': payload.get('NextToken'),
                    'has_more': bool(payload.get('NextToken'))
                },
                'date_range': {
                    'posted_after': posted_after,
                    'posted_before': posted_before
                },
                'summary': self._calculate_financial_summary(financial_events)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Get financial events error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve financial events'
            }
    
    async def get_financial_events_by_group(
        self,
        event_group_id: str,
        max_results_per_page: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get financial events for a specific group."""
        try:
            # Build query parameters
            params = {
                'MaxResultsPerPage': min(max_results_per_page, 100)
            }
            
            if next_token:
                params['NextToken'] = next_token
            
            # Make API call
            response = await self.client.get(
                endpoint='finances',
                path=f'/finances/v0/financialEventGroups/{event_group_id}/financialEvents',
                params=params
            )
            
            # Process response
            payload = response.get('payload', {})
            financial_events = payload.get('FinancialEvents', {})
            
            result = {
                'success': True,
                'event_group_id': event_group_id,
                'financial_events': self._format_financial_events(financial_events),
                'pagination': {
                    'next_token': payload.get('NextToken'),
                    'has_more': bool(payload.get('NextToken'))
                },
                'summary': self._calculate_financial_summary(financial_events)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Get financial events by group error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to retrieve financial events for group {event_group_id}'
            }
    
    async def get_financial_event_groups(
        self,
        max_results_per_page: int = 100,
        financial_event_group_started_before: Optional[str] = None,
        financial_event_group_started_after: Optional[str] = None,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get financial event groups."""
        try:
            # Set default date range if not specified
            if not financial_event_group_started_after:
                financial_event_group_started_after = (datetime.utcnow() - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Build query parameters
            params = {
                'MaxResultsPerPage': min(max_results_per_page, 100)
            }
            
            if financial_event_group_started_after:
                params['FinancialEventGroupStartedAfter'] = financial_event_group_started_after
            if financial_event_group_started_before:
                params['FinancialEventGroupStartedBefore'] = financial_event_group_started_before
            if next_token:
                params['NextToken'] = next_token
            
            # Make API call
            response = await self.client.get(
                endpoint='finances',
                path='/finances/v0/financialEventGroups',
                params=params
            )
            
            # Process response
            payload = response.get('payload', {})
            event_groups = payload.get('FinancialEventGroupList', [])
            
            result = {
                'success': True,
                'financial_event_groups': [],
                'pagination': {
                    'next_token': payload.get('NextToken'),
                    'has_more': bool(payload.get('NextToken')),
                    'total_returned': len(event_groups)
                },
                'date_range': {
                    'started_after': financial_event_group_started_after,
                    'started_before': financial_event_group_started_before
                }
            }
            
            # Process each event group
            for group in event_groups:
                group_info = {
                    'financial_event_group_id': group.get('FinancialEventGroupId'),
                    'processing_status': group.get('ProcessingStatus'),
                    'fund_transfer_status': group.get('FundTransferStatus'),
                    'original_total': self._format_currency(group.get('OriginalTotal', {})),
                    'converted_total': self._format_currency(group.get('ConvertedTotal', {})),
                    'fund_transfer_date': group.get('FundTransferDate'),
                    'trace_id': group.get('TraceId'),
                    'account_tail': group.get('AccountTail'),
                    'beginning_balance': self._format_currency(group.get('BeginningBalance', {})),
                    'financial_event_group_start': group.get('FinancialEventGroupStart'),
                    'financial_event_group_end': group.get('FinancialEventGroupEnd')
                }
                
                result['financial_event_groups'].append(group_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Get financial event groups error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve financial event groups'
            }
    
    def _format_financial_events(self, financial_events: Dict[str, Any]) -> Dict[str, Any]:
        """Format financial events for consistent output."""
        formatted_events = {}
        
        # Shipment events
        if 'ShipmentEventList' in financial_events:
            formatted_events['shipment_events'] = []
            for event in financial_events['ShipmentEventList']:
                shipment_event = {
                    'amazon_order_id': event.get('AmazonOrderId'),
                    'seller_order_id': event.get('SellerOrderId'),
                    'marketplace_name': event.get('MarketplaceName'),
                    'order_charge_list': [self._format_charge(charge) for charge in event.get('OrderChargeList', [])],
                    'order_charge_adjustment_list': [self._format_charge(charge) for charge in event.get('OrderChargeAdjustmentList', [])],
                    'shipment_fee_list': [self._format_fee(fee) for fee in event.get('ShipmentFeeList', [])],
                    'shipment_fee_adjustment_list': [self._format_fee(fee) for fee in event.get('ShipmentFeeAdjustmentList', [])],
                    'order_fee_list': [self._format_fee(fee) for fee in event.get('OrderFeeList', [])],
                    'order_fee_adjustment_list': [self._format_fee(fee) for fee in event.get('OrderFeeAdjustmentList', [])],
                    'direct_payment_list': [self._format_direct_payment(payment) for payment in event.get('DirectPaymentList', [])],
                    'posted_date': event.get('PostedDate')
                }
                formatted_events['shipment_events'].append(shipment_event)
        
        # Refund events
        if 'RefundEventList' in financial_events:
            formatted_events['refund_events'] = []
            for event in financial_events['RefundEventList']:
                refund_event = {
                    'amazon_order_id': event.get('AmazonOrderId'),
                    'seller_order_id': event.get('SellerOrderId'),
                    'marketplace_name': event.get('MarketplaceName'),
                    'order_charge_adjustment_list': [self._format_charge(charge) for charge in event.get('OrderChargeAdjustmentList', [])],
                    'shipment_fee_adjustment_list': [self._format_fee(fee) for fee in event.get('ShipmentFeeAdjustmentList', [])],
                    'order_fee_adjustment_list': [self._format_fee(fee) for fee in event.get('OrderFeeAdjustmentList', [])],
                    'direct_payment_list': [self._format_direct_payment(payment) for payment in event.get('DirectPaymentList', [])],
                    'posted_date': event.get('PostedDate')
                }
                formatted_events['refund_events'].append(refund_event)
        
        return formatted_events
    
    def _format_charge(self, charge: Dict[str, Any]) -> Dict[str, Any]:
        """Format charge information."""
        return {
            'charge_type': charge.get('ChargeType'),
            'charge_amount': self._format_currency(charge.get('ChargeAmount', {})),
            'tax_amount': self._format_currency(charge.get('TaxAmount', {}))
        }
    
    def _format_fee(self, fee: Dict[str, Any]) -> Dict[str, Any]:
        """Format fee information."""
        return {
            'fee_type': fee.get('FeeType'),
            'fee_amount': self._format_currency(fee.get('FeeAmount', {})),
            'tax_amount': self._format_currency(fee.get('TaxAmount', {}))
        }
    
    def _format_direct_payment(self, payment: Dict[str, Any]) -> Dict[str, Any]:
        """Format direct payment information."""
        return {
            'direct_payment_type': payment.get('DirectPaymentType'),
            'direct_payment_amount': self._format_currency(payment.get('DirectPaymentAmount', {}))
        }
    
    def _format_currency(self, currency_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format currency amount."""
        return {
            'amount': currency_data.get('CurrencyAmount'),
            'currency_code': currency_data.get('CurrencyCode')
        }
    
    def _calculate_financial_summary(self, financial_events: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from financial events."""
        summary = {
            'total_shipment_events': 0,
            'total_refund_events': 0,
            'total_charges': {'EUR': 0, 'USD': 0, 'GBP': 0},
            'total_fees': {'EUR': 0, 'USD': 0, 'GBP': 0},
            'total_refunds': {'EUR': 0, 'USD': 0, 'GBP': 0}
        }
        
        # Count shipment events
        shipment_events = financial_events.get('ShipmentEventList', [])
        summary['total_shipment_events'] = len(shipment_events)
        
        # Count refund events
        refund_events = financial_events.get('RefundEventList', [])
        summary['total_refund_events'] = len(refund_events)
        
        # Calculate totals (simplified - would need more complex logic for real totals)
        for event in shipment_events:
            for charge in event.get('OrderChargeList', []):
                charge_amount = charge.get('ChargeAmount', {})
                currency = charge_amount.get('CurrencyCode', 'EUR')
                amount = float(charge_amount.get('CurrencyAmount', 0))
                if currency in summary['total_charges']:
                    summary['total_charges'][currency] += amount
        
        return summary