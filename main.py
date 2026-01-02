from fastapi import FastAPI
import uvicorn
from schemas import NotionEvent
import services

app = FastAPI()
	
# NOTION WEBHOOK LISTENER
@app.post("/webhook")
async def receive_webhook(payload: dict):
	raw_data = services.parse_notion_payload(payload)
	if not raw_data:
		return {"status": "ignored"}
	
	event = NotionEvent(**raw_data)

	print(f"\n--- New Input: {event.title} ---")

	ai_decision = services.analyze_task(event.title)

	if ai_decision:
		await services.update_notion_task(event.id, ai_decision)

	return {"status": "received"}	

@app.get("/")
async def root():
	return {"message": "Server is running..."}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)