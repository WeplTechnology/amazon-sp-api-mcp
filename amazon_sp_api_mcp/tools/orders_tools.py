"""
Orders management tools for Amazon SP-API MCP.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from ..client.http_client import SPAPIClient
from ..config import SPAPIConfig

logger = logging.getLogger(__name__)

class OrdersTools:
    """Tools for managing orders through SP-API."""
    
    def __init__(self, client: SPAPIClient, config: SPAPIConfig):
        self.client = client
        self.config = config
    
    async def get_orders(
        self,
        marketplace_ids: Optional[List[str]] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        last_updated_after: Optional[str] = None,
        order_statuses: Optional[List[str]] = None,
        fulfillment_channels: Optional[List[str]] = None,
        payment_methods: Optional[List[str]] = None,
        buyer_email: Optional[str] = None,
        seller_order_id: Optional[str] = None,
        max_results_per_page: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get orders with filtering options."""
        try:
            # Use configured marketplaces if not specified
            if not marketplace_ids:
                marketplace_ids = self.config.marketplace_ids
            
            # Set default date range if not specified
            if not created_after and not last_updated_after:
                created_after = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Build query parameters
            params = {
                'MarketplaceIds': ','.join(marketplace_ids),
                'MaxResultsPerPage': min(max_results_per_page, 100)
            }
            
            # Add optional parameters
            if created_after:
                params['CreatedAfter'] = created_after
            if created_before:
                params['CreatedBefore'] = created_before
            if last_updated_after:
                params['LastUpdatedAfter'] = last_updated_after
            if order_statuses:
                params['OrderStatuses'] = ','.join(order_statuses)
            if fulfillment_channels:
                params['FulfillmentChannels'] = ','.join(fulfillment_channels)
            if payment_methods:
                params['PaymentMethods'] = ','.join(payment_methods)
            if buyer_email:
                params['BuyerEmail'] = buyer_email
            if seller_order_id:
                params['SellerOrderId'] = seller_order_id
            if next_token:
                params['NextToken'] = next_token
            
            # Make API call
            response = await self.client.get(
                endpoint='orders',
                path='/orders/v0/orders',
                params=params
            )
            
            # Process response
            payload = response.get('payload', {})
            orders = payload.get('Orders', [])
            
            result = {
                'success': True,
                'orders': [],
                'pagination': {
                    'next_token': payload.get('NextToken'),
                    'has_more': bool(payload.get('NextToken')),
                    'total_returned': len(orders)
                },
                'summary': {
                    'date_range': {
                        'created_after': created_after,
                        'created_before': created_before
                    },
                    'filters_applied': {
                        'marketplace_ids': marketplace_ids,
                        'order_statuses': order_statuses,
                        'fulfillment_channels': fulfillment_channels
                    }
                }
            }
            
            # Process each order
            for order in orders:
                order_info = {
                    'amazon_order_id': order.get('AmazonOrderId'),
                    'seller_order_id': order.get('SellerOrderId'),
                    'purchase_date': order.get('PurchaseDate'),
                    'last_update_date': order.get('LastUpdateDate'),
                    'order_status': order.get('OrderStatus'),
                    'fulfillment_channel': order.get('FulfillmentChannel'),
                    'sales_channel': order.get('SalesChannel'),
                    'order_channel': order.get('OrderChannel'),
                    'ship_service_level': order.get('ShipServiceLevel'),
                    'order_total': {
                        'amount': order.get('OrderTotal', {}).get('Amount'),
                        'currency_code': order.get('OrderTotal', {}).get('CurrencyCode')
                    },
                    'number_of_items_shipped': order.get('NumberOfItemsShipped'),
                    'number_of_items_unshipped': order.get('NumberOfItemsUnshipped'),
                    'payment_method': order.get('PaymentMethod'),
                    'marketplace_id': order.get('MarketplaceId'),
                    'shipment_service_level_category': order.get('ShipmentServiceLevelCategory'),
                    'is_business_order': order.get('IsBusinessOrder', False),
                    'is_prime': order.get('IsPrime', False),
                    'is_premium_order': order.get('IsPremiumOrder', False),
                    'is_global_express_enabled': order.get('IsGlobalExpressEnabled', False)
                }
                
                result['orders'].append(order_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Get orders error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to retrieve orders'
            }
    
    async def get_order_details(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """Get detailed information for a specific order."""
        try:
            # Make API call
            response = await self.client.get(
                endpoint='orders',
                path=f'/orders/v0/orders/{order_id}'
            )
            
            # Process response
            payload = response.get('payload', {})
            
            if not payload:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': f'No order found with ID {order_id}'
                }
            
            # Format order details
            order = {
                'amazon_order_id': payload.get('AmazonOrderId'),
                'seller_order_id': payload.get('SellerOrderId'),
                'purchase_date': payload.get('PurchaseDate'),
                'last_update_date': payload.get('LastUpdateDate'),
                'order_status': payload.get('OrderStatus'),
                'fulfillment_channel': payload.get('FulfillmentChannel'),
                'sales_channel': payload.get('SalesChannel'),
                'order_total': {
                    'amount': payload.get('OrderTotal', {}).get('Amount'),
                    'currency_code': payload.get('OrderTotal', {}).get('CurrencyCode')
                },
                'number_of_items_shipped': payload.get('NumberOfItemsShipped'),
                'number_of_items_unshipped': payload.get('NumberOfItemsUnshipped'),
                'payment_method': payload.get('PaymentMethod'),
                'marketplace_id': payload.get('MarketplaceId'),
                'shipping_address': self._format_address(payload.get('ShippingAddress', {})),
                'buyer_info': {
                    'buyer_email': payload.get('BuyerInfo', {}).get('BuyerEmail'),
                    'buyer_name': payload.get('BuyerInfo', {}).get('BuyerName')
                },
                'is_business_order': payload.get('IsBusinessOrder', False),
                'is_prime': payload.get('IsPrime', False),
                'earliest_ship_date': payload.get('EarliestShipDate'),
                'latest_ship_date': payload.get('LatestShipDate'),
                'earliest_delivery_date': payload.get('EarliestDeliveryDate'),
                'latest_delivery_date': payload.get('LatestDeliveryDate')
            }
            
            return {
                'success': True,
                'order': order
            }
            
        except Exception as e:
            logger.error(f"Get order details error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to get details for order {order_id}'
            }
    
    async def get_order_items(
        self,
        order_id: str,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get line items for a specific order."""
        try:
            # Build parameters
            params = {}
            if next_token:
                params['NextToken'] = next_token
            
            # Make API call
            response = await self.client.get(
                endpoint='orders',
                path=f'/orders/v0/orders/{order_id}/orderItems',
                params=params
            )
            
            # Process response
            payload = response.get('payload', {})
            items = payload.get('OrderItems', [])
            
            result = {
                'success': True,
                'order_id': order_id,
                'items': [],
                'pagination': {
                    'next_token': payload.get('NextToken'),
                    'has_more': bool(payload.get('NextToken')),
                    'total_returned': len(items)
                }
            }
            
            # Process each item
            for item in items:
                item_info = {
                    'asin': item.get('ASIN'),
                    'seller_sku': item.get('SellerSKU'),
                    'order_item_id': item.get('OrderItemId'),
                    'title': item.get('Title'),
                    'quantity_ordered': item.get('QuantityOrdered'),
                    'quantity_shipped': item.get('QuantityShipped'),
                    'item_price': {
                        'amount': item.get('ItemPrice', {}).get('Amount'),
                        'currency_code': item.get('ItemPrice', {}).get('CurrencyCode')
                    },
                    'item_tax': {
                        'amount': item.get('ItemTax', {}).get('Amount'),
                        'currency_code': item.get('ItemTax', {}).get('CurrencyCode')
                    },
                    'shipping_price': {
                        'amount': item.get('ShippingPrice', {}).get('Amount'),
                        'currency_code': item.get('ShippingPrice', {}).get('CurrencyCode')
                    },
                    'gift_wrap_price': {
                        'amount': item.get('GiftWrapPrice', {}).get('Amount'),
                        'currency_code': item.get('GiftWrapPrice', {}).get('CurrencyCode')
                    },
                    'promotion_discount': {
                        'amount': item.get('PromotionDiscount', {}).get('Amount'),
                        'currency_code': item.get('PromotionDiscount', {}).get('CurrencyCode')
                    },
                    'condition_note': item.get('ConditionNote'),
                    'condition_id': item.get('ConditionId'),
                    'condition_subtype_id': item.get('ConditionSubtypeId'),
                    'scheduled_delivery_start_date': item.get('ScheduledDeliveryStartDate'),
                    'scheduled_delivery_end_date': item.get('ScheduledDeliveryEndDate')
                }
                
                result['items'].append(item_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Get order items error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to get items for order {order_id}'
            }
    
    async def update_shipment_status(
        self,
        order_id: str,
        shipment_date: str,
        carrier_name: str,
        carrier_code: Optional[str] = None,
        tracking_number: Optional[str] = None,
        ship_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update shipment status for an order."""
        try:
            # Prepare shipment data
            shipment_data = {
                'ShipmentDate': shipment_date,
                'CarrierName': carrier_name
            }
            
            if carrier_code:
                shipment_data['CarrierCode'] = carrier_code
            if tracking_number:
                shipment_data['TrackingNumber'] = tracking_number
            if ship_method:
                shipment_data['ShipMethod'] = ship_method
            
            # Make API call
            response = await self.client.post(
                endpoint='orders',
                path=f'/orders/v0/orders/{order_id}/shipment',
                data=shipment_data
            )
            
            return {
                'success': True,
                'order_id': order_id,
                'message': 'Shipment status updated successfully',
                'shipment_info': shipment_data
            }
            
        except Exception as e:
            logger.error(f"Update shipment status error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to update shipment status for order {order_id}'
            }
    
    def _format_address(self, address: Dict[str, Any]) -> Dict[str, Any]:
        """Format shipping address from API response."""
        return {
            'name': address.get('Name'),
            'address_line1': address.get('AddressLine1'),
            'address_line2': address.get('AddressLine2'),
            'address_line3': address.get('AddressLine3'),
            'city': address.get('City'),
            'county': address.get('County'),
            'district': address.get('District'),
            'state_or_region': address.get('StateOrRegion'),
            'postal_code': address.get('PostalCode'),
            'country_code': address.get('CountryCode'),
            'phone': address.get('Phone')
        }