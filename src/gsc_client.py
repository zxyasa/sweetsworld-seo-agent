"""Google Search Console API client for keyword research."""
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account


class GSCClient:
    """Client for Google Search Console API."""

    def __init__(self, property_url: str, credentials_file: str):
        """
        Initialize GSC client.

        Args:
            property_url: GSC property URL (e.g., https://sweetsworld.com.au)
            credentials_file: Path to service account credentials JSON file
        """
        self.property_url = property_url

        # Validate credentials file
        creds_path = Path(credentials_file)
        if not creds_path.exists():
            raise FileNotFoundError(
                f"GSC credentials file not found: {credentials_file}\n"
                f"Please download service account credentials from Google Cloud Console"
            )

        # Initialize API client
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            self.service = build('searchconsole', 'v1', credentials=credentials)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GSC client: {str(e)}")

    def get_related_keywords(
        self,
        primary_keyword: str,
        days: int = 90,
        max_results: int = 20
    ) -> Dict[str, any]:
        """
        Get related keywords from Search Console data.

        Args:
            primary_keyword: Primary keyword to search for
            days: Number of days to look back (default: 90)
            max_results: Maximum number of keywords to return (default: 20)

        Returns:
            Dict containing:
                - related_keywords: List of related keyword strings
                - top_queries: List of dicts with query, clicks, impressions
                - primary_keyword_data: Stats for the primary keyword
        """
        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            # Build request
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['query'],
                'rowLimit': max_results * 2,  # Get more to filter
                'startRow': 0
            }

            # Execute query
            response = self.service.searchanalytics().query(
                siteUrl=self.property_url,
                body=request
            ).execute()

            if 'rows' not in response:
                return {
                    'related_keywords': [],
                    'top_queries': [],
                    'primary_keyword_data': None
                }

            # Process results
            all_queries = []
            related_keywords = []
            primary_keyword_data = None

            for row in response.get('rows', []):
                query = row['keys'][0].lower()
                clicks = row.get('clicks', 0)
                impressions = row.get('impressions', 0)
                ctr = row.get('ctr', 0)
                position = row.get('position', 0)

                query_data = {
                    'query': query,
                    'clicks': clicks,
                    'impressions': impressions,
                    'ctr': round(ctr * 100, 2),
                    'position': round(position, 1)
                }

                all_queries.append(query_data)

                # Check if this is the primary keyword
                if primary_keyword.lower() in query:
                    if primary_keyword_data is None or clicks > primary_keyword_data['clicks']:
                        primary_keyword_data = query_data

                    # Add as related keyword
                    if query not in related_keywords and len(related_keywords) < max_results:
                        related_keywords.append(query)

            # Get top queries by clicks
            top_queries = sorted(all_queries, key=lambda x: x['clicks'], reverse=True)[:max_results]

            return {
                'related_keywords': related_keywords[:max_results],
                'top_queries': top_queries,
                'primary_keyword_data': primary_keyword_data
            }

        except Exception as e:
            print(f"⚠️  GSC API error: {str(e)}")
            return {
                'related_keywords': [],
                'top_queries': [],
                'primary_keyword_data': None
            }

    def get_top_pages(self, days: int = 30, max_results: int = 10) -> List[Dict]:
        """
        Get top performing pages by clicks.

        Args:
            days: Number of days to look back
            max_results: Maximum number of pages to return

        Returns:
            List of dicts with page data
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['page'],
                'rowLimit': max_results
            }

            response = self.service.searchanalytics().query(
                siteUrl=self.property_url,
                body=request
            ).execute()

            pages = []
            for row in response.get('rows', []):
                pages.append({
                    'url': row['keys'][0],
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr': round(row.get('ctr', 0) * 100, 2),
                    'position': round(row.get('position', 0), 1)
                })

            return pages

        except Exception as e:
            print(f"⚠️  GSC API error: {str(e)}")
            return []
