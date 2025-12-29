from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from transformers import pipeline
import httpx, os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

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
classifer = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
print('Model loaded!')

# normalization layer - cleans notion payload
def parse_notion_payload(payload: dict):
	try:
		page_id = payload.get("data", {}).get("id", "")
		properties = payload.get("data", {}).get("properties", {})
		name_list = properties.get("Name", {}).get("title", [])
		task_type_list = properties.get("Task type", {}).get("multi_select", [])

		title = "".join([t.get("plain_text", "") for t in name_list])
		days_remaining = properties.get("Days remaining", {}).get("formula", {}).get("string", "Unknown")
		due_date_data = properties.get("Due date", {}).get("date", {})
		due_date = due_date_data.get("start") if due_date_data else "No due date"
		status = properties.get("Status", {}).get("status", {}).get("name", "Unknown")
		priority = properties.get("Priority", {}).get("select", {}).get("name", "Unknown")
		task_type = "".join([t.get("name", "") for t in task_type_list])

		return {
			'id': page_id,
			"title": title,
			"days_remaining": days_remaining,
			"due_date": due_date,
			"status": status,
			"priority": priority,
			"task_type": task_type
		}
	except Exception as e:
		print(f"Error parsing payload: {e}")
		return None

async def update_notion_task(page_id: str, ai_tag: str):
	url = f"https://api.notion.com/v1/pages/{page_id}"
	payload = {
        "properties": {
            "AI Category": {
                "select": {
                    "name": ai_tag
                }
            }
        }
    }

	async with httpx.AsyncClient() as client:
		response = await client.patch(url, json=payload, headers=headers)
		if response.status_code == 200:
			print(f"Successfully updated Notion page {page_id} with '{ai_tag}'")
		else:
			print(f"Failed to update Notion: {response.status_code} - {response.text}")

# LISTENER - webhook endpoint
@app.post("/webhook")
async def receive_webhook(payload: dict):
	clean_data = parse_notion_payload(payload)

	if not clean_data:
		print("Received invalid or empty data")
		return {"status": "ignored"}
	
	# zero-shot classification
	ai_result = classifer(clean_data['title'], LABELS, multi_label=False)
	ai_category = ai_result['labels'][0]
	ai_confidence = ai_result['scores'][0]
	
	print("\n--- New Event Detected ---")
	print(f"Task:   		{clean_data['title']}")
	print(f"Due:    		{clean_data['due_date']}")
	print(f"AI Assessment:	{ai_category} ({round(ai_confidence * 100)}% confidence)")
	print("-----------------------------\n")	

	if ai_confidence >= 0.4:
		print("Updating Notion with AI category...")
		await update_notion_task(clean_data['id'], ai_category)
	else:
		print(f"AI confidence ({round(ai_confidence * 100)}%) too low, update skipped.")

	print("-----------------------------\n")

	return {"status": "received", "updated": True}	

@app.get("/")
async def root():
	return {"message": "Server is running..."}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)