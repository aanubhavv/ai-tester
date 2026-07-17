import logging
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Set
import json

from playwright.sync_api import sync_playwright
from google.genai import types

from app.services.project_service import project_service
from app.services.ai.ai_service import ai_service
from app.services.ai.prompt_manager import prompt_manager

logger = logging.getLogger(__name__)

class ExplorationService:
    def explore_website(self, project_id: str) -> str:
        project = project_service.get_project(project_id)
        if not project or not project.primary_url:
            return "No valid primary URL found for this project."
        
        base_url = project.primary_url
        visited: Set[str] = set()
        to_visit: List[str] = [base_url]
        max_pages = getattr(project, 'max_crawl_pages', 5)
        
        exploration_data = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            
            while to_visit and len(visited) < max_pages:
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue
                    
                visited.add(current_url)
                try:
                    logger.info(f"AI Explorer visiting: {current_url}")
                    response = page.goto(current_url, wait_until="domcontentloaded", timeout=15000)
                    
                    # Wait a bit for dynamic content to settle
                    page.wait_for_timeout(2000)
                    
                    title = page.title()
                    final_url = page.url
                    
                    # Capture screenshot
                    screenshot_bytes = page.screenshot(full_page=True)
                    
                    # Extract interactable elements
                    elements_info = page.evaluate('''() => {
                        const links = Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText || a.textContent, href: a.href}));
                        const buttons = Array.from(document.querySelectorAll('button')).map(b => b.innerText || b.textContent);
                        const inputs = Array.from(document.querySelectorAll('input, select, textarea')).map(i => ({type: i.type, name: i.name, id: i.id}));
                        return {links, buttons, inputs};
                    }''')
                    
                    # Clean up empty strings and limit counts to avoid massive contexts
                    links = [l for l in elements_info["links"] if l.get("text") and l.get("href")][:50]
                    buttons = [b for b in elements_info["buttons"] if b][:20]
                    
                    page_info = {
                        "url": final_url,
                        "title": title,
                        "links": links,
                        "buttons": buttons,
                        "inputs": elements_info["inputs"]
                    }
                    
                    # Analyze page with Vision AI
                    page_analysis_prompt = prompt_manager.get_prompt(
                        "test_generation/page_analysis", 
                        url=final_url, 
                        title=title, 
                        dom_elements=json.dumps(page_info, indent=2)
                    )
                    
                    multimodal_content = [
                        types.Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
                        page_analysis_prompt
                    ]
                    
                    try:
                        ai_page_analysis = ai_service.generate_text_raw(
                            task="exploration",
                            prompt=multimodal_content
                        )
                    except Exception as e:
                        logger.error(f"Failed to analyze page with AI: {e}")
                        ai_page_analysis = "Vision AI analysis failed."
                        
                    exploration_data.append({
                        "url": final_url,
                        "title": title,
                        "ai_analysis": ai_page_analysis
                    })
                    
                    # Add internal links to queue
                    base_domain = urlparse(base_url).netloc
                    for link in links:
                        href = link.get("href")
                        if href:
                            parsed_href = urlparse(href)
                            if parsed_href.netloc == base_domain or not parsed_href.netloc:
                                full_url = urljoin(final_url, href)
                                full_url = full_url.split('#')[0]
                                if full_url not in visited and full_url not in to_visit:
                                    to_visit.append(full_url)
                                    
                except Exception as e:
                    logger.error(f"Error exploring {current_url}: {e}")
                    
            browser.close()
            
        if not exploration_data:
            return "Exploration failed to yield any data."
            
        # Summarize the entire exploration
        exploration_text = "=== EXPLORATION RESULTS ===\n"
        for p in exploration_data:
            exploration_text += f"\nPAGE: {p['title']} ({p['url']})\n"
            exploration_text += f"ANALYSIS:\n{p['ai_analysis']}\n"
            exploration_text += "-" * 40 + "\n"
            
        try:
            summary = ai_service.generate_text(
                task="test_generation/exploration_summary",
                context_kwargs={"exploration_data": exploration_text},
                use_cache=False
            )
            return summary
        except Exception as e:
            logger.error(f"Failed to generate exploration summary: {e}")
            return exploration_text

exploration_service = ExplorationService()
