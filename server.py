from fastapi import FastAPI
from pydantic import BaseModel
import json
import uvicorn

app = FastAPI()

# 1. normalization layer - incoming notion payload
def parse_notion_payload(payload: dict):
	try:
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

# 2. LISTENER - webhook endpoint
@app.post("/webhook")
async def receive_webhook(payload: dict):
	clean_data = parse_notion_payload(payload)

	if not clean_data:
		print("Received invalid or empty data")
		return {"status": "ignored"}
	
	print("\n--- New Event Detected ---")
	print(f"Task:   		{clean_data['title']}")
	print(f"Days Remaining:	{clean_data['days_remaining']}")
	print(f"Due:    		{clean_data['due_date']}")
	print(f"Status: 		{clean_data['status']}")
	print(f"Priority: 		{clean_data['priority']}")
	print(f"Task Type:   	{clean_data['task_type']}")
	print("-----------------------------\n")

	return {"status": "received"}

@app.get("/")
async def root():
	return {"message": "Server is running..."}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)