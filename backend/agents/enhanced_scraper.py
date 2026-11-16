"""
Enhanced Scraper Agent - Improved filtering for services
"""

import re
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .base_agent import BaseAgent

class EnhancedScraperAgent(BaseAgent):
    def __init__(self):
        super().__init__("EnhancedScraperAgent")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.visited_urls = set()
        
        # Keywords to filter out (navigation, footer, generic)
        self.skip_keywords = [
            'let\'s connect', 'contact us', 'sign in', 'register', 'login',
            'privacy policy', 'terms of use', 'cookie policy', 'about us',
            'careers', 'blog', 'news', 'events', 'webinars', 'podcasts',
            'sitemap', 'help', 'support', 'faq', 'search', 'menu',
            'home', 'back to top', 'view all', 'read more', 'learn more',
            'get started', 'request demo', 'free trial', 'download',
            'follow us', 'share', 'subscribe', 'newsletter'
        ]
        
        # Country/region names to filter out
        self.country_names = [
            'afghanistan', 'albania', 'algeria', 'andorra', 'angola', 'antigua', 'argentina',
            'armenia', 'australia', 'austria', 'azerbaijan', 'bahamas', 'bahrain', 'bangladesh',
            'barbados', 'belarus', 'belgium', 'belize', 'benin', 'bhutan', 'bolivia',
            'bosnia', 'botswana', 'brazil', 'brunei', 'bulgaria', 'burkina', 'burundi',
            'cambodia', 'cameroon', 'canada', 'cape verde', 'central african', 'chad',
            'chile', 'china', 'colombia', 'comoros', 'congo', 'costa rica', 'croatia',
            'cuba', 'cyprus', 'czech', 'denmark', 'djibouti', 'dominica', 'dominican',
            'ecuador', 'egypt', 'el salvador', 'equatorial guinea', 'eritrea', 'estonia',
            'ethiopia', 'fiji', 'finland', 'france', 'gabon', 'gambia', 'georgia',
            'germany', 'ghana', 'greece', 'grenada', 'guatemala', 'guinea', 'guyana',
            'haiti', 'honduras', 'hungary', 'iceland', 'india', 'indonesia', 'iran',
            'iraq', 'ireland', 'israel', 'italy', 'ivory coast', 'jamaica', 'japan',
            'jordan', 'kazakhstan', 'kenya', 'kiribati', 'kuwait', 'kyrgyzstan', 'laos',
            'latvia', 'lebanon', 'lesotho', 'liberia', 'libya', 'liechtenstein', 'lithuania',
            'luxembourg', 'madagascar', 'malawi', 'malaysia', 'maldives', 'mali', 'malta',
            'marshall islands', 'mauritania', 'mauritius', 'mexico', 'micronesia', 'moldova',
            'monaco', 'mongolia', 'montenegro', 'morocco', 'mozambique', 'myanmar', 'namibia',
            'nauru', 'nepal', 'netherlands', 'new zealand', 'nicaragua', 'niger', 'nigeria',
            'north korea', 'north macedonia', 'norway', 'oman', 'pakistan', 'palau', 'panama',
            'papua new guinea', 'paraguay', 'peru', 'philippines', 'poland', 'portugal',
            'qatar', 'romania', 'russia', 'rwanda', 'saint kitts', 'saint lucia',
            'saint vincent', 'samoa', 'san marino', 'sao tome', 'saudi arabia', 'senegal',
            'serbia', 'seychelles', 'sierra leone', 'singapore', 'slovakia', 'slovenia',
            'solomon islands', 'somalia', 'south africa', 'south korea', 'south sudan',
            'spain', 'sri lanka', 'sudan', 'suriname', 'swaziland', 'sweden', 'switzerland',
            'syria', 'taiwan', 'tajikistan', 'tanzania', 'thailand', 'timor-leste', 'togo',
            'tonga', 'trinidad', 'tunisia', 'turkey', 'turkmenistan', 'tuvalu', 'uganda',
            'ukraine', 'united arab emirates', 'united kingdom', 'united republic of',
            'united states', 'uruguay', 'uzbekistan', 'vanuatu', 'vatican', 'venezuela',
            'vietnam', 'yemen', 'zambia', 'zimbabwe'
        ]
        
        # Common generic words to filter out
        self.generic_words = [
            'services', 'solutions', 'offerings', 'expertise', 'capabilities',
            'about', 'contact', 'home', 'menu', 'back', 'support', 'help',
            'faq', 'events', 'news', 'blog', 'careers', 'partners', 'clients'
        ]
    
    async def process(self, input_data: Dict) -> Dict:
        urls = input_data.get("urls", [])
        self.log(f"Starting enhanced scrape of {len(urls)} companies")
        
        results = []
        for url in urls:
            try:
                data = await self._scrape_company(url)
                results.append({"url": url, "data": data, "status": "success"})
                await asyncio.sleep(1)
            except Exception as e:
                self.log(f"Error: {str(e)}")
                results.append({"url": url, "error": str(e), "status": "failed"})
        
        return {"scraped_data": results, "total": len(results)}
    
    async def _scrape_company(self, url: str) -> Dict:
        """Scrape company data from multiple pages with improved filtering"""
        
        # 1. Scrape homepage
        home_data = await self._scrape_page(url)
        
        # 2. Try to find and scrape services page
        services_data = await self._find_and_scrape_page(url, ['services', 'solutions', 'what-we-do'])
        
        # 3. Try to find and scrape about page
        about_data = await self._find_and_scrape_page(url, ['about', 'about-us', 'company', 'who-we-are', 'our-story'])

        # 4. Pages that often mention team size / founding (used only for company size)
        careers_data = await self._find_and_scrape_page(url, ['careers', 'jobs', 'join-us'])
        team_data = await self._find_and_scrape_page(url, ['team', 'our-team', 'people'])
        
        # Merge all text
        combined_text = " ".join([
            home_data.get('text', ''),
            services_data.get('text', ''),
            about_data.get('text', '')
        ])
        
        # Extract services with improved filtering
        services = self._extract_services_clean(combined_text, home_data.get('soup'), services_data.get('soup'))
        
        # Extract tech stack
        tech_stack = self._extract_tech_clean(combined_text)
        
        # Extract clients
        clients = self._extract_clients_clean(combined_text, home_data.get('soup'))
        
        # Extract company name
        company_name = self._extract_company_name_clean(home_data.get('soup'), url)
        
        # Extract about
        about = self._extract_about_clean(home_data.get('soup'), about_data.get('soup'), combined_text)
        
        # Extract founded year
        founded_year = self._extract_founded_year_clean(combined_text)

        # Classify company size (Startup / Small / Medium / Enterprise / Unknown)
        size_text = " ".join([combined_text, careers_data.get('text', ''), team_data.get('text', '')])
        wikidata = self._lookup_wikidata(company_name, url, home_data.get('title') or '')
        if founded_year == "Unknown" and wikidata.get("founded_year"):
            founded_year = wikidata["founded_year"]
        team_count = self._count_team_members(team_data)
        company_size = self._extract_company_size(size_text, founded_year, wikidata, team_count)

        # Extract industry
        industry = self._extract_industry_clean(combined_text)
        
        return {
            "company_name": company_name,
            "url": url,
            "services": services[:20],
            "tech_stack": tech_stack[:15],
            "clients": {"names": clients[:15]},
            "about": about[:500],
            "founded_year": founded_year,
            "company_size": company_size,
            "industry": industry[:10],
            "page_title": home_data.get('title', ''),
            "meta_description": home_data.get('description', '')
        }
    
    async def _scrape_page(self, url: str) -> Dict:
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            text = re.sub(r'\s+', ' ', text).strip()
            
            return {
                'soup': soup,
                'text': text,
                'title': soup.title.string if soup.title else '',
                'description': self._get_meta_description(soup)
            }
        except:
            return {}
    
    async def _find_and_scrape_page(self, base_url: str, paths: List[str]) -> Dict:
        for path in paths:
            for prefix in ['', '/', '/en/', '/us/', '/global/']:
                url = urljoin(base_url, f"{prefix}{path}")
                if url not in self.visited_urls:
                    self.visited_urls.add(url)
                    result = await self._scrape_page(url)
                    if result:
                        return result
        return {}
    
    def _is_valid_service(self, text: str) -> bool:
        """Check if text is a valid service name"""
        if not text or len(text) < 3 or len(text) > 80:
            return False
        
        text_lower = text.lower()
        
        # Skip if it's a country name
        for country in self.country_names:
            if country in text_lower:
                return False
        
        # Skip if it's a generic word
        for word in self.generic_words:
            if text_lower == word or text_lower.endswith(word):
                return False
        
        # Skip if it's navigation/footer text
        for skip in self.skip_keywords:
            if skip in text_lower:
                return False
        
        # Must contain service-related words
        service_indicators = [
            'development', 'services', 'solutions', 'consulting', 'engineering',
            'design', 'build', 'cloud', 'data', 'ai', 'analytics', 'security',
            'automation', 'integration', 'management', 'transformation',
            'strategy', 'architecture', 'platform', 'infrastructure'
        ]
        
        has_indicator = any(ind in text_lower for ind in service_indicators)
        if not has_indicator:
            # Check if it's a common service name
            common_services = [
                'artificial intelligence', 'machine learning', 'cloud computing',
                'cybersecurity', 'digital transformation', 'data analytics',
                'software development', 'web development', 'mobile development',
                'devops', 'iot', 'blockchain', 'saas', 'enterprise solutions'
            ]
            if not any(service in text_lower for service in common_services):
                return False
        
        return True
    
    def _extract_services_clean(self, text: str, *soups) -> List[str]:
        """Extract services with clean filtering"""
        services = []
        
        # Common service keywords to look for
        service_keywords = [
            'AI Development', 'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
            'Custom Software Development', 'Web Development', 'Mobile Development',
            'Cloud Computing', 'Cloud Services', 'DevOps', 'Data Analytics',
            'Data Engineering', 'Digital Transformation', 'IoT', 'Blockchain',
            'Cybersecurity', 'Enterprise Solutions', 'SaaS', 'API Development',
            'IT Consulting', 'Managed Services', 'Quality Assurance', 'Automation',
            'RPA', 'Business Intelligence', 'Big Data', 'Application Modernization',
            'Cloud Migration', 'Infrastructure Management', 'Security Consulting',
            'Strategy Consulting', 'Product Engineering', 'Platform Engineering',
            'Salesforce', 'SAP', 'Oracle', 'ERP', 'CRM', 'Data Science',
            'AI Consulting', 'MLOps', 'DevSecOps', 'Cloud Native Development',
            'Microservices', 'Serverless', 'Containerization', 'Kubernetes',
            'Azure', 'AWS', 'GCP', 'Snowflake', 'Databricks', 'Tableau', 'PowerBI',
            'React', 'Angular', 'Vue.js', 'Node.js', 'Python', 'Java', 'Go', 'Rust'
        ]
        
        # Check for each keyword
        for keyword in service_keywords:
            if keyword.lower() in text.lower():
                if self._is_valid_service(keyword):
                    services.append(keyword)
        
        # Also extract from HTML sections
        for soup in soups:
            if not soup:
                continue
            
            # Look for service sections
            service_sections = soup.find_all(['div', 'section', 'ul'], 
                class_=re.compile(r'service|solution|offer|capability|expertise|what we do', re.I))
            
            for section in service_sections:
                # Get headings and list items
                items = section.find_all(['h2', 'h3', 'h4', 'h5', 'li', 'strong', 'b', 'span'])
                for item in items:
                    item_text = item.get_text(strip=True)
                    if self._is_valid_service(item_text):
                        services.append(item_text)
        
        # Also look for service-related paragraphs
        for soup in soups:
            if not soup:
                continue
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if len(p_text) > 10 and len(p_text) < 100:
                    if any(word in p_text.lower() for word in ['offer', 'provide', 'service', 'solution', 'develop', 'build']):
                        if self._is_valid_service(p_text):
                            services.append(p_text)
        
        # Remove duplicates and clean
        seen = set()
        unique = []
        for s in services:
            s = s.strip()
            # Remove numbering
            s = re.sub(r'^\d+\.\s*', '', s)
            s = re.sub(r'^[•●·\-*]\s*', '', s)
            if s and len(s) > 3 and s not in seen:
                seen.add(s)
                unique.append(s)
        
        return unique
    
    def _extract_tech_clean(self, text: str) -> List[str]:
        """Extract technology stack"""
        tech_stack = []
        
        technologies = [
            'Python', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue.js', 'Next.js',
            'Node.js', 'Express', 'Django', 'Flask', 'Spring Boot', 'Java', 'C#', '.NET',
            'Go', 'Rust', 'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
            'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy',
            'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch',
            'Kafka', 'Spark', 'Hadoop', 'Tableau', 'PowerBI', 'Snowflake', 'Databricks',
            'Git', 'GitHub', 'GitLab', 'Jenkins', 'Terraform', 'Salesforce', 'SAP', 'Oracle',
            'OpenAI', 'LangChain', 'LLM', 'RAG', 'Gemini', 'ChatGPT'
        ]
        
        for tech in technologies:
            if tech.lower() in text.lower():
                tech_stack.append(tech)
        
        return list(set(tech_stack))
    
    def _extract_clients_clean(self, text: str, soup) -> List[str]:
        """Extract client names"""
        clients = []
        
        # Look for client sections
        if soup:
            client_sections = soup.find_all(['div', 'section', 'ul'], 
                class_=re.compile(r'client|customer|partner|brand|clientele', re.I))
            for section in client_sections:
                section_text = section.get_text()
                # Look for company names
                company_pattern = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b'
                matches = re.findall(company_pattern, section_text)
                for match in matches:
                    clean = match.strip()
                    if 3 < len(clean) < 40:
                        skip_words = ['Client', 'Customer', 'Partner', 'Brand', 'Logo', 'Trusted', 'View', 'All']
                        if clean not in skip_words and not any(word in clean.lower() for word in ['logo', 'icon', 'button']):
                            clients.append(clean)
        
        # Also look in text
        patterns = [
            r'(?:clients|customers|partners|trusted by)[:\s]+([^.\n]{10,80})',
            r'worked with\s+([^.\n]{10,80})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                names = re.split(r',\s*|\s+and\s+|\s*&\s*', match)
                for name in names:
                    clean = name.strip()
                    if 3 < len(clean) < 40:
                        skip_words = ['clients', 'customers', 'partners', 'include', 'trusted', 'more']
                        if not any(word in clean.lower() for word in skip_words):
                            clients.append(clean)
        
        return list(set(clients))
    
    def _extract_company_name_clean(self, soup, url: str) -> str:
        """Extract company name"""
        if soup:
            og = soup.find('meta', property='og:site_name')
            if og and og.get('content'):
                name = og['content'].strip()
                if len(name) > 2 and len(name) < 80:
                    return name
            
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
                for sep in ['|', '–', '—', '-']:
                    if sep in title:
                        parts = title.split(sep)
                        for part in parts:
                            part = part.strip()
                            if len(part) > 2 and len(part) < 60:
                                return part
        
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if domain_match:
            name = domain_match.group(1).split('.')[0]
            return name.capitalize()
        
        return "Unknown"
    
    def _extract_about_clean(self, home_soup, about_soup, text: str) -> str:
        """Extract about text"""
        soup = about_soup or home_soup
        if soup:
            about_section = soup.find(['div', 'section'], class_=re.compile(r'about|overview|company|hero', re.I))
            if about_section:
                about_text = about_section.get_text(strip=True)
                if len(about_text) > 50:
                    return about_text
        
        patterns = [
            r'(?:about|overview)[:\s]+([^.\n]{50,}[.][^.\n]{0,200})',
            r'we are\s+([^.\n]{50,}[.][^.\n]{0,200})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0][:500]
        
        return "No about information available"
    
    def _extract_founded_year_clean(self, text: str) -> str:
        patterns = [
            r'(?:founded|established|since|Years of)\s+(?:in\s+)?(\d{4})',
            r'(\d{4})\s*(?:founded|established)',
            r'est\.\s*(\d{4})'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                year = matches[0]
                if 1900 <= int(year) <= datetime.now().year:
                    return year
        return "Unknown"

    # A company founded within this many years counts as a Startup
    STARTUP_MAX_AGE_YEARS = 10

    @staticmethod
    def _size_from_employees(employees: int) -> str:
        if employees < 50:
            return "Startup"
        if employees < 200:
            return "Small Business"
        if employees < 1000:
            return "Medium Business"
        return "Enterprise"

    def _extract_company_size(self, text: str, founded_year: str,
                              wikidata: Optional[Dict] = None, team_count: int = 0) -> Dict[str, Any]:
        """Classify the company by size. Rules are tried in order; first match wins:
        1. Employee count stated on the website
        2. Employee count from Wikidata (well-known companies)
        3. Founded within the last STARTUP_MAX_AGE_YEARS years -> Startup
           (founded year from website/Wikidata, else estimated from
           "(c) 2015-2026" or "12+ years of experience")
        4. Self-description keywords ("we are a startup", "offices in 40 countries")
        5. People listed on the team page (only if founding year is unknown)
        6. Otherwise Unknown
        """
        wikidata = wikidata or {}

        # 1. Employee count on the website
        employees = self._extract_employee_count(text)
        if employees is not None:
            return {"category": self._size_from_employees(employees), "employees": employees, "source": "employee_count"}

        # 2. Employee count from Wikidata
        if wikidata.get("employees"):
            employees = wikidata["employees"]
            return {"category": self._size_from_employees(employees), "employees": employees, "source": "wikidata"}

        # 3. Founded year (stated, or estimated from other clues)
        year = founded_year if founded_year and founded_year.isdigit() else self._estimate_founded_year(text)
        if year:
            age = datetime.now().year - int(year)
            if 0 <= age <= self.STARTUP_MAX_AGE_YEARS:
                return {"category": "Startup", "employees": None, "source": "founded_year"}

        # 4. Keywords
        if re.search(r"\b(?:we\s+are|we're|is)\s+an?\s+(?:[\w-]+\s+){0,2}start-?up\b", text, re.IGNORECASE):
            return {"category": "Startup", "employees": None, "source": "keywords"}
        global_presence = re.search(
            r"(?:offices|presence|operations|locations)\s+in\s+(\d+)\+?\s+countries", text, re.IGNORECASE
        )
        if global_presence and int(global_presence.group(1)) >= 20:
            return {"category": "Enterprise", "employees": None, "source": "keywords"}

        # 5. Team page head-count (last resort: team pages often list only leaders)
        if not year and team_count >= 3:
            return {"category": self._size_from_employees(team_count), "employees": team_count, "source": "team_page"}

        # 6. Nothing found
        return {"category": "Unknown", "employees": None, "source": "none"}

    def _estimate_founded_year(self, text: str) -> Optional[str]:
        """Estimate founding year from indirect clues when it is not stated."""
        this_year = datetime.now().year
        # "(c) 2015-2026" / "Copyright 2015 - 2026"
        match = re.search(r"(?:©|&copy;|\(c\)|copyright)\s*(?:copyright\s*)?(\d{4})\s*[-–]\s*(\d{4})", text, re.IGNORECASE)
        if match and 1900 <= int(match.group(1)) < int(match.group(2)) <= this_year:
            return match.group(1)
        # "12+ years of experience"
        match = re.search(r"(\d{1,3})\+?\s*years?\s+of\s+(?:experience|excellence|expertise|innovation|service)", text, re.IGNORECASE)
        if match and 0 < int(match.group(1)) < 150:
            return str(this_year - int(match.group(1)))
        return None

    def _count_team_members(self, team_data: Dict) -> int:
        """Rough head-count from a team page: unique personal LinkedIn links or member cards."""
        soup = team_data.get('soup') if team_data else None
        if not soup:
            return 0
        title = (team_data.get('title') or '').lower()
        if 'leadership' in title or 'board' in title:
            return 0
        linkedin = {a['href'].split('?')[0].rstrip('/') for a in soup.find_all('a', href=True)
                    if 'linkedin.com/in/' in a['href']}
        cards = soup.find_all(class_=re.compile(r'team[-_]?member|member[-_]?card|person[-_]?card|staff[-_]?member', re.I))
        return max(len(linkedin), len(cards))

    def _lookup_wikidata(self, company_name: str, url: str, page_title: str = '') -> Dict[str, Any]:
        """Look up employee count and founding year on Wikidata (free, no API key).
        Only accepts an entry whose official website matches this company's domain."""
        result: Dict[str, Any] = {}
        domain = urlparse(url).netloc.lower().removeprefix('www.')
        if not domain:
            return result
        # Try the company name, then the page title ("Persistent Systems | ..."), then the domain ("deepai")
        title_name = re.split(r'\s[|\-–—:]\s', page_title.strip())[0].strip() if page_title else ''
        searches = [n for n in dict.fromkeys([company_name, title_name, domain.split('.')[0]])
                    if n and n != "Unknown" and len(n) <= 60]
        try:
            # 1st: find the company by its official website address (works even if the site blocks us)
            variants = '|'.join(f'P856={p}{w}{domain}{sl}' for p in ['https://', 'http://']
                                for w in ['www.', ''] for sl in ['/', ''])
            by_site = self._wikidata_get({"action": "query", "list": "search",
                                          "srsearch": f'haswbstatement:"{variants}"', "srlimit": 5})
            def candidate_lists():
                yield [x["title"] for x in by_site.get("query", {}).get("search", [])]
                # 2nd: search by name (only reached if the website lookup found no match)
                for name in searches:
                    found = self._wikidata_get({"action": "wbsearchentities", "search": name, "language": "en",
                                                "type": "item", "limit": 5})
                    yield [item["id"] for item in found.get("search", [])]

            for ids in candidate_lists():
                if not ids:
                    continue
                entities = self._wikidata_get({"action": "wbgetentities", "ids": "|".join(ids),
                                               "props": "claims|sitelinks"}).get("entities", {})
                for entity_id in ids:  # keep search ranking order
                    claims = entities.get(entity_id, {}).get("claims", {})
                    websites = [c["mainsnak"].get("datavalue", {}).get("value", "") for c in claims.get("P856", [])]
                    if not any(domain in urlparse(w).netloc.lower() for w in websites if isinstance(w, str)):
                        continue
                    employees = self._latest_claim(claims.get("P1128", []))
                    if employees:
                        result["employees"] = int(float(employees["amount"]))
                    else:
                        wiki_title = entities[entity_id].get("sitelinks", {}).get("enwiki", {}).get("title")
                        if wiki_title:
                            result.update(self._wikipedia_employees(wiki_title))
                    inception = self._latest_claim(claims.get("P571", []))
                    if inception:
                        result["founded_year"] = inception["time"][1:5]
                    return result
        except Exception as e:
            self.log(f"Wikidata lookup failed for {domain}: {e}")
        return result

    def _wikipedia_employees(self, title: str) -> Dict[str, Any]:
        """Read 'num_employees' from the English Wikipedia infobox."""
        try:
            resp = requests.get("https://en.wikipedia.org/w/api.php",
                                params={"action": "parse", "page": title, "prop": "wikitext",
                                        "section": 0, "format": "json"},
                                headers={'User-Agent': 'CompetitorIntel/1.0 (competitor intelligence dashboard)'},
                                timeout=8)
            wikitext = resp.json().get("parse", {}).get("wikitext", {}).get("*", "")
            line = re.search(r"\|\s*num_employees\s*=([^\n]*)", wikitext)
            if line:
                value = re.sub(r"\{\{[^{}|]*\|?|\}\}|<ref[^>]*/>|<ref.*?</ref>", " ", line.group(1))
                number = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)", value)
                if number and int(number.group(1).replace(",", "")) > 0:
                    return {"employees": int(number.group(1).replace(",", ""))}
        except Exception as e:
            self.log(f"Wikipedia lookup failed for {title}: {e}")
        return {}

    def _wikidata_get(self, params: Dict) -> Dict:
        """GET the Wikidata API; on rate limit (HTTP 429) wait and retry once."""
        headers = {'User-Agent': 'CompetitorIntel/1.0 (competitor intelligence dashboard)'}
        params = {**params, "format": "json"}
        for attempt in range(2):
            resp = requests.get("https://www.wikidata.org/w/api.php", params=params, headers=headers, timeout=8)
            if resp.status_code == 429 and attempt == 0:
                wait = resp.headers.get("Retry-After", "")
                time.sleep(min(int(wait), 10) if wait.isdigit() else 3)
                continue
            resp.raise_for_status()
            return resp.json()
        return {}

    @staticmethod
    def _latest_claim(claims: List[Dict]) -> Optional[Dict]:
        """Pick the preferred value, else the one with the latest 'point in time' (P585)."""
        claims = [c for c in claims if c.get("rank") != "deprecated" and c["mainsnak"].get("datavalue")]
        if not claims:
            return None
        preferred = [c for c in claims if c.get("rank") == "preferred"]
        if preferred:
            return preferred[0]["mainsnak"]["datavalue"]["value"]
        def when(c):
            q = c.get("qualifiers", {}).get("P585", [])
            return q[0].get("datavalue", {}).get("value", {}).get("time", "") if q else ""
        return max(claims, key=when)["mainsnak"]["datavalue"]["value"]

    def _extract_employee_count(self, text: str) -> Optional[int]:
        """Find a stated employee count, e.g. 'team of 25', '500+ employees', '10,000 professionals'."""
        number = r"(\d{1,3}(?:,\d{3})+|\d+)"
        patterns = [
            number + r"\s*\+?\s*(?:employees|staff|team\s+members|professionals)\b",
            r"team\s+of\s+(?:over\s+|more\s+than\s+)?" + number,
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                count = int(match.group(1).replace(",", ""))
                if count > 0:
                    return count
        return None
    
    def _extract_industry_clean(self, text: str) -> List[str]:
        industries = []
        industry_list = [
            'AI', 'Machine Learning', 'Data Science', 'SaaS', 'Cloud Computing',
            'Cybersecurity', 'Fintech', 'Healthtech', 'Edtech', 'E-commerce',
            'Analytics', 'Automation', 'Robotics', 'IoT', 'Blockchain',
            'Healthcare', 'Finance', 'Retail', 'Manufacturing', 'Education',
            'Government', 'Telecom', 'Media', 'Energy', 'Banking', 'Insurance'
        ]
        for industry in industry_list:
            if industry.lower() in text.lower():
                industries.append(industry)
        return list(set(industries))
    
    def _get_meta_description(self, soup) -> str:
        meta = soup.find("meta", attrs={"name": "description"})
        return meta.get("content") if meta else None

    def _extract_clients_clean(self, text: str, soup) -> List[str]:
        """Extract client names with better filtering"""
        clients = []
        
        # Skip patterns for noise
        noise_patterns = [
            r'files patents', r'from ideation to prototype', r'are at the heart of',
            r'delivers solutions for', r'retail', r'bfsi', r'and delivers solutions'
        ]
        
        # Look for client sections
        if soup:
            client_sections = soup.find_all(['div', 'section', 'ul'], 
                class_=re.compile(r'client|customer|partner|brand|clientele|logo', re.I))
            for section in client_sections:
                section_text = section.get_text()
                # Look for company names with proper capitalization
                company_pattern = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b'
                matches = re.findall(company_pattern, section_text)
                for match in matches:
                    clean = match.strip()
                    # Filter criteria
                    if 3 < len(clean) < 40:
                        skip_words = ['Client', 'Customer', 'Partner', 'Brand', 'Logo', 'Trusted', 
                                    'View', 'All', 'Read', 'More', 'Learn', 'About', 'Contact',
                                    'Services', 'Solutions', 'Products', 'Company', 'Our', 'The']
                        if clean not in skip_words:
                            # Check for noise patterns
                            is_noise = False
                            for pattern in noise_patterns:
                                if re.search(pattern, clean, re.IGNORECASE):
                                    is_noise = True
                                    break
                            if not is_noise:
                                clients.append(clean)
        
        # Also look in text with better patterns
        patterns = [
            r'(?:clients|customers|partners|trusted by)[:\s]+([^.\n]{10,80})',
            r'worked with\s+([^.\n]{10,80})',
            r'(?:including|such as)\s+([^.\n]{10,80})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split by commas, "and", "&"
                names = re.split(r',\s*|\s+and\s+|\s*&\s*', match)
                for name in names:
                    clean = name.strip()
                    # Filter criteria
                    if 3 < len(clean) < 40:
                        skip_words = ['clients', 'customers', 'partners', 'include', 'trusted', 
                                    'more', 'view', 'read', 'learn']
                        if not any(word in clean.lower() for word in skip_words):
                            # Check for noise patterns
                            is_noise = False
                            for pattern in noise_patterns:
                                if re.search(pattern, clean, re.IGNORECASE):
                                    is_noise = True
                                    break
                            if not is_noise:
                                clients.append(clean)
        
        return list(set(clients))
