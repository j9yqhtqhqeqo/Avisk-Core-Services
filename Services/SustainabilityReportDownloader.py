"""
Sustainability Report Downloader for S&P 500 Companies

This module downloads sustainability/ESG reports from S&P 500 company websites.
It searches for common sustainability report patterns and downloads PDF files.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from io import StringIO, BytesIO
import logging
from typing import List, Dict, Optional, Tuple

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    from Utilities.Lookups import DB_Connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

try:
    from Utilities.PathConfiguration import PathConfiguration
    PATH_CONFIG_AVAILABLE = True
except ImportError:
    PATH_CONFIG_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SustainabilityReportDownloader:
    """
    Downloads sustainability reports for S&P 500 companies.

    Features:
    - Loads S&P 500 company list
    - Searches company websites for sustainability reports
    - Downloads PDF reports with metadata
    - Tracks download progress and errors
    """

    # Common keywords for sustainability reports
    SUSTAINABILITY_KEYWORDS = [
        'sustainability',
        'esg',
        'corporate-responsibility',
        'environmental',
        'social-responsibility',
        'citizenship',
        'impact-report',
        'annual-report',
        'csr'
    ]

    # Common file patterns - expanded to catch more variations
    REPORT_PATTERNS = [
        r'sustainability.*report',
        r'sustainability',
        r'esg.*report',
        r'esg',
        r'corporate.*responsibility',
        r'environmental.*social.*governance',
        r'environmental.*progress.*report',
        r'environmental.*responsibility',
        r'environmental.*report',
        r'impact.*report',
        r'csr.*report',
        r'climate.*report',
        r'carbon.*report',
        r'progress.*report',
        r'responsibility.*report',
    ]

    # Known company website mappings (symbol -> domain)
    COMPANY_WEBSITES = {
        'AAPL': 'apple.com',
        'MSFT': 'microsoft.com',
        'GOOGL': 'google.com',
        'GOOG': 'google.com',
        'AMZN': 'amazon.com',
        'META': 'meta.com',
        'NVDA': 'nvidia.com',
        'TSLA': 'tesla.com',
        'JPM': 'jpmorganchase.com',
        'V': 'visa.com',
        'JNJ': 'jnj.com',
        'WMT': 'walmart.com',
        'MA': 'mastercard.com',
        'PG': 'pg.com',
        'XOM': 'exxonmobil.com',
        'UNH': 'unitedhealthgroup.com',
        'HD': 'homedepot.com',
        'CVX': 'chevron.com',
        'KO': 'coca-colacompany.com',
        'PFE': 'pfizer.com',
        'ABBV': 'abbvie.com',
        'MRK': 'merck.com',
        'COST': 'costco.com',
        'PEP': 'pepsico.com',
        'TMO': 'thermofisher.com',
        'AVGO': 'broadcom.com',
        'MCD': 'mcdonalds.com',
        'CSCO': 'cisco.com',
        'ABT': 'abbott.com',
        'ACN': 'accenture.com',
        'WFC': 'wellsfargo.com',
        'CRM': 'salesforce.com',
        'DHR': 'danaher.com',
        'BAC': 'bankofamerica.com',
        'LIN': 'linde.com',
        'AMD': 'amd.com',
        'INTC': 'intel.com',
        'TXN': 'ti.com',
        'NKE': 'nike.com',
        'ORCL': 'oracle.com',
        'UPS': 'ups.com',
        'BMY': 'bms.com',
        'QCOM': 'qualcomm.com',
        'RTX': 'rtx.com',
        'NEE': 'nexteraenergy.com',
        'PM': 'pmi.com',
        'UNP': 'up.com',
        'IBM': 'ibm.com',
        'GE': 'ge.com',
        'CAT': 'caterpillar.com',
        'BA': 'boeing.com',
        'DE': 'deere.com',
        'SPGI': 'spglobal.com',
        'AXP': 'americanexpress.com',
        'HON': 'honeywell.com',
        'AMGN': 'amgen.com',
        'GS': 'goldmansachs.com',
        'ISRG': 'intuitive.com',
        'BKNG': 'booking.com',
        'MDLZ': 'mondelezinternational.com',
        'GILD': 'gilead.com',
        'BLK': 'blackrock.com',
        'SYK': 'stryker.com',
        'ADI': 'analog.com',
        'VRTX': 'vrtx.com',
        'ADP': 'adp.com',
        'MMC': 'mmc.com',
        'TJX': 'tjx.com',
        'MMM': '3m.com',
        'CVS': 'cvshealth.com',
        'SCHW': 'schwab.com',
        'LRCX': 'lamresearch.com',
        'C': 'citigroup.com',
        'REGN': 'regeneron.com',
        'CB': 'chubb.com',
        'PLD': 'prologis.com',
        'ZTS': 'zoetis.com',
        'EOG': 'eogresources.com',
        'MO': 'altria.com',
        'SO': 'southerncompany.com',
        'CI': 'cigna.com',
        'DUK': 'duke-energy.com',
        'CME': 'cmegroup.com',
        'SNPS': 'synopsys.com',
        'CL': 'colgatepalmolive.com',
        'ICE': 'ice.com',
        'EQIX': 'equinix.com',
        'NOC': 'northropgrumman.com',
        'BDX': 'bd.com',
        'ITW': 'itw.com',
        'WM': 'wm.com',
        'SHW': 'sherwin-williams.com',
        'AON': 'aon.com',
        'CDNS': 'cadence.com',
        'APD': 'airproducts.com',
        'MPC': 'marathonpetroleum.com',
        'FDX': 'fedex.com',
        'USB': 'usbank.com',
        'ETN': 'eaton.com',
        'EMR': 'emerson.com',
        'PSX': 'phillips66.com',
        'KLAC': 'kla.com',
        'MCO': 'moodys.com',
        'MRNA': 'modernatx.com',
        'ORLY': 'oreillyauto.com',
        'AEP': 'aep.com',
        'D': 'dominionenergy.com',
        'GD': 'gd.com',
        'CTAS': 'cintas.com',
        'ADSK': 'autodesk.com',
        'SLB': 'slb.com',
        'HCA': 'hcahealthcare.com',
        'ROP': 'rfroper.com',
        'PCAR': 'paccar.com',
        'F': 'ford.com',
        'GM': 'gm.com',
        'VLO': 'valero.com',
        'AIG': 'aig.com',
        'MET': 'metlife.com',
        'TRV': 'travelers.com',
        'COP': 'conocophillips.com',
        'HUM': 'humana.com',
        'AZO': 'autozone.com',
        'MSCI': 'msci.com',
        'EW': 'edwards.com',
        'A': 'agilent.com',
        'ECL': 'ecolab.com',
        'AFL': 'aflac.com',
        'ALL': 'allstate.com',
        'PRU': 'prudential.com',
        'STZ': 'cbrands.com',
        'MAR': 'marriott.com',
        'WELL': 'welltower.com',
        'GIS': 'generalmills.com',
        'HES': 'hess.com',
        'DG': 'dollargeneral.com',
        'DLTR': 'dollartree.com',
        'KMB': 'kimberly-clark.com',
        'O': 'realtyincome.com',
        'SPG': 'simon.com',
        'EXC': 'exeloncorp.com',
        'PEG': 'pseg.com',
        'XEL': 'xcelenergy.com',
        'ED': 'coned.com',
        'WEC': 'wecenergygroup.com',
        'DTE': 'dteenergy.com',
        'ES': 'eversource.com',
        'AES': 'aes.com',
        'PPL': 'pplweb.com',
        'EIX': 'edison.com',
        'AEE': 'ameren.com',
        'LNT': 'alliantenergy.com',
        'CMS': 'cmsenergy.com',
        'EVRG': 'evergy.com',
        'NI': 'nisource.com',
        'PNW': 'pinnaclewest.com',
    }

    # Companies with special sustainability report page URLs
    # These companies host reports on non-standard pages
    CUSTOM_SUSTAINABILITY_PAGES = {
        # Top Tech
        'NVDA': [
            'https://www.nvidia.com/en-us/csr/',
            'https://www.nvidia.com/en-us/sustainability/',
        ],
        'MSFT': [
            'https://www.microsoft.com/en-us/corporate-responsibility/reports-hub',
            'https://www.microsoft.com/en-us/corporate-responsibility/sustainability/report',
        ],
        'AAPL': [
            'https://www.apple.com/environment/',
            'https://www.apple.com/environment/reports/',
        ],
        'GOOGL': [
            'https://sustainability.google/reports/',
        ],
        'GOOG': [
            'https://sustainability.google/reports/',
        ],
        'AMZN': [
            'https://sustainability.aboutamazon.com/',
            'https://sustainability.aboutamazon.com/reporting',
        ],
        'META': [
            'https://sustainability.fb.com/',
            'https://sustainability.fb.com/reports/',
        ],
        'TSLA': [
            'https://www.tesla.com/impact',
            'https://www.tesla.com/impact-report',
        ],
        # Financial Services
        'JPM': [
            'https://www.jpmorganchase.com/about/governance/esg',
            'https://www.jpmorganchase.com/impact/environmental-sustainability',
        ],
        'V': [
            'https://usa.visa.com/about-visa/esg.html',
            'https://corporate.visa.com/en/esg.html',
        ],
        'MA': [
            'https://www.mastercard.us/en-us/vision/corp-responsibility.html',
        ],
        'BAC': [
            'https://about.bankofamerica.com/en/making-an-impact/esg-reporting',
        ],
        'WFC': [
            'https://www.wellsfargo.com/about/corporate-responsibility/',
        ],
        'GS': [
            'https://www.goldmansachs.com/our-firm/sustainability/',
        ],
        'MS': [
            'https://www.morganstanley.com/about-us-governance/sustainability-at-morgan-stanley',
        ],
        'C': [
            'https://www.citigroup.com/global/our-impact/sustainability',
        ],
        # Healthcare
        'LLY': [
            'https://www.lilly.com/impact',
            'https://esg.lilly.com/',
        ],
        'JNJ': [
            'https://www.jnj.com/about-jnj/environmental-social-governance-esg',
        ],
        'UNH': [
            'https://www.unitedhealthgroup.com/what-we-do/sustainability.html',
        ],
        'ABBV': [
            'https://www.abbvie.com/our-impact/environmental-social-governance.html',
        ],
        'MRK': [
            'https://www.merck.com/company-overview/esg/',
        ],
        'TMO': [
            'https://corporate.thermofisher.com/us/en/index/corporate-social-responsibility.html',
        ],
        'ABT': [
            'https://www.abbott.com/responsibility/sustainability.html',
        ],
        'AMGN': [
            'https://www.amgen.com/responsibility',
        ],
        # Energy
        'XOM': [
            'https://corporate.exxonmobil.com/sustainability-report',
        ],
        'CVX': [
            'https://www.chevron.com/sustainability',
        ],
        # Consumer
        'COST': [
            'https://www.costco.com/sustainability.html',
        ],
        'HD': [
            'https://corporate.homedepot.com/responsibility',
        ],
        'PG': [
            'https://us.pg.com/sustainability-reports/',
        ],
        'KO': [
            'https://www.coca-colacompany.com/sustainability',
        ],
        'PEP': [
            'https://www.pepsico.com/our-impact/sustainability',
        ],
        'MCD': [
            'https://corporate.mcdonalds.com/corpmcd/our-purpose-and-impact.html',
        ],
        'DIS': [
            'https://thewaltdisneycompany.com/csr/',
        ],
        'NFLX': [
            'https://about.netflix.com/en/sustainability',
        ],
        # Technology & Communications
        'ORCL': [
            'https://www.oracle.com/corporate/citizenship/',
        ],
        'IBM': [
            'https://www.ibm.com/impact/environment/',
        ],
        'CSCO': [
            'https://www.cisco.com/c/m/en_us/about/csr/esg-hub/report.html',
        ],
        'CRM': [
            'https://www.salesforce.com/company/stakeholder-impact-report/',
        ],
        'INTC': [
            'https://www.intel.com/content/www/us/en/corporate-responsibility/corporate-responsibility.html',
        ],
        'AMD': [
            'https://www.amd.com/en/corporate-responsibility.html',
        ],
        'T': [
            'https://about.att.com/csr/home.html',
        ],
        'VZ': [
            'https://www.verizon.com/about/responsibility/',
        ],
        # Industrials
        'CAT': [
            'https://www.caterpillar.com/en/company/sustainability.html',
        ],
        'BA': [
            'https://www.boeing.com/principles/sustainability',
        ],
        'GE': [
            'https://www.ge.com/sustainability',
        ],
        'RTX': [
            'https://www.rtx.com/our-responsibility/sustainability',
        ],
        'LIN': [
            'https://www.linde.com/about-linde/sustainability',
        ],
        'PM': [
            'https://www.pmi.com/sustainability',
        ],
        # Semiconductor Equipment
        'LRCX': [
            'https://www.lamresearch.com/company/esg-impact/',
        ],
        'KLAC': [
            'https://www.kla-tencor.com/company/corporate-responsibility',
        ],
        'AMAT': [
            'https://www.appliedmaterials.com/company/corporate-responsibility',
        ],
        'MU': [
            'https://www.micron.com/about/sustainability',
        ],
        # Additional top companies
        'GILD': [
            'https://www.gilead.com/purpose/esg',
        ],
        'AXP': [
            'https://about.americanexpress.com/corporate-sustainability',
        ],
        'NEE': [
            'https://www.nexteraenergy.com/sustainability.html',
        ],
        'HON': [
            'https://www.honeywell.com/us/en/company/sustainability',
        ],
        'LOW': [
            'https://corporate.lowes.com/our-responsibilities',
        ],
        'BLK': [
            'https://www.blackrock.com/corporate/sustainability',
        ],
        'SPGI': [
            'https://www.spglobal.com/en/who-we-are/corporate-responsibility',
        ],
    }

    # Direct PDF URL patterns for major companies
    # Format: symbol -> {year -> [list of PDF URLs]}
    # Use {year} as placeholder for the year
    KNOWN_REPORT_URL_PATTERNS = {
        # Top Tech Companies
        'NVDA': [
            'https://images.nvidia.com/aem-dam/Solutions/documents/NVIDIA-Sustainability-Report-Fiscal-Year-{year}.pdf',
            'https://images.nvidia.com/aem-dam/Solutions/documents/FY{year}-NVIDIA-Corporate-Responsibility-Report.pdf',
            # NVIDIA uses fiscal years - FY25 = calendar 2024
        ],
        'GOOG': [
            'https://www.gstatic.com/gumdrop/sustainability/google-{year}-environmental-report.pdf',
            'https://www.gstatic.com/gumdrop/sustainability/google-{year}-supplier-responsibility-report.pdf',
            'https://www.gstatic.com/gumdrop/sustainability/{year}-google-statement-against-modern-slavery.pdf',
            'https://www.gstatic.com/gumdrop/sustainability/alphabet-{year}-cdp-climate-change-response.pdf',
        ],
        'GOOGL': [
            'https://www.gstatic.com/gumdrop/sustainability/google-{year}-environmental-report.pdf',
            'https://www.gstatic.com/gumdrop/sustainability/google-{year}-supplier-responsibility-report.pdf',
            'https://www.gstatic.com/gumdrop/sustainability/{year}-google-statement-against-modern-slavery.pdf',
            'https://www.gstatic.com/gumdrop/sustainability/alphabet-{year}-cdp-climate-change-response.pdf',
        ],
        'AMZN': [
            'https://sustainability.aboutamazon.com/{year}-amazon-sustainability-report.pdf',
            'https://sustainability.aboutamazon.com/{year}-sustainability-executive-summary.pdf',
            'https://sustainability.aboutamazon.com/{year}-amazon-sustainability-report-aws-summary.pdf',
            'https://sustainability.aboutamazon.com/{year}-sustainability-reporting-framework-summary.pdf',
        ],
        'MSFT': [
            'https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RE5b38N',  # 2024 report
            'https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RE4RwfV',  # 2023 report
        ],
        'AAPL': [
            'https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_{year}.pdf',
            'https://www.apple.com/environment/pdf/Apple_CDP-Climate-Change-Questionnaire_{year}.pdf',
        ],
        'META': [
            'https://sustainability.fb.com/wp-content/uploads/{year}/07/Meta-{year}-Sustainability-Report.pdf',
        ],
        'TSLA': [
            'https://www.tesla.com/ns_videos/Tesla-Impact-Report-{year}.pdf',
            'https://www.tesla.com/ns_videos/{year}-tesla-impact-report.pdf',
        ],
        # Financial Services
        'JPM': [
            'https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/documents/{year}-esg-report.pdf',
            'https://www.jpmorganchase.com/content/dam/jpmc/jpmorgan-chase-and-co/documents/jpmc-{year}-annual-report.pdf',
        ],
        'V': [
            'https://usa.visa.com/content/dam/VCOM/regional/na/us/about-visa/documents/visa-{year}-esg-report.pdf',
        ],
        'MA': [
            'https://www.mastercard.com/content/dam/public/mastercardcom/na/global-site/documents/mastercard-{year}-sustainability-report.pdf',
        ],
        'BAC': [
            'https://about.bankofamerica.com/content/dam/about/report-center/{year}/Bank-of-America-{year}-Annual-Report.pdf',
        ],
        'WFC': [
            'https://www08.wellsfargomedia.com/assets/pdf/about/corporate-responsibility/environmental-social-governance-report-{year}.pdf',
        ],
        'GS': [
            'https://www.goldmansachs.com/a/pgs/sustainability-report-{year}.pdf',
        ],
        'MS': [
            'https://www.morganstanley.com/content/dam/msdotcom/sustainability/{year}-sustainability-report.pdf',
            'https://www.morganstanley.com/content/dam/msdotcom/en/assets/pdfs/Morgan_Stanley_{year}_Sustainability_Report.pdf',
        ],
        'C': [
            'https://www.citigroup.com/global/assets/pdf/citi-{year}-esg-report.pdf',
        ],
        # Healthcare
        'LLY': [
            'https://esg.lilly.com/_assets/pdf/lilly-{year}-esg-report.pdf',
        ],
        'JNJ': [
            'https://www.jnj.com/sites/default/files/{year}-health-for-humanity-report.pdf',
        ],
        'UNH': [
            'https://www.unitedhealthgroup.com/content/dam/UHG/{year}/sustainability-report-{year}.pdf',
        ],
        'ABBV': [
            'https://www.abbvie.com/content/dam/abbvie-dotcom/uploads/PDFs/{year}-abbvie-esg-report.pdf',
        ],
        'MRK': [
            'https://www.merck.com/assets/pdfs/{year}-esg-progress-report.pdf',
            'https://www.merck.com/wp-content/uploads/sites/124/2025/08/PurposeforProgressMerckImpactReport{year}-2025.pdf',
        ],
        'TMO': [
            'https://corporate.thermofisher.com/content/dam/tfcorpsite/documents/csr-report/{year}-corporate-social-responsibility-report.pdf',
        ],
        'ABT': [
            'https://www.abbott.com/content/dam/corp/abbott/en-us/documents/pdfs/{year}-global-sustainability-report.pdf',
        ],
        'AMGN': [
            'https://www.amgen.com/-/media/amgen/full/www-amgen-com/downloads/responsibility/{year}-amgen-esg-report.pdf',
        ],
        # Energy
        'XOM': [
            'https://corporate.exxonmobil.com/-/media/Global/Files/sustainability-report/publication/{year}-sustainability-report.pdf',
        ],
        'CVX': [
            'https://www.chevron.com/-/media/chevron/sustainability/documents/{year}-corporate-sustainability-report.pdf',
        ],
        # Consumer
        'COST': [
            'https://www.costco.com/wcsstore/CostcoUSBCCatalogAssetStore/sustainability-reports/{year}-sustainability-report.pdf',
        ],
        'HD': [
            'https://ir.homedepot.com/~/media/Files/H/HomeDepot-IR/documents/governance/{year}-esg-report.pdf',
        ],
        'PG': [
            'https://us.pg.com/-/media/PGCOMUS/Documents/PDF/Sustainability_Reports/PG-Citizenship-Report-{year}.pdf',
        ],
        'KO': [
            'https://www.coca-colacompany.com/content/dam/company/us/en/reports/{year}-business-environmental-social-governance-report.pdf',
            'https://www.coca-colacompany.com/content/dam/company/us/en/reports/{year}-environmental-update/{year}-environmental-update.pdf',
        ],
        'PEP': [
            'https://www.pepsico.com/docs/default-source/sustainability-and-esg-topics/pepsico-{year}-esg-summary.pdf',
            'https://www.pepsico.com/docs/pepsico-5v9wci20/media/Files/esg-topics/{year}-pepsico-modern-slavery-and-human-trafficking-statement.pdf',
        ],
        'MCD': [
            'https://corporate.mcdonalds.com/content/dam/gwscorp/assets/sustainability/{year}-purpose-impact-report.pdf',
        ],
        'DIS': [
            'https://thewaltdisneycompany.com/app/uploads/{year}/disney-{year}-csr-report.pdf',
        ],
        'NFLX': [
            'https://s22.q4cdn.com/959853165/files/doc_downloads/ESG/{year}/Netflix-Environmental-Social-Governance-{year}-Report.pdf',
        ],
        # Technology & Communications
        'ORCL': [
            'https://www.oracle.com/a/ocom/docs/corporate/citizenship/oracle-{year}-corporate-citizenship-report.pdf',
        ],
        'IBM': [
            'https://www.ibm.com/ibm/environment/annual/{year}-ibm-corporate-environmental-report.pdf',
        ],
        'CSCO': [
            'https://www.cisco.com/c/dam/m/en_us/about/csr/esg-hub/_pdf/{year}-cisco-purpose-report.pdf',
        ],
        'CRM': [
            'https://www.salesforce.com/content/dam/web/en_us/www/documents/reports/sustainability/salesforce-{year}-stakeholder-impact-report.pdf',
        ],
        'INTC': [
            'https://csrreportbuilder.intel.com/pdfbuilder/pdfs/CSR-{year}-Full-Report.pdf',
        ],
        'AMD': [
            'https://www.amd.com/content/dam/amd/en/documents/corporate/cr/{year}-corporate-responsibility-summary.pdf',
        ],
        'T': [
            'https://about.att.com/content/dam/csr/PDFs/ATT{year}ESGSummary.pdf',
        ],
        'VZ': [
            'https://www.verizon.com/about/sites/default/files/Verizon-{year}-ESG-Report.pdf',
        ],
        # Industrials
        'CAT': [
            'https://www.caterpillar.com/en/company/sustainability/sustainability-report/current-report/{year}-sustainability-report.pdf',
        ],
        'BA': [
            'https://www.boeing.com/content/dam/boeing/boeingdotcom/principles/sustainability/{year}_boeing_sustainability_report.pdf',
        ],
        'GE': [
            'https://www.ge.com/sites/default/files/{year}-ge-aerospace-sustainability-report.pdf',
        ],
        'RTX': [
            'https://www.rtx.com/-/media/rtx/sustainability/pdf/{year}-esg-report.pdf',
        ],
        'LIN': [
            'https://www.linde.com/-/media/linde/sustainability/documents/{year}-sustainable-development-report.pdf',
        ],
        'PM': [
            'https://www.pmi.com/resources/docs/default-source/sustainability-reports-and-publications/pmi-integrated-report-{year}.pdf',
        ],
        # Semiconductor Equipment (verified working)
        'LRCX': [
            'https://www.lamresearch.com/wp-content/uploads/2025/07/Lam-Research-{year}-Global-Impact-Report.pdf',
        ],
        'KLAC': [
            'https://www.kla-tencor.com/wp-content/uploads/{year}-KLA-Global-Impact-Report.pdf',
        ],
        'AMAT': [
            'https://www.appliedmaterials.com/content/dam/site/company/csr/{year}-sustainability-report.pdf',
        ],
        'MU': [
            'https://www.micron.com/-/media/client/global/documents/sustainability/{year}-sustainability-report.pdf',
        ],
        # Additional Top 100 Companies
        'GILD': [
            'https://www.gilead.com/-/media/files/pdfs/{year}-esg-report.pdf',
        ],
        'AXP': [
            'https://s29.q4cdn.com/330303330/files/doc_downloads/ESG/{year}/American-Express-{year}-ESG-Report.pdf',
        ],
        'TJX': [
            'https://www.tjx.com/docs/default-source/corporate-responsibility/{year}-tjx-corporate-responsibility-report.pdf',
        ],
        'ISRG': [
            'https://isrg.intuitive.com/static-files/{year}-sustainability-report.pdf',
        ],
        'APH': [
            'https://www.amphenol.com/sites/default/files/{year}-sustainability-report.pdf',
        ],
        'NEE': [
            'https://www.nexteraenergy.com/content/dam/nee/us/en/pdf/{year}-environmental-social-governance-report.pdf',
        ],
        'HON': [
            'https://www.honeywell.com/content/dam/honeywell/files/ESG/{year}-sustainability-report.pdf',
        ],
        'LOW': [
            'https://corporate.lowes.com/sites/lowes-corp/files/2025-04/{year}-Lowes-Corporate-Responsibility-Report.pdf',
        ],
        'UNP': [
            'https://www.up.com/cs/groups/public/@uprr/@corprel/documents/up_pdf_nativedocs/{year}-building-america-report.pdf',
        ],
        'SPGI': [
            'https://www.spglobal.com/corporate-responsibility/pdfs/{year}-Corporate-Responsibility-Report.pdf',
        ],
        'BLK': [
            'https://www.blackrock.com/corporate/literature/continuous-disclosure-and-important-information/{year}-annual-sustainability-report.pdf',
        ],
        'ADP': [
            'https://www.adp.com/-/media/adp/resource-center/pdf/{year}-adp-esg-report.pdf',
        ],
        'BKNG': [
            'https://www.bookingholdings.com/wp-content/uploads/{year}/04/Booking-Holdings-{year}-Sustainability-Report.pdf',
        ],
        'SYK': [
            'https://www.stryker.com/content/dam/stryker/about/sustainability/{year}-sustainability-report.pdf',
        ],
        'MDLZ': [
            'https://www.mondelezinternational.com/-/media/Mondelez/Snacking-Made-Right/{year}-ESG-Report.pdf',
        ],
        'REGN': [
            'https://www.regeneron.com/downloads/{year}-sustainability-report.pdf',
        ],
        'VRTX': [
            'https://www.vrtx.com/sites/default/files/{year}-vertex-corporate-responsibility-report.pdf',
        ],
        'CME': [
            'https://www.cmegroup.com/content/dam/cmegroup/company/corporate-responsibility/{year}-cme-group-corporate-responsibility-report.pdf',
        ],
        'PLD': [
            'https://www.prologis.com/sites/default/files/{year}-ESG-Impact-Report.pdf',
        ],
        'CI': [
            'https://www.cigna.com/static/www-cigna-com/docs/{year}-corporate-responsibility-report.pdf',
        ],
        'WM': [
            'https://sustainability.wm.com/downloads/{year}-sustainability-report.pdf',
        ],
        'DE': [
            'https://www.deere.com/assets/pdfs/common/sustainability/{year}-sustainability-report.pdf',
        ],
        'MMC': [
            'https://www.mmc.com/content/dam/mmc-web/Files/ESG/{year}-ESG-Report.pdf',
        ],
    }

    def __init__(self, download_dir: Optional[str] = None,
                 delay_seconds: float = 2.0,
                 current_sector_id: Optional[int] = None,
                 use_storage: bool = True,
                 year_filter: Optional[List[int]] = None):
        """
        Initialize the downloader.

        Args:
            download_dir: Directory to save downloaded reports (overrides PathConfiguration)
            delay_seconds: Delay between requests to be respectful to servers
            current_sector_id: The current sector ID being processed (e.g., 1007)
            use_storage: If True, use PathConfiguration for Stage0SourcePDFFiles path
            year_filter: List of years to download (e.g., [2024, 2023]). If None, download all years.
        """
        # Initialize PathConfiguration for storage paths
        self.path_config = None
        self.use_storage = use_storage

        if use_storage and PATH_CONFIG_AVAILABLE:
            self.path_config = PathConfiguration()
            self.base_download_dir = Path(
                self.path_config.get_stage0_input_path())
            logger.info(f"Using storage path: {self.base_download_dir}")
        elif download_dir:
            self.base_download_dir = Path(download_dir)
        else:
            self.base_download_dir = Path('./sustainability_reports')

        self.base_download_dir.mkdir(parents=True, exist_ok=True)
        # Keep download_dir for backward compatibility (cache files, etc.)
        self.download_dir = self.base_download_dir

        # Separate cache directory for progress files (not in PDF storage)
        self.cache_dir = Path('./sustainability_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.delay_seconds = delay_seconds
        self.current_sector_id = current_sector_id
        self.year_filter = year_filter  # List of years to download, or None for all

        # Track progress
        self.downloaded_reports = []
        self.failed_downloads = []

        # Track companies already checked in t_sec_company (to avoid repeated lookups)
        self._checked_companies = set()

        # Database connection (optional)
        self.db_connection = None
        self._init_db_connection()

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def _init_db_connection(self):
        """Initialize database connection if available."""
        if not DB_AVAILABLE:
            logger.warning(
                "Database modules not available - downloads will not be recorded to t_data_source")
            return

        try:
            connection_string = DB_Connection().DB_CONNECTION_STRING
            self.db_connection = psycopg2.connect(connection_string)
            logger.info(
                "Database connection established for tracking downloads")
        except Exception as e:
            logger.warning(
                f"Could not connect to database: {e} - downloads will not be recorded to t_data_source")
            self.db_connection = None

    def _get_next_company_id(self) -> int:
        """
        Get the next available company_id from t_sec_company.

        Returns:
            Next company_id (max + 1) or 1 if table is empty
        """
        if not self.db_connection:
            return 1

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(company_id), 0) + 1 FROM t_sec_company")
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else 1
        except Exception as e:
            logger.error(f"Failed to get next company_id: {e}")
            return 1

    def _company_exists(self, company_name: str) -> Optional[int]:
        """
        Check if a company already exists in t_sec_company.

        Args:
            company_name: Name of the company to check

        Returns:
            company_id if exists, None otherwise
        """
        if not self.db_connection:
            return None

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT company_id FROM t_sec_company WHERE conformed_name = %s LIMIT 1",
                (company_name,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to check if company exists: {e}")
            return None

    def _get_sector_id(self) -> Optional[int]:
        """
        Look up sector_id from t_data_lookups using the current sector ID.

        Returns:
            sector_id from t_data_lookups, or None if not found
        """
        if not self.db_connection or not self.current_sector_id:
            return None

        try:
            cursor = self.db_connection.cursor()
            # Self-join to find matching sector_id based on description
            cursor.execute("""
                SELECT b.data_lookups_id 
                FROM t_data_lookups a
                INNER JOIN t_data_lookups b ON a.data_lookups_description = b.data_lookups_description 
                WHERE a.data_lookups_id = %s 
                  AND b.data_lookups_id != %s
            """, (self.current_sector_id, self.current_sector_id))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(
                f"Failed to get sector_id for current_sector_id {self.current_sector_id}: {e}")
            return None

    def _sector_mapping_exists(self, company_id: int) -> bool:
        """
        Check if a company-sector mapping already exists.

        Args:
            company_id: The company_id to check

        Returns:
            True if mapping exists, False otherwise
        """
        if not self.db_connection:
            return False

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "SELECT 1 FROM t_sec_company_sector_map WHERE company_id = %s LIMIT 1",
                (company_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check sector mapping: {e}")
            return False

    def _ensure_sector_mapping(self, company_id: int, company_name: str, sector_id: int) -> bool:
        """
        Ensure company-sector mapping exists in t_sec_company_sector_map.

        Args:
            company_id: The company_id from t_sec_company
            company_name: Name of the company
            sector_id: The sector_id from t_data_lookups

        Returns:
            True if mapping exists or was created, False on error
        """
        if not self.db_connection:
            return False

        try:
            # Check if mapping already exists
            if self._sector_mapping_exists(company_id):
                logger.debug(
                    f"Sector mapping already exists for company_id {company_id}")
                return True

            cursor = self.db_connection.cursor()
            insert_sql = """
                INSERT INTO t_sec_company_sector_map (
                    company_id, company_name, sector_id,
                    added_dt, added_by, modify_dt, modify_by
                )
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s)
            """

            cursor.execute(insert_sql, (
                company_id,
                company_name,
                sector_id,
                'SustainabilityReportDownloader',
                'SustainabilityReportDownloader'
            ))

            self.db_connection.commit()
            cursor.close()

            logger.info(
                f"Added sector mapping for '{company_name}' (company_id: {company_id}, sector_id: {sector_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure sector mapping: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False

    def _ensure_company_exists(self, company_name: str) -> Optional[int]:
        """
        Ensure company exists in t_sec_company, inserting if necessary.
        Also ensures sector mapping exists in t_sec_company_sector_map.
        Only checks once per company per session.

        Args:
            company_name: Name of the company

        Returns:
            company_id if company exists or was inserted, None on error
        """
        if not self.db_connection:
            return None

        # Skip if already checked this company
        if company_name in self._checked_companies:
            # Return existing company_id
            return self._company_exists(company_name)

        try:
            # Check if company exists
            existing_id = self._company_exists(company_name)
            if existing_id:
                logger.info(
                    f"Company '{company_name}' already exists in t_sec_company (id: {existing_id})")
                self._checked_companies.add(company_name)
                # Ensure sector mapping exists if current_sector_id is set
                if self.current_sector_id:
                    sector_id = self._get_sector_id()
                    if sector_id:
                        self._ensure_sector_mapping(
                            existing_id, company_name, sector_id)
                return existing_id

            # Insert new company with placeholder values
            next_id = self._get_next_company_id()
            cursor = self.db_connection.cursor()

            insert_sql = """
                INSERT INTO t_sec_company (
                    company_id, reporting_year, conformed_name, sic_code, sic_code_4_digit,
                    irs_number, state_of_incorporation, street_1, city, state, zip,
                    added_dt, added_by, modify_dt, modify_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s)
            """

            cursor.execute(insert_sql, (
                next_id,
                0,  # reporting_year placeholder
                company_name,
                '9999',  # sic_code placeholder
                9999,  # sic_code_4_digit placeholder
                9999,  # irs_number placeholder
                'PH',  # state_of_incorporation placeholder
                'PlaceHolder',  # street_1 placeholder
                'PlaceHolder',  # city placeholder
                'PH',  # state placeholder
                '9999',  # zip placeholder
                'SustainabilityReportDownloader',
                'SustainabilityReportDownloader'
            ))

            self.db_connection.commit()
            cursor.close()

            logger.info(
                f"Added company '{company_name}' to t_sec_company (id: {next_id})")
            self._checked_companies.add(company_name)

            # Add sector mapping if current_sector_id is set
            if self.current_sector_id:
                sector_id = self._get_sector_id()
                if sector_id:
                    self._ensure_sector_mapping(
                        next_id, company_name, sector_id)
                else:
                    logger.warning(
                        f"Could not find sector_id for current_sector_id {self.current_sector_id}")

            return next_id

        except Exception as e:
            logger.error(f"Failed to ensure company exists: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False

    def _data_source_exists(self, company_name: str, year: int, document_name: str) -> Optional[int]:
        """
        Check if a data source entry already exists.

        Args:
            company_name: Name of the company
            year: Year of the report
            document_name: Name of the document file

        Returns:
            unique_id if exists, None otherwise
        """
        if not self.db_connection:
            return None

        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                """SELECT unique_id FROM t_data_source 
                   WHERE company_name = %s AND year = %s AND source_url = %s 
                   LIMIT 1""",
                (company_name, year, document_name)
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to check if data source exists: {e}")
            return None

    def _is_url_in_database(self, url: str, company_name: str) -> bool:
        """
        Check if a URL has already been tracked in the database.
        Only checks database - NOT file system. This allows re-registering
        existing files that are missing from the database.

        Args:
            url: The download URL
            company_name: Name of the company

        Returns:
            True if already in database, False otherwise
        """
        if not self.db_connection:
            return False

        # Extract filename and year from URL for checking
        url_path = urlparse(url).path
        original_filename = os.path.basename(url_path)

        # Extract year from URL
        year_match = re.search(r'20\d{2}', url)
        if not year_match:
            return False  # Can't determine year, proceed with download

        year_str = year_match.group()

        # Build expected filename
        if not (original_filename and original_filename.lower().endswith('.pdf')):
            return False  # Can't determine filename, proceed with download

        try:
            cursor = self.db_connection.cursor()
            # Check if any entry exists with this filename pattern
            cursor.execute(
                """SELECT unique_id FROM t_data_source 
                   WHERE company_name = %s AND year = %s 
                   AND source_url LIKE %s
                   LIMIT 1""",
                (company_name, int(year_str),
                 f"%{original_filename[:-4]}%")
            )
            result = cursor.fetchone()
            cursor.close()
            if result:
                logger.info(
                    f"Skipping {url} - already in database (id: {result[0]})")
                return True
        except Exception as e:
            logger.debug(f"Database check failed: {e}")

        return False

    def _add_to_data_source(self, company_name: str, year: int, source_url: str,
                            document_name: str, filepath: str) -> Optional[int]:
        """
        Add a downloaded report entry to t_data_source table.

        Args:
            company_name: Name of the company
            year: Year of the report
            source_url: URL where the report was downloaded from
            document_name: Name of the document file
            filepath: Local file path where document is saved

        Returns:
            unique_id of the inserted record, or None if failed/already exists
        """
        if not self.db_connection:
            return None

        # Check if entry already exists
        existing_id = self._data_source_exists(
            company_name, year, document_name)
        if existing_id:
            logger.info(
                f"Data source already exists for {document_name} (id: {existing_id}) - skipping insert")
            return existing_id

        # Ensure company exists in t_sec_company first (with sector mapping)
        self._ensure_company_exists(company_name)

        try:
            cursor = self.db_connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor)

            # content_type 1 = Sustainability Report
            # source_type = 'file' for downloaded files
            insert_sql = """
                INSERT INTO t_data_source 
                (company_name, year, content_type, source_type, source_url, 
                 processed_ind, added_dt, added_by, modify_dt, modify_by)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, CURRENT_TIMESTAMP, %s)
                RETURNING unique_id
            """

            cursor.execute(insert_sql, (
                company_name,
                int(year),
                1,  # content_type: Sustainability Report
                'file',  # source_type: file
                document_name,  # source_url stores the filename
                0,  # processed_ind: Not yet processed
                'SustainabilityReportDownloader',
                'SustainabilityReportDownloader'
            ))

            result = cursor.fetchone()
            unique_id = result['unique_id'] if result else None

            self.db_connection.commit()
            cursor.close()

            logger.info(
                f"Added to t_data_source: {document_name} (id: {unique_id})")
            return unique_id

        except Exception as e:
            logger.error(f"Failed to add to t_data_source: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return None

    def _extract_year_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        """
        Extract year from PDF metadata or content.

        Args:
            pdf_content: Raw PDF file content as bytes

        Returns:
            Year string (e.g., '2024') or None if not found
        """
        if not PYMUPDF_AVAILABLE:
            return None

        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_content, filetype="pdf")

            # Try metadata first (creation date, modification date, title)
            metadata = doc.metadata
            if metadata:
                # Check creation date
                if metadata.get('creationDate'):
                    year_match = re.search(
                        r'20\d{2}', metadata['creationDate'])
                    if year_match:
                        doc.close()
                        return year_match.group()

                # Check modification date
                if metadata.get('modDate'):
                    year_match = re.search(r'20\d{2}', metadata['modDate'])
                    if year_match:
                        doc.close()
                        return year_match.group()

                # Check title
                if metadata.get('title'):
                    year_match = re.search(r'20\d{2}', metadata['title'])
                    if year_match:
                        doc.close()
                        return year_match.group()

            # If no year in metadata, check first page content
            if len(doc) > 0:
                first_page = doc[0]
                text = first_page.get_text()[:2000]  # First 2000 chars

                # Look for year patterns in context of reports
                # e.g., "2024 Report", "FY 2023", "Fiscal Year 2022"
                year_patterns = [
                    r'(?:FY|Fiscal Year|Annual Report|Report)\s*(20\d{2})',
                    r'(20\d{2})\s*(?:Annual|Report|Sustainability|ESG|Environmental)',
                    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(20\d{2})',
                    r'(20\d{2})'  # Fallback: any year
                ]

                for pattern in year_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        doc.close()
                        return match.group(1) if match.lastindex else match.group()

            doc.close()
            return None

        except Exception as e:
            logger.debug(f"Error extracting year from PDF: {e}")
            return None

    def get_company_website(self, symbol: str, company_name: str) -> Optional[str]:
        """
        Get the website URL for a company.

        Args:
            symbol: Stock symbol
            company_name: Company name

        Returns:
            Website URL or None if not found
        """
        # Check known mappings first
        if symbol in self.COMPANY_WEBSITES:
            return f"https://www.{self.COMPANY_WEBSITES[symbol]}"

        # Try to derive from company name
        # Clean the company name for URL generation
        clean_name = company_name.lower()

        # Remove common suffixes
        for suffix in [' inc.', ' inc', ' corp.', ' corp', ' corporation',
                       ' company', ' co.', ' co', ' ltd.', ' ltd', ' llc',
                       ' plc', ' n.v.', ' s.a.', ' ag', ' se', ' nv',
                       ' holdings', ' group', ' international', ' intl']:
            clean_name = clean_name.replace(suffix, '')

        # Remove special characters and spaces
        clean_name = re.sub(r'[^a-z0-9]', '', clean_name)

        if clean_name:
            return f"https://www.{clean_name}.com"

        return None

    def load_sp500_companies(self, csv_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load S&P 500 company list.

        Args:
            csv_path: Path to CSV file with company data. If None, fetches from Wikipedia.

        Returns:
            DataFrame with columns: Symbol, Company, Website
        """
        if csv_path and os.path.exists(csv_path):
            logger.info(f"Loading companies from {csv_path}")
            return pd.read_csv(csv_path)

        # Fetch from Wikipedia
        logger.info("Fetching S&P 500 list from Wikipedia")
        try:
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            # Use requests with proper headers to avoid 403 Forbidden
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            tables = pd.read_html(StringIO(response.text))
            df = tables[0]

            # Rename columns for consistency
            df = df.rename(columns={
                'Symbol': 'Symbol',
                'Security': 'Company',
                'GICS Sector': 'Sector'
            })

            # Save for future use
            cache_file = self.cache_dir / 'sp500_companies.csv'
            df.to_csv(cache_file, index=False)
            logger.info(f"Saved company list to {cache_file}")

            return df

        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            raise

    def search_company_website(self, company_name: str,
                               base_url: str, symbol: str = None) -> List[str]:
        """
        Search company website for sustainability report links.

        Args:
            company_name: Name of the company
            base_url: Base URL of company website
            symbol: Stock symbol (optional, for custom URL lookup)

        Returns:
            List of potential report URLs
        """
        potential_urls = []

        try:
            # Check for custom sustainability pages first (for companies like Microsoft, Apple, etc.)
            custom_pages = []
            if symbol and symbol in self.CUSTOM_SUSTAINABILITY_PAGES:
                custom_pages = self.CUSTOM_SUSTAINABILITY_PAGES[symbol]
                logger.info(
                    f"Using custom sustainability pages for {symbol}: {custom_pages}")

            # Try custom pages first
            for custom_url in custom_pages:
                try:
                    response = self.session.get(
                        custom_url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        logger.info(
                            f"Found custom sustainability page: {custom_url}")
                        soup = BeautifulSoup(response.content, 'html.parser')
                        pdf_links = self._extract_pdf_links(soup, custom_url)
                        potential_urls.extend(pdf_links)
                        logger.info(
                            f"Found {len(pdf_links)} PDFs on custom page {custom_url}")
                except requests.RequestException as e:
                    logger.debug(f"Custom page not found: {custom_url} - {e}")
                time.sleep(self.delay_seconds / 2)

            # Try common sustainability page patterns
            search_paths = [
                '',  # Homepage first
                '/sustainability',
                '/sustainability-report',
                '/sustainability-reports',
                '/sustainability/reports',
                '/esg',
                '/esg-report',
                '/esg-reports',
                '/esg/reports',
                '/corporate-responsibility',
                '/corporate-responsibility/reports',
                '/about/sustainability',
                '/about/esg',
                '/about/responsibility',
                '/investors/esg',
                '/investors/sustainability',
                '/investor-relations/esg',
                '/responsibility',
                '/responsibility/reports',
                '/impact',
                '/impact-report',
                '/our-impact',
                '/our-impact/reports',
                '/environment',
                '/environmental',
                '/csr',
                '/corporate-social-responsibility',
                '/governance/esg',
                '/citizenship',
                '/corporate-citizenship',
                '/social-impact',
                '/reports',
                '/annual-report',
                '/annual-reports',
                '/company/sustainability',
                '/who-we-are/sustainability',
                '/our-story/sustainability',
                '/about-us/sustainability',
            ]

            for path in search_paths:
                url = urljoin(base_url, path) if path else base_url
                try:
                    response = self.session.get(
                        url, timeout=15, allow_redirects=True)
                    if response.status_code == 200:
                        if path:
                            logger.info(f"Found sustainability page: {url}")
                        # Parse page for PDF links
                        soup = BeautifulSoup(response.content, 'html.parser')
                        pdf_links = self._extract_pdf_links(soup, url)
                        potential_urls.extend(pdf_links)

                        # Also look for links to sustainability pages
                        if not path:  # On homepage, look for sustainability links
                            for link in soup.find_all('a', href=True):
                                href = link['href'].lower()
                                text = link.get_text().lower()
                                if any(kw in href or kw in text for kw in ['sustainability', 'esg', 'impact', 'responsibility']):
                                    sub_url = urljoin(base_url, link['href'])
                                    if sub_url.startswith(base_url):
                                        try:
                                            sub_response = self.session.get(
                                                sub_url, timeout=15, allow_redirects=True)
                                            if sub_response.status_code == 200:
                                                sub_soup = BeautifulSoup(
                                                    sub_response.content, 'html.parser')
                                                sub_pdf_links = self._extract_pdf_links(
                                                    sub_soup, sub_url)
                                                potential_urls.extend(
                                                    sub_pdf_links)
                                                logger.info(
                                                    f"Found {len(sub_pdf_links)} PDFs on {sub_url}")
                                        except requests.RequestException:
                                            pass
                                        time.sleep(self.delay_seconds / 2)

                except requests.RequestException as e:
                    logger.debug(f"Path not found: {url} - {e}")
                    continue

                # Be respectful - add delay
                time.sleep(self.delay_seconds)

        except Exception as e:
            logger.error(f"Error searching {company_name} website: {e}")

        return list(set(potential_urls))  # Remove duplicates

    def search_duckduckgo(self, company_name: str, year: Optional[int] = None) -> List[str]:
        """
        Search DuckDuckGo for sustainability reports as a fallback.

        Args:
            company_name: Name of the company
            year: Optional year to filter results

        Returns:
            List of PDF URLs found
        """
        pdf_urls = []

        try:
            # Build search query
            year_str = str(year) if year else ""
            search_terms = [
                f'"{company_name}" sustainability report {year_str} filetype:pdf',
                f'"{company_name}" ESG report {year_str} filetype:pdf',
                f'"{company_name}" environmental report {year_str} filetype:pdf',
            ]

            for query in search_terms:
                try:
                    # Use DuckDuckGo HTML search (no API key needed)
                    encoded_query = requests.utils.quote(query)
                    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }

                    response = self.session.get(
                        url, headers=headers, timeout=15)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')

                        # Find result links
                        for result in soup.find_all('a', class_='result__a'):
                            href = result.get('href', '')
                            # DuckDuckGo wraps URLs, extract actual URL
                            if 'uddg=' in href:
                                # Extract the actual URL from DuckDuckGo's redirect
                                import urllib.parse
                                parsed = urllib.parse.parse_qs(
                                    urllib.parse.urlparse(href).query)
                                if 'uddg' in parsed:
                                    actual_url = parsed['uddg'][0]
                                    if actual_url.lower().endswith('.pdf'):
                                        pdf_urls.append(actual_url)
                                        logger.info(
                                            f"DuckDuckGo found PDF: {actual_url}")
                            elif href.lower().endswith('.pdf'):
                                pdf_urls.append(href)
                                logger.info(f"DuckDuckGo found PDF: {href}")

                        # Also check result snippets for PDF links
                        for result in soup.find_all('a', class_='result__url'):
                            href = result.get('href', '')
                            if href.lower().endswith('.pdf'):
                                pdf_urls.append(href)

                    time.sleep(self.delay_seconds)  # Be respectful

                except Exception as e:
                    logger.debug(f"DuckDuckGo search error for '{query}': {e}")
                    continue

            # Deduplicate and validate URLs
            pdf_urls = list(set(pdf_urls))
            logger.info(
                f"DuckDuckGo search for {company_name} found {len(pdf_urls)} PDFs")

        except Exception as e:
            logger.error(f"DuckDuckGo search failed for {company_name}: {e}")

        return pdf_urls

    def try_known_report_urls(self, symbol: str, year: int) -> List[str]:
        """
        Try known direct PDF URLs for major companies.

        Major tech companies like Google, Amazon, Microsoft have predictable
        URL patterns for their sustainability reports.

        Args:
            symbol: Stock symbol (e.g., 'GOOG', 'AMZN')
            year: Year to search for

        Returns:
            List of valid PDF URLs that exist
        """
        valid_urls = []

        if symbol not in self.KNOWN_REPORT_URL_PATTERNS:
            return valid_urls

        patterns = self.KNOWN_REPORT_URL_PATTERNS[symbol]
        logger.info(
            f"Trying {len(patterns)} known URL patterns for {symbol} {year}")

        for pattern in patterns:
            url = pattern.replace('{year}', str(year))
            try:
                # HEAD request to check if PDF exists
                response = self.session.head(
                    url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get(
                        'content-type', '').lower()
                    if 'pdf' in content_type or url.lower().endswith('.pdf'):
                        logger.info(f"Found known report: {url}")
                        valid_urls.append(url)
                else:
                    logger.debug(
                        f"Known URL not found (status {response.status_code}): {url}")
            except requests.RequestException as e:
                logger.debug(f"Failed to check known URL: {url} - {e}")

            time.sleep(0.5)  # Brief delay between checks

        return valid_urls

    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract PDF links from HTML that match sustainability patterns.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of PDF URLs
        """
        pdf_links = []

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().lower()

            # Check if it's a PDF
            if href.lower().endswith('.pdf'):
                # Check if it matches sustainability patterns
                full_url = urljoin(base_url, href)

                # Check both URL and link text for keywords
                combined_text = f"{href} {link_text}".lower()

                for pattern in self.REPORT_PATTERNS:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        pdf_links.append(full_url)
                        logger.debug(f"Found potential report: {full_url}")
                        break

        return pdf_links

    def _filter_urls_by_year(self, urls: List[str]) -> List[str]:
        """
        Filter URLs to only include those matching the year filter.
        This is done by checking if any year from the filter appears in the URL.

        Args:
            urls: List of URLs to filter

        Returns:
            Filtered list of URLs matching the year filter
        """
        if self.year_filter is None:
            return urls

        filtered_urls = []
        year_patterns = [str(year) for year in self.year_filter]

        for url in urls:
            # Check if any of the target years appear in the URL
            url_lower = url.lower()
            year_found = False

            for year in year_patterns:
                if year in url_lower:
                    filtered_urls.append(url)
                    year_found = True
                    break

            # If no year found in URL, we can't pre-filter - include it for PDF check
            if not year_found:
                # Check if URL has ANY year pattern (20xx)
                year_match = re.search(r'20\d{2}', url)
                if year_match:
                    # URL has a year but it's not in our filter - skip it
                    logger.debug(
                        f"Skipping {url} - year {year_match.group()} not in filter {self.year_filter}")
                else:
                    # No year in URL - include for PDF metadata check
                    filtered_urls.append(url)

        logger.info(
            f"Year filter applied: {len(filtered_urls)}/{len(urls)} URLs match years {self.year_filter}")
        return filtered_urls

    def download_report(self, url: str, company_symbol: str,
                        company_name: Optional[str] = None,
                        year: Optional[int] = None) -> Optional[str]:
        """
        Download a report PDF.

        Args:
            url: URL of the PDF
            company_symbol: Stock symbol of the company
            company_name: Name of the company (for database tracking)
            year: Year of the report (optional)

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Check if already in DATABASE BEFORE making HTTP request
            # (only checks DB, not file system - allows re-registering existing files)
            if company_name and self._is_url_in_database(url, company_name):
                return None  # Skip - already tracked in database

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Extract original filename from URL
            url_path = urlparse(url).path
            original_filename = os.path.basename(url_path)

            # Extract year from URL or filename first
            year_match = re.search(r'20\d{2}', url)
            year_str = None

            if year_match:
                year_str = year_match.group()
            else:
                # Try to extract year from PDF content/metadata
                year_str = self._extract_year_from_pdf(response.content)
                if year_str:
                    logger.debug(
                        f"Extracted year {year_str} from PDF content for {url}")

            # Fallback to current year if no year found
            if not year_str:
                year_str = str(datetime.now().year)
                logger.debug(f"No year found, using current year for {url}")

            # Check year filter - skip if year doesn't match filter
            if self.year_filter is not None:
                try:
                    report_year = int(year_str)
                    if report_year not in self.year_filter:
                        logger.info(
                            f"Skipping {url} - year {year_str} not in filter {self.year_filter}")
                        return None
                except ValueError:
                    logger.warning(
                        f"Could not parse year from {year_str}, skipping filter check")

            # Use original filename if it's a valid PDF name, otherwise generate one
            if original_filename and original_filename.lower().endswith('.pdf'):
                # Remove .pdf extension
                base_name = original_filename[:-4]

                # Check if year is already at the end (e.g., _2020 or -2020)
                if not re.search(r'[-_]20\d{2}$', base_name):
                    # Append year at the end
                    base_name = f"{base_name}-{year_str}"

                # Prefix with company symbol if not already present
                if not base_name.upper().startswith(company_symbol):
                    filename = f"{company_symbol}_{base_name}.pdf"
                else:
                    filename = f"{base_name}.pdf"
            else:
                # Fallback: generate filename with year and hash for uniqueness
                url_hash = hash(url) % 10000
                filename = f"{company_symbol}_report_{url_hash:04d}-{year_str}.pdf"

            # Create yearly folder structure (e.g., Stage0SourcePDFFiles/2023/)
            year_dir = self.base_download_dir / year_str
            year_dir.mkdir(parents=True, exist_ok=True)
            filepath = year_dir / filename

            # Check if file already exists with same content (skip duplicate downloads)
            if filepath.exists():
                existing_size = filepath.stat().st_size
                if existing_size == len(response.content):
                    logger.debug(f"File exists, skipping write: {filepath}")
                    # Still add to database if not already tracked
                    db_id = None
                    if company_name:
                        db_id = self._add_to_data_source(
                            company_name=company_name,
                            year=int(year_str),
                            source_url=url,
                            document_name=filename,
                            filepath=str(filepath)
                        )
                        if db_id:
                            logger.info(
                                f"Registered existing file in database: {filepath} (id: {db_id})")
                    return str(filepath)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded: {filepath}")

            # Add entry to t_data_source table
            db_id = None
            if company_name:
                db_id = self._add_to_data_source(
                    company_name=company_name,
                    year=int(year_str),
                    source_url=url,
                    document_name=filename,
                    filepath=str(filepath)
                )

            # Track success
            self.downloaded_reports.append({
                'symbol': company_symbol,
                'company_name': company_name,
                'url': url,
                'filepath': str(filepath),
                'download_date': datetime.now().isoformat(),
                'file_size': len(response.content),
                'db_id': db_id
            })

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            self.failed_downloads.append({
                'symbol': company_symbol,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return None

    def process_company(self, symbol: str, company_name: str,
                        website: Optional[str] = None) -> Dict:
        """
        Process a single company - search and download reports.

        Args:
            symbol: Stock symbol
            company_name: Company name
            website: Company website URL

        Returns:
            Dictionary with processing results
        """
        result = {
            'symbol': symbol,
            'company': company_name,
            'website': website,
            'reports_found': 0,
            'reports_downloaded': 0,
            'status': 'pending'
        }

        if not website:
            result['status'] = 'no_website'
            logger.warning(f"No website for {company_name} ({symbol})")
            return result

        try:
            # Normalize website URL
            if not website.startswith('http'):
                website = f'https://{website}'

            # First, try known direct PDF URLs for major companies
            report_urls = []
            if self.year_filter and symbol in self.KNOWN_REPORT_URL_PATTERNS:
                logger.info(f"Trying known report URLs for {symbol}")
                for year in self.year_filter:
                    known_urls = self.try_known_report_urls(symbol, year)
                    report_urls.extend(known_urls)
                logger.info(
                    f"Found {len(report_urls)} reports from known URLs for {symbol}")

            # Search company website for additional reports
            logger.info(f"Processing {company_name} ({symbol})")
            website_urls = self.search_company_website(
                company_name, website, symbol)

            # Apply year filter to URLs before downloading (optimization)
            if self.year_filter:
                website_urls = self._filter_urls_by_year(website_urls)

            report_urls.extend(website_urls)

            # Fallback to DuckDuckGo search if no reports found
            if not report_urls:
                logger.info(
                    f"No reports found on website, trying DuckDuckGo search for {company_name}")
                if self.year_filter:
                    # Search for each year
                    for year in self.year_filter:
                        ddg_urls = self.search_duckduckgo(company_name, year)
                        report_urls.extend(ddg_urls)
                else:
                    # Search without year filter
                    report_urls = self.search_duckduckgo(company_name)

            # Remove duplicates
            report_urls = list(set(report_urls))

            result['reports_found'] = len(report_urls)

            # Download reports
            downloaded_count = 0
            for url in report_urls:
                filepath = self.download_report(url, symbol, company_name)
                if filepath:
                    downloaded_count += 1
                time.sleep(self.delay_seconds)

            result['reports_downloaded'] = downloaded_count
            result['status'] = 'completed'

        except Exception as e:
            logger.error(f"Error processing {company_name}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def download_all_reports(self, companies_df: pd.DataFrame,
                             limit: Optional[int] = None) -> pd.DataFrame:
        """
        Download sustainability reports for all companies.

        Args:
            companies_df: DataFrame with company information
            limit: Maximum number of companies to process (for testing)

        Returns:
            DataFrame with processing results
        """
        results = []

        # Get required columns
        required_cols = ['Symbol', 'Company']
        if not all(col in companies_df.columns for col in required_cols):
            raise ValueError(f"DataFrame must have columns: {required_cols}")

        # Process companies
        companies = companies_df.head(limit) if limit else companies_df
        total = len(companies)

        logger.info(f"Starting download for {total} companies")

        for idx, row in companies.iterrows():
            symbol = row['Symbol']
            company = row['Company']
            # Try to get website from DataFrame first, otherwise derive it
            website = row.get('Website', row.get('website', None))
            if not website or pd.isna(website):
                website = self.get_company_website(symbol, company)

            logger.info(
                f"Progress: {idx + 1}/{total} - {company} ({website or 'No website'})")

            result = self.process_company(symbol, company, website)
            results.append(result)

            # Save progress periodically
            if (idx + 1) % 10 == 0:
                self._save_progress(results)

        # Final save
        results_df = pd.DataFrame(results)
        self._save_progress(results)
        self._save_metadata()

        logger.info(
            f"Completed! Downloaded {len(self.downloaded_reports)} reports")
        return results_df

    def _save_progress(self, results: List[Dict]):
        """Save download progress to CSV."""
        progress_file = self.cache_dir / 'download_progress.csv'
        pd.DataFrame(results).to_csv(progress_file, index=False)
        logger.debug(f"Saved progress to {progress_file}")

    def _save_metadata(self):
        """Save download metadata."""
        # Save successful downloads
        if self.downloaded_reports:
            downloads_file = self.cache_dir / 'downloaded_reports.csv'
            pd.DataFrame(self.downloaded_reports).to_csv(
                downloads_file, index=False)
            logger.info(
                f"Saved {len(self.downloaded_reports)} download records")

        # Save failures
        if self.failed_downloads:
            failures_file = self.cache_dir / 'failed_downloads.csv'
            pd.DataFrame(self.failed_downloads).to_csv(
                failures_file, index=False)
            logger.info(f"Saved {len(self.failed_downloads)} failure records")

    def close(self):
        """Close database connection and cleanup resources."""
        if self.db_connection:
            try:
                self.db_connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")
        self.session.close()

    def __enter__(self):
        """Support context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on context manager exit."""
        self.close()
        return False


def main():
    """Example usage of the downloader."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download sustainability reports for S&P 500 companies'
    )
    parser.add_argument(
        '--output-dir',
        default='./sustainability_reports',
        help='Directory to save reports'
    )
    parser.add_argument(
        '--companies-csv',
        help='CSV file with company data (optional)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of companies to process (for testing)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds'
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = SustainabilityReportDownloader(
        download_dir=args.output_dir,
        delay_seconds=args.delay
    )

    # Load companies
    companies_df = downloader.load_sp500_companies(args.companies_csv)

    # Download reports
    results_df = downloader.download_all_reports(
        companies_df, limit=args.limit)

    # Print summary
    print("\n" + "="*60)
    print("DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total companies processed: {len(results_df)}")
    print(f"Reports found: {results_df['reports_found'].sum()}")
    print(f"Reports downloaded: {results_df['reports_downloaded'].sum()}")
    print(f"Failed: {len(downloader.failed_downloads)}")
    print(f"\nResults saved to: {args.output_dir}")
    print("="*60)


if __name__ == '__main__':
    main()
