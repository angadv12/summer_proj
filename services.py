import httpx
from transformers import pipeline
from dateparser.search import search_dates
from datetime import datetime
import os

from dotenv import load_dotenv
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2025-09-03"
}

## brain - zero-shot classifer
print('Loading zero-shot model...')
LABELS = ["Health & Life", "University Work", "Personal Work", "Chores", 
		   		"Hobby", "Social Event", "Physical Activity"]
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
print('Model loaded!')

def classify_task(text: str):
	# zero-shot classification
	result = classifier(
		text,
		LABELS,
		multi_label=False,
		hypothesis_template="The topic of this task is {}."
	)
	return result['labels'][0], result['scores'][0]

def extract_date(text: str):
	matches = search_dates(text, languages=['en'], settings={'PREFER_DATES_FROM': 'future'})
	if matches:
		date_text, dt_obj = matches[-1]
		return dt_obj.isoformat(), True
	
	return None, False

async def update_notion_task(page_id: str, ai_tag: str, due_date: str = None):
	url = f"https://api.notion.com/v1/pages/{page_id}"
	properties = {
		"Category": { "select": {"name": ai_tag } }
	}
	if due_date:
		properties["Due date"] = {
			"date": { "start": due_date }
		}
	payload = { "properties": properties }

	async with httpx.AsyncClient() as client:
		response = await client.patch(url, json=payload, headers=headers)
		return (response.status_code == 200), response.text # True if success
	
# normalization layer - cleans notion payload JSON
def parse_notion_payload(payload: dict):
	try:
		data = payload.get("data", {})
		page_id = data.get("id", "")
		props = data.get("properties", {})

		name_list = props.get("Name", {}).get("title", [])
		title = "".join([t.get("plain_text", "") for t in name_list])
		
		return {
			'id': page_id,
			"title": title,
		}
	except Exception as e:
		print(f"Error parsing: {e}")
		return None