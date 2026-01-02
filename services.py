import os
import httpx
import json
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai
from google.genai import types
import typing_extensions as typing
from schemas import TaskExtraction

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2025-09-03"
}

client = genai.Client(api_key=GEMINI_API_KEY)

def analyze_task(text: str) -> TaskExtraction:
	eastern_tz = ZoneInfo("America/New_York")
	now = datetime.now(eastern_tz)
	current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
	day_of_week = now.strftime("%A")

	prompt = f"""
	You are an elite Chief of Staff. Analyze this raw thought from your boss:
	"{text}"

	**CRITICAL CONTEXT:**
	- Current Date/Time: {current_time_str} ({day_of_week})
	- Timezone: US Eastern Time (New York)

	**INSTRUCTIONS:**
	1. **Category**: Pick one of ["Errand", "Health & Life", "University Work", "Extracurricular Work", "Chores", 
		   		"Hobby", "Social Event", "Physical Activity"].
    2. **Priority**: [High, Medium, Low].
    3. **Due Date**: Extract the absolute ISO 8601 date/time (YYYY-MM-DDTHH:MM:SS). 
       - Assume "tomorrow" is relative to the current date.
       - If a time is mentioned (e.g., "at 5pm"), include it.
       - If NO time is mentioned, default to 23:59:00 (End of Day).
       - Return null if no date is found.
    4. **Summary**: A crisp 3-5 word title for the task.
    5. **Is Urgent**: True if the language implies stress or immediate deadlines.
    """

	try:
		response = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=TaskExtraction,
                temperature=0.1 
            )
        )
		
		data = json.loads(response.text)

		if data.get("due_date_iso"):
			naive_dt = datetime.fromisoformat(data["due_date_iso"])
			aware_dt = naive_dt.replace(tzinfo=eastern_tz)
			data["due_date_iso"] = aware_dt.isoformat()
	
		print(f"Gemini 3 Thought: {data}")
		return data
	except Exception as e:
		print(f"AI Error: {e}")
		return None

async def update_notion_task(page_id: str, data: dict) -> typing.Tuple[bool, str]:
	url = f"https://api.notion.com/v1/pages/{page_id}"
	properties = {
		"Category": { "select": {"name": data.get("category", "Chores") } },
		"Priority": { "select": {"name": data.get("priority", "Medium") } },
	}
	if data.get("summary"):
		properties["Name"] = { "title": [{ "text": { "content": data['summary'] } }] }
	
	if data.get("due_date_iso"):
		properties["Due date"] = {
		"date": { "start": data["due_date_iso"] }
	}
	
	payload = { "properties": properties }

	async with httpx.AsyncClient() as client:
		response = await client.patch(url, json=payload, headers=headers)
		if response.status_code != 200:
			print(f"Notion Error: {response.text}")
		else:
			print("Notion Updated Successfully")
		return (response.status_code == 200)
	
# normalization layer - cleans notion payload JSON
def parse_notion_payload(payload: dict):
	try:
		data = payload.get("data", {})
		page_id = data.get('id', "")

		props = data.get('properties', {})
		name_list = props.get("Name", {}).get("title", [])
		raw_text = "".join([t.get("plain_text", "") for t in name_list])

		if not page_id or not raw_text:
			return None
        
		return {'id': page_id, "title": raw_text}
	except Exception as e:
		print(f"Error parsing: {e}")
		return None