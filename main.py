from fastapi import FastAPI
import uvicorn
from schemas import NotionEvent
import services

app = FastAPI()
	
# NOTION WEBHOOK LISTENER
@app.post("/webhook")
async def receive_webhook(payload: dict):
	data = services.parse_notion_payload(payload)
	if not data:
		return {"status": "ignored"}
	
	event = NotionEvent(**data)

	category, confidence = services.classify_task(event.title)

	extracted_date, has_time = services.extract_date(event.title)

	print(f"Event: {event.title}")
	print(f"AI Prediction: {category} ({round(confidence * 100)}% confidence)")
	if extracted_date:
		print(f"Date detected: {extracted_date}")

	if confidence >= 0.4:
		print("Updating Notion...")
		success = await services.update_notion_task(event.id, category, extracted_date)
		print("Update complete!" if success[0] else f"Update failed! {success[1]}")
	else:
		print(f"Low confidence, update skipped.")

	print("-----------------------------\n")

	return {"status": "received"}	

@app.get("/")
async def root():
	return {"message": "Server is running..."}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)