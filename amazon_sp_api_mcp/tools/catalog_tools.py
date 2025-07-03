"""
Catalog management tools for Amazon SP-API MCP.
"""

from typing import Dict, Any, List, Optional
import logging

from ..client.http_client import SPAPIClient
from ..config import SPAPIConfig

logger = logging.getLogger(__name__)

class CatalogTools:
    """Tools for managing catalog items through SP-API."""
    
    def __init__(self, client: SPAPIClient, config: SPAPIConfig):
        self.client = client
        self.config = config
    
    async def search_catalog_items(
        self,
        keywords: Optional[str] = None,
        marketplace_ids: Optional[List[str]] = None,
        included_data: Optional[List[str]] = None,
        brand_names: Optional[List[str]] = None,
        classification_ids: Optional[List[str]] = None,
        page_size: int = 20,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for catalog items."""
        try:
            if not marketplace_ids:
                marketplace_ids = self.config.marketplace_ids
            
            if not included_data:
                included_data = ['summaries', 'attributes', 'images']
            
            # Build query parameters
            params = {
                'marketplaceIds': ','.join(marketplace_ids),
                'includedData': ','.join(included_data),
                'pageSize': min(page_size, 20)
            }
            
            if keywords:
                params['keywords'] = keywords
            if brand_names:
                params['brandNames'] = ','.join(brand_names)
            if classification_ids:
                params['classificationIds'] = ','.join(classification_ids)
            if page_token:
                params['pageToken'] = page_token
            
            # Make API call
            response = await self.client.get(
                endpoint='catalog',
                path='/catalog/2022-04-01/items',
                params=params
            )
            
            # Process response
            items = response.get('items', [])
            pagination = response.get('pagination', {})
            
            result = {
                'success': True,
                'items': [],
                'pagination': {
                    'next_token': pagination.get('nextToken'),
                    'previous_token': pagination.get('previousToken'),
                    'has_more': bool(pagination.get('nextToken')),
                    'total_returned': len(items)
                },
                'search_criteria': {
                    'keywords': keywords,
                    'marketplace_ids': marketplace_ids,
                    'brand_names': brand_names,
                    'included_data': included_data
                }
            }
            
            # Process each item
            for item in items:
                item_info = self._format_catalog_item(item)
                result['items'].append(item_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Search catalog items error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to search catalog items'
            }
    
    async def get_catalog_item(
        self,
        asin: str,
        marketplace_ids: Optional[List[str]] = None,
        included_data: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get detailed information about a specific catalog item."""
        try:
            if not marketplace_ids:
                marketplace_ids = self.config.marketplace_ids
            
            if not included_data:
                included_data = [
                    'summaries', 'attributes', 'dimensions', 
                    'images', 'productTypes', 'relationships', 'salesRanks'
                ]
            
            # Build query parameters
            params = {
                'marketplaceIds': ','.join(marketplace_ids),
                'includedData': ','.join(included_data)
            }
            
            # Make API call
            response = await self.client.get(
                endpoint='catalog',
                path=f'/catalog/2022-04-01/items/{asin}',
                params=params
            )
            
            # Process response
            item_info = self._format_catalog_item(response)
            
            result = {
                'success': True,
                'asin': asin,
                'item': item_info,
                'marketplace_ids': marketplace_ids
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Get catalog item error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to get catalog item {asin}'
            }
    
    async def get_catalog_item_variations(
        self,
        asin: str,
        marketplace_ids: Optional[List[str]] = None,
        included_data: Optional[List[str]] = None,
        page_size: int = 20,
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get variations of a parent catalog item."""
        try:
            if not marketplace_ids:
                marketplace_ids = self.config.marketplace_ids
            
            if not included_data:
                included_data = ['summaries', 'attributes']
            
            # Build query parameters
            params = {
                'marketplaceIds': ','.join(marketplace_ids),
                'includedData': ','.join(included_data),
                'pageSize': min(page_size, 20)
            }
            
            if page_token:
                params['pageToken'] = page_token
            
            # Make API call
            response = await self.client.get(
                endpoint='catalog',
                path=f'/catalog/2022-04-01/items/{asin}/variations',
                params=params
            )
            
            # Process response
            variations = response.get('variations', [])
            pagination = response.get('pagination', {})
            
            result = {
                'success': True,
                'parent_asin': asin,
                'variations': [],
                'pagination': {
                    'next_token': pagination.get('nextToken'),
                    'previous_token': pagination.get('previousToken'),
                    'has_more': bool(pagination.get('nextToken')),
                    'total_returned': len(variations)
                }
            }
            
            # Process each variation
            for variation in variations:
                variation_info = self._format_catalog_item(variation)
                result['variations'].append(variation_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Get catalog item variations error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to get variations for catalog item {asin}'
            }
    
    def _format_catalog_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format catalog item data for consistent output."""
        formatted_item = {
            'asin': item.get('asin')
        }
        
        # Add summaries
        summaries = item.get('summaries', [])
        if summaries:
            summary = summaries[0]  # Use first summary
            formatted_item.update({
                'item_name': summary.get('itemName'),
                'brand': summary.get('brand'),
                'color': summary.get('color'),
                'item_classification': summary.get('itemClassification'),
                'manufacturer': summary.get('manufacturer'),
                'model_number': summary.get('modelNumber'),
                'package_quantity': summary.get('packageQuantity'),
                'part_number': summary.get('partNumber'),
                'size': summary.get('size'),
                'style': summary.get('style'),
                'website_display_group': summary.get('websiteDisplayGroup'),
                'website_display_group_name': summary.get('websiteDisplayGroupName')
            })
        
        # Add attributes
        attributes = item.get('attributes', {})
        if attributes:
            formatted_item['attributes'] = self._format_attributes(attributes)
        
        # Add images
        images = item.get('images', [])
        if images:
            formatted_item['images'] = [{
                'variant': img.get('variant'),
                'link': img.get('link'),
                'height': img.get('height'),
                'width': img.get('width')
            } for img in images]
        
        # Add dimensions
        dimensions = item.get('dimensions', [])
        if dimensions:
            formatted_item['dimensions'] = [{
                'name': dim.get('name'),
                'value': dim.get('value'),
                'unit': dim.get('unit')
            } for dim in dimensions]
        
        # Add product types
        product_types = item.get('productTypes', [])
        if product_types:
            formatted_item['product_types'] = [{
                'product_type': pt.get('productType'),
                'marketplace_id': pt.get('marketplaceId')
            } for pt in product_types]
        
        # Add sales ranks
        sales_ranks = item.get('salesRanks', [])
        if sales_ranks:
            formatted_item['sales_ranks'] = [{
                'product_category_id': sr.get('productCategoryId'),
                'rank': sr.get('rank'),
                'marketplace_id': sr.get('marketplaceId')
            } for sr in sales_ranks]
        
        return formatted_item
    
    def _format_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Format product attributes for easier consumption."""
        formatted_attrs = {}
        
        for attr_name, attr_data in attributes.items():
            if isinstance(attr_data, list) and attr_data:
                # Take first value if multiple
                attr_value = attr_data[0]
                if isinstance(attr_value, dict):
                    # Extract value and unit if present
                    if 'value' in attr_value:
                        formatted_attrs[attr_name] = {
                            'value': attr_value.get('value'),
                            'unit': attr_value.get('unit')
                        }
                    else:
                        formatted_attrs[attr_name] = attr_value
                else:
                    formatted_attrs[attr_name] = attr_value
            elif isinstance(attr_data, dict):
                formatted_attrs[attr_name] = attr_data
            else:
                formatted_attrs[attr_name] = attr_data
        
        return formatted_attrs