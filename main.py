import argparse
import sys
from typing import List

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import config
from scrapers.base import Product
from scrapers.mercadolivre import MercadoLivreScraper
from scrapers.amazon import AmazonScraper
from filters import apply_filters, deduplicate_products
from affiliate import apply_affiliate_links
from exporters import Exporter
from templates import format_deals_as_separate_messages
from whatsapp_sender import WhatsAppSender
from scheduler import DealScheduler

def main():
    parser = argparse.ArgumentParser(description='PromoPet Hunter')
    parser.add_argument('--terms', nargs='+', default=config.DEFAULT_SEARCH_TERMS)
    parser.add_argument('--stores', nargs='+', default=['mercadolivre', 'amazon'])
    parser.add_argument('--group', default=config.DEFAULT_WHATSAPP_GROUP)
    parser.add_argument('--test-group', action='store_true')
    parser.add_argument('--test-amazon', action='store_true')
    parser.add_argument('--test-meli', action='store_true')
    parser.add_argument('--schedule', action='store_true')
    parser.add_argument('--login-whatsapp', action='store_true')
    args = parser.parse_args()

    if args.login_whatsapp:
        WhatsAppSender().setup_session()
        return

    if args.test_amazon:
        DealScheduler(group_name=args.group).run_single_test(target_store='amazon')
        return

    if args.test_meli:
        DealScheduler(group_name=args.group).run_single_test(target_store='mercadolivre')
        return

    if args.test_group:
        DealScheduler(group_name=args.group).run_single_test()
        return

    if args.schedule:
        DealScheduler(group_name=args.group).start_day_schedule()
        return

if __name__ == '__main__':
    main()
