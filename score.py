import os
import time
import json
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class ArticleScore(BaseModel):
    is_relevant: bool
    innovation_score: int
    traffic_score: int
    justification: str
    translated_title: str
    translated_summary: str

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)

def score_article(article, config):
    client = get_client()
    if not client:
        return {"innovation_score": 0, "traffic_score": 0, "justification": "OpenAI API Key not configured", "is_relevant": False, "translated_title": article['title'], "translated_summary": "Error"}

    prompt = f"""
    You are an expert industry analyst and VC. Evaluate this tech news article based on the dual-track criteria.
    
    Target Industries: {', '.join([ind['name'] for ind in config.get('industries', [])])}
    
    Criteria:
    {config.get('importance_criteria', '')}
    
    Article Title: {article['title']}
    Article Summary: {article['summary']}
    
    Tasks:
    1. Determine if this article is relevant to the tech industry (True/False).
    2. If relevant, score its 'innovation_score' (0-10).
    3. Score its 'traffic_score' (0-10).
    4. Provide a concise 1-sentence justification explaining the scores in {config.get('output', {}).get('language', 'Chinese')}.
    5. Provide the translation of the 'Article Title' into {config.get('output', {}).get('language', 'Chinese')}.
    6. Provide a short summary of the article content in {config.get('output', {}).get('language', 'Chinese')}.
    
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
    
    model_name = config.get('output', {}).get('model', 'gpt-4o-mini')
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg or "rate limit" in err_msg:
                if attempt < max_retries - 1:
                    print(f"Rate limited or Timeout. Waiting 5s before retry {attempt+1}/{max_retries}...", flush=True)
                    time.sleep(5)
                    continue
            print(f"Error scoring article '{article['title']}': {e}", flush=True)
            return {"innovation_score": 0, "traffic_score": 0, "justification": f"Error: {e}", "is_relevant": False, "translated_title": article['title'], "translated_summary": "Error"}

def deduplicate_articles(articles, config):
    if len(articles) <= 1:
        return articles
        
    client = get_client()
    if not client:
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
            "published_at": a['published_at'],
            "innovation_score": sd.get('innovation_score', 0),
            "traffic_score": sd.get('traffic_score', 0),
            "justification": sd.get('justification', '')
        })
        
    prompt = f"""
    You are an expert tech editor. Your task is to review the following top news articles and merge those that report on the EXACT SAME EVENT.
    If multiple articles are about the same event/announcement, merge them into a single article.
    If an article is unique, keep it as its own entry.
    
    When merging:
    1. 'translated_title': Create a comprehensive title in {config.get('output', {}).get('language', 'Chinese')}.
    2. 'translated_summary': Write a merged summary capturing all perspectives in {config.get('output', {}).get('language', 'Chinese')}.
    3. 'innovation_score': Keep the MAX innovation_score among the merged articles.
    4. 'traffic_score': Keep the MAX traffic_score among the merged articles.
    5. 'justification': Combine the justifications.
    6. 'source': Combine the sources (e.g. "TechCrunch, 36氪").
    7. 'link': Provide a SINGLE primary URL (pick the best one, do NOT combine multiple URLs).
    
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
    
    model_name = "gpt-5.4"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        result = json.loads(response.choices[0].message.content)
        
        final_articles = []
        for ma in result.get("merged_articles", []):
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
    except Exception as e:
        print(f"Error deduplicating articles: {e}", flush=True)
        return articles
