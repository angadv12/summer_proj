import httpx
from transformers import pipeline
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
	result = classifier(text, LABELS, multi_label=False)
	return result['labels'][0], result['scores'][0]

async def update_notion_task(page_id: str, ai_tag: str):
	url = f"https://api.notion.com/v1/pages/{page_id}"
	payload = {
        "properties": {
            "Category": {
                "select": {
                    "name": ai_tag
                }
            }
        }
    }
	async with httpx.AsyncClient() as client:
		response = await client.patch(url, json=payload, headers=headers)
		return response.status_code == 200 # True if success
	
# normalization layer - cleans notion payload JSON
def parse_notion_payload(payload: dict):
	try:
		page_id = payload.get("data", {}).get("id", "")
		props = payload.get("data", {}).get("properties", {})

		name_list = props.get("Name", {}).get("title", [])
		title = "".join([t.get("plain_text", "") for t in name_list])
		
		days_remaining = props.get("Days remaining", {}).get("formula", {}).get("string", "Unknown")
		due_date_data = props.get("Due date", {}).get("date", {})
		due_date = due_date_data.get("start") if due_date_data else "No due date"
		priority = props.get("Priority", {}).get("select", {}).get("name", "Unknown")

		return {
			'id': page_id,
			"title": title,
			"days_remaining": days_remaining,
			"due_date": due_date,
			"priority": priority,
		}
	except Exception as e:
		print(f"Error parsing payload: {e}")
		return None