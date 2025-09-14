#!/usr/bin/env python3
"""
Scraping CLI - Command-line interface for multi-source profile scraping
"""

import sys
import os
import json
from pathlib import Path
import argparse
from typing import List, Optional
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ScraperManager, SourceType
from scrapers.instagram_scraper import InstagramScraper
from scrapers.google_images_scraper import GoogleImagesScraper
from loguru import logger


class ScrapingCLI:
    """Command-line interface for profile scraping"""
    
    def __init__(self):
        self.scraper_manager = ScraperManager()
        self._register_scrapers()
        
    def _register_scrapers(self):
        """Register available scrapers"""
        try:
            # Register Instagram scraper
            instagram_scraper = InstagramScraper(headless=True)
            self.scraper_manager.register_scraper(instagram_scraper)
            
            # Register Google Images scraper
            google_scraper = GoogleImagesScraper(headless=True)
            self.scraper_manager.register_scraper(google_scraper)
            
            logger.info("All scrapers registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering scrapers: {e}")
    
    def search_profiles(self, query: str, sources: Optional[List[str]] = None, 
                       limit: int = 20, output: Optional[str] = None):
        """Search for profiles across sources"""
        print(f"🔍 Searching for: '{query}'")
        print(f"📊 Limit: {limit} profiles per source")
        
        # Convert source strings to SourceType
        source_types = []
        if sources:
            for source in sources:
                try:
                    source_types.append(SourceType(source.lower().replace('_', '')))
                except ValueError:
                    print(f"❌ Unknown source: {source}")
                    return
        else:
            source_types = self.scraper_manager.get_available_sources()
        
        print(f"🎯 Sources: {[s.value for s in source_types]}")
        print()
        
        # Perform search
        start_time = datetime.now()
        results = self.scraper_manager.search_all_sources(
            query=query, 
            limit_per_source=limit,
            sources=source_types
        )
        
        # Display results
        total_found = 0
        total_errors = 0
        
        for source_type, result in results.items():
            print(f"📱 {source_type.value.upper()}")
            print(f"  ✅ Found: {result.successful} profiles")
            print(f"  ❌ Failed: {result.failed}")
            print(f"  ⏭️  Skipped: {result.skipped}")
            print(f"  ⏱️  Time: {result.execution_time:.2f}s")
            
            if result.error_messages:
                print(f"  ⚠️  Errors: {len(result.error_messages)}")
                for error in result.error_messages[:3]:  # Show first 3 errors
                    print(f"     • {error}")
            
            total_found += result.successful
            total_errors += result.failed
            print()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"🎉 Search completed in {elapsed:.2f}s")
        print(f"📈 Total found: {total_found} profiles")
        if total_errors > 0:
            print(f"⚠️  Total errors: {total_errors}")
        
        # Save results to file if requested
        if output:
            self._save_results_to_file(results, output, query)
        
        # Show sample profiles
        self._show_sample_profiles(results, limit=3)
    
    def list_cached_profiles(self, source: Optional[str] = None, 
                           max_age_hours: Optional[int] = None):
        """List cached profiles"""
        source_type = None
        if source:
            try:
                source_type = SourceType(source.lower())
            except ValueError:
                print(f"❌ Unknown source: {source}")
                return
        
        profiles = self.scraper_manager.get_cached_profiles(
            source_type=source_type,
            max_age_hours=max_age_hours
        )
        
        if not profiles:
            print("📭 No cached profiles found")
            return
        
        print(f"💾 Found {len(profiles)} cached profiles")
        if source_type:
            print(f"🎯 Source: {source_type.value}")
        if max_age_hours:
            print(f"⏰ Max age: {max_age_hours} hours")
        print()
        
        # Group by source
        by_source = {}
        for profile in profiles:
            source_key = profile.source_type.value
            if source_key not in by_source:
                by_source[source_key] = []
            by_source[source_key].append(profile)
        
        for source_key, source_profiles in by_source.items():
            print(f"📱 {source_key.upper()} ({len(source_profiles)} profiles)")
            
            for i, profile in enumerate(source_profiles[:5]):  # Show first 5
                age_str = f", {profile.age}" if profile.age else ""
                location_str = f", {profile.location}" if profile.location else ""
                print(f"  {i+1}. {profile.name or 'Unknown'}{age_str}{location_str}")
                print(f"     ID: {profile.source_id}")
                print(f"     Images: {profile.image_count}")
                print(f"     Scraped: {profile.scraped_at.strftime('%Y-%m-%d %H:%M')}")
                if profile.bio:
                    bio_preview = profile.bio[:60] + "..." if len(profile.bio) > 60 else profile.bio
                    print(f"     Bio: {bio_preview}")
                print()
            
            if len(source_profiles) > 5:
                print(f"  ... and {len(source_profiles) - 5} more")
                print()
    
    def get_scraping_stats(self, days: int = 7):
        """Show scraping statistics"""
        stats = self.scraper_manager.get_scraping_stats(days)
        
        print(f"📊 Scraping Statistics (Last {days} days)")
        print("=" * 50)
        
        print(f"🎯 Total Profiles: {stats['total_profiles']}")
        print()
        
        print("📱 By Source:")
        for source, count in stats['profile_counts'].items():
            print(f"  {source}: {count} profiles")
        print()
        
        if stats['session_stats']:
            print("📈 Session Stats:")
            for source, session_stats in stats['session_stats'].items():
                print(f"  {source}:")
                print(f"    Sessions: {session_stats['sessions']}")
                print(f"    Successful: {session_stats['successful']}")
                print(f"    Failed: {session_stats['failed']}")
                print(f"    Avg Time: {session_stats['avg_execution_time']:.2f}s")
            print()
    
    def cleanup_old_profiles(self, max_age_days: int = 30, dry_run: bool = False):
        """Clean up old cached profiles"""
        if dry_run:
            print(f"🔍 DRY RUN: Would delete profiles older than {max_age_days} days")
            # Get profiles that would be deleted
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(days=max_age_days)
            profiles = self.scraper_manager.get_cached_profiles()
            old_profiles = [p for p in profiles if p.scraped_at < cutoff]
            print(f"📊 Would delete {len(old_profiles)} profiles")
            
            if old_profiles:
                print("\n🗑️  Profiles to be deleted:")
                for profile in old_profiles[:10]:  # Show first 10
                    print(f"  • {profile.name or profile.source_id} ({profile.source_type.value}) - {profile.scraped_at.strftime('%Y-%m-%d')}")
                if len(old_profiles) > 10:
                    print(f"  ... and {len(old_profiles) - 10} more")
        else:
            print(f"🗑️  Cleaning up profiles older than {max_age_days} days...")
            deleted_count = self.scraper_manager.cleanup_old_profiles(max_age_days)
            print(f"✅ Deleted {deleted_count} old profiles")
    
    def export_profiles(self, output_file: str, source: Optional[str] = None, 
                       format: str = 'json'):
        """Export profiles to file"""
        source_type = None
        if source:
            try:
                source_type = SourceType(source.lower())
            except ValueError:
                print(f"❌ Unknown source: {source}")
                return
        
        profiles = self.scraper_manager.get_cached_profiles(source_type=source_type)
        
        if not profiles:
            print("📭 No profiles to export")
            return
        
        # Convert to dictionaries
        profile_dicts = [profile.to_dict() for profile in profiles]
        
        try:
            if format.lower() == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(profile_dicts, f, indent=2, ensure_ascii=False, default=str)
            elif format.lower() == 'csv':
                import csv
                if profile_dicts:
                    with open(output_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=profile_dicts[0].keys())
                        writer.writeheader()
                        for profile_dict in profile_dicts:
                            # Convert lists/dicts to strings for CSV
                            csv_row = {}
                            for k, v in profile_dict.items():
                                if isinstance(v, (list, dict)):
                                    csv_row[k] = json.dumps(v)
                                else:
                                    csv_row[k] = v
                            writer.writerow(csv_row)
            else:
                print(f"❌ Unsupported format: {format}")
                return
            
            print(f"✅ Exported {len(profiles)} profiles to {output_file}")
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def _save_results_to_file(self, results, output_file: str, query: str):
        """Save search results to file"""
        try:
            output_data = {
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'results': {}
            }
            
            for source_type, result in results.items():
                output_data['results'][source_type.value] = {
                    'total_found': result.total_found,
                    'successful': result.successful,
                    'failed': result.failed,
                    'skipped': result.skipped,
                    'execution_time': result.execution_time,
                    'profiles': [profile.to_dict() for profile in result.profiles],
                    'errors': result.error_messages
                }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"💾 Results saved to {output_file}")
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
    
    def _show_sample_profiles(self, results, limit: int = 3):
        """Show sample profiles from results"""
        print("👥 Sample Profiles:")
        print("-" * 40)
        
        shown = 0
        for source_type, result in results.items():
            if shown >= limit:
                break
                
            for profile in result.profiles[:limit-shown]:
                print(f"📱 {source_type.value.upper()}: {profile.name or 'Unknown'}")
                if profile.age:
                    print(f"   Age: {profile.age}")
                if profile.location:
                    print(f"   Location: {profile.location}")
                if profile.bio:
                    bio_preview = profile.bio[:80] + "..." if len(profile.bio) > 80 else profile.bio
                    print(f"   Bio: {bio_preview}")
                print(f"   Images: {profile.image_count}")
                print(f"   Confidence: {profile.confidence_score:.2f}")
                print()
                
                shown += 1
                if shown >= limit:
                    break
        
        if shown == 0:
            print("   No profiles to display")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Multi-Source Profile Scraper')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for profiles')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--sources', nargs='+', 
                              choices=['instagram', 'google_images'],
                              help='Sources to search (default: all)')
    search_parser.add_argument('--limit', type=int, default=20,
                              help='Max profiles per source (default: 20)')
    search_parser.add_argument('--output', help='Save results to file')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List cached profiles')
    list_parser.add_argument('--source', choices=['instagram', 'google_images'],
                            help='Filter by source')
    list_parser.add_argument('--max-age-hours', type=int,
                            help='Max age in hours')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show scraping statistics')
    stats_parser.add_argument('--days', type=int, default=7,
                             help='Number of days to analyze (default: 7)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old profiles')
    cleanup_parser.add_argument('--max-age-days', type=int, default=30,
                               help='Max age in days (default: 30)')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be deleted without deleting')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export profiles to file')
    export_parser.add_argument('output_file', help='Output file path')
    export_parser.add_argument('--source', choices=['instagram', 'google_images'],
                              help='Filter by source')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json',
                              help='Output format (default: json)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create necessary directories
    os.makedirs('data/scraped_profiles', exist_ok=True)
    
    cli = ScrapingCLI()
    
    try:
        if args.command == 'search':
            cli.search_profiles(args.query, args.sources, args.limit, args.output)
        elif args.command == 'list':
            cli.list_cached_profiles(args.source, args.max_age_hours)
        elif args.command == 'stats':
            cli.get_scraping_stats(args.days)
        elif args.command == 'cleanup':
            cli.cleanup_old_profiles(args.max_age_days, args.dry_run)
        elif args.command == 'export':
            cli.export_profiles(args.output_file, args.source, args.format)
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()