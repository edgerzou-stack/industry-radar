import os
import time
import json
from dotenv import load_dotenv
from openai import OpenAI
from google import genai

load_dotenv()

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)

def get_deepseek_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)

def _call_llm_with_fallback(prompt, config, system_prompt="You are a helpful assistant designed to output JSON.", title_context=""):
    """
    Executes the Triple-Tier Cascade Router:
    1. Google Gemini (gemini-2.5-flash)
    2. OpenAI (gpt-5.4-mini for scoring, gpt-5.5 for heavy lifting)
    3. DeepSeek (deepseek-v4-flash for scoring, deepseek-v4-pro for heavy lifting)
    """
    
    is_heavy = "VC Analyst" in system_prompt
    openai_model = "gpt-5.5" if is_heavy else "gpt-5.4-mini"
    deepseek_model = "deepseek-v4-pro" if is_heavy else "deepseek-v4-flash"
    
    # 1. Gemini
    gemini_client = get_gemini_client()
    if gemini_client:
        try:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )
            return json.loads(response.text)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "exhausted" in err_str or "quota" in err_str or "503" in err_str or "unavailable" in err_str:
                print(f"Gemini limit/overload for '{title_context}'. Falling back to OpenAI...", flush=True)
            else:
                print(f"Gemini error for '{title_context}': {e}. Halting execution!", flush=True)
                raise e

    # 2. OpenAI
    openai_client = get_openai_client()
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI error/limit for '{title_context}': {e}. Falling back to DeepSeek...", flush=True)

    # 3. DeepSeek
    deepseek_client = get_deepseek_client()
    if deepseek_client:
        try:
            response = deepseek_client.chat.completions.create(
                model=deepseek_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"DeepSeek error for '{title_context}': {e}. Halting execution!", flush=True)
            raise e
            
    raise Exception(f"All LLM APIs failed or are unconfigured for '{title_context}'")

def score_article(article, config):
    prompt = f"""
    You are an expert industry analyst and VC. Evaluate this tech news article based on the dual-track criteria.
    
    Target Industries: {', '.join([ind['name'] for ind in config.get('industries', [])])}
    
    Criteria:
    {config.get('importance_criteria', '')}
    
    Article Title: {article['title']}
    Article Summary: {article['summary']}
    Current Date: {datetime.now().strftime('%Y-%m-%d')}
    
    Tasks:
    1. Determine if this article is relevant to the tech industry (True/False). 
       **CRITICAL REJECTION RULES: You MUST set is_relevant to False if the article is:**
       - A news roundup, summary, or digest (e.g., "Top 10 news", "Morning brief", "Weekly digest", "8点1氪", "氪星晚报", "晚报").
       - A shopping deal, discount, or advertisement (e.g., "Prime Day deals", "Black Friday", "Save $50 on...", "优惠精选", "购物指南").
       - Re-hashed old news or an old event being re-reported as new (e.g., "炒冷饭" - a breakthrough or event that actually happened months or years prior to the Current Date). If you recognize the event as historical relative to the Current Date, YOU MUST REJECT IT by setting is_relevant to False.
    2. If relevant, score its 'innovation_score' (0-10).
    3. Score its 'traffic_score' (0-10).
    4. Provide a concise 1-sentence justification explaining the scores in {config.get('output', {}).get('language', 'Chinese')}.
    5. Provide the translation of the 'Article Title' into {config.get('output', {}).get('language', 'Chinese')}.
    6. Provide a HIGHLY CONDENSED summary of the article content. **CRITICAL RULE: The translated_summary MUST be ONE SINGLE SENTENCE and MUST NOT exceed 50 Chinese characters. Be extremely brief.**
    
    You must output strictly in JSON format matching this schema:
    {{
      "is_relevant": boolean,
      "innovation_score": integer,
      "traffic_score": integer,
      "justification": string,
      "translated_title": string,
      "translated_summary": string
    }}
    """
    
    result = _call_llm_with_fallback(prompt, config, title_context=article['title'][:30])
    if result:
        return result
        
    return {"innovation_score": 0, "traffic_score": 0, "justification": "All API endpoints failed or unconfigured", "is_relevant": False, "translated_title": article['title'], "translated_summary": "Error"}

def deduplicate_articles(articles, config):
    if len(articles) <= 1:
        return articles
        
    payload = []
    for idx, a in enumerate(articles):
        sd = a.get('score_data', {})
        payload.append({
            "id": idx,
            "title": sd.get('translated_title', a['title']),
            "summary": sd.get('translated_summary', a['summary']),
            "source": a['source'],
            "link": a['link'],
            "published_at": a.get('published_at', ''),
            "innovation_score": sd.get('innovation_score', 0),
            "traffic_score": sd.get('traffic_score', 0)
        })
        
    prompt = f"""
    You are an expert tech editor. Your task is to review the following top news articles and merge those that report on the EXACT SAME EVENT.
    If multiple articles are about the same event/announcement, merge them into a single article.
    If an article is unique, keep it as its own entry.
    
    When merging:
    1. 'translated_title': Create a comprehensive title in {config.get('output', {}).get('language', 'Chinese')}.
    2. 'translated_summary': Write a merged summary capturing all perspectives. **CRITICAL RULE: The translated_summary MUST be ONE SINGLE SENTENCE and MUST NOT exceed 50 Chinese characters. Be extremely brief.**
    3. 'innovation_score': Keep the MAX innovation_score among the merged articles.
    4. 'traffic_score': Keep the MAX traffic_score among the merged articles. CRITICAL: If merging from MULTIPLE DIFFERENT sources, add +1 to the final traffic_score for every additional unique source (up to a max of 10).
    5. 'justification': Combine the justifications.
    6. 'source': Combine the sources (e.g. "TechCrunch, 36氪").
    7. 'link': Provide a SINGLE primary URL (pick the best one, do NOT combine multiple URLs).
    8. 'published_at': Keep the earliest 'published_at' among the merged articles.
    
    Output strictly in JSON format matching this schema:
    {{
      "merged_articles": [
        {{
          "translated_title": string,
          "translated_summary": string,
          "innovation_score": integer,
          "traffic_score": integer,
          "justification": string,
          "source": string,
          "link": string,
          "published_at": string
        }}
      ]
    }}
    
    Input Articles JSON:
    {json.dumps(payload, ensure_ascii=False)}
    """
    
    result_json = _call_llm_with_fallback(prompt, config, title_context="Deduplication Phase")
    
    if not result_json:
        return articles

    final_articles = []
    
    for ma in result_json.get("merged_articles", []):
        final_articles.append({
            "title": ma.get("translated_title", ""),
            "summary": ma.get("translated_summary", ""),
            "source": ma.get("source", ""),
            "link": ma.get("link", ""),
            "published_at": ma.get("published_at", ""), 
            "score_data": {
                "is_relevant": True,
                "innovation_score": ma.get("innovation_score", 0),
                "traffic_score": ma.get("traffic_score", 0),
                "justification": ma.get("justification", ""),
                "translated_title": ma.get("translated_title", ""),
                "translated_summary": ma.get("translated_summary", "")
            }
        })
    return final_articles
