from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import asyncio
import json
from datetime import datetime

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store data in memory
users = {}
active_bets = {}

@app.get("/")
async def root():
    return {"message": "Solana Betting API is running"}

async def fetch_trending_solana():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.dexscreener.com/latest/dex/tokens/solana') as response:
                data = await response.json()
                pairs = data.get('pairs', [])
                sorted_pairs = sorted(
                    pairs, 
                    key=lambda x: float(x.get('volume', {}).get('h24', 0)), 
                    reverse=True
                )
                return sorted_pairs[:10]
    except Exception as e:
        print(f"Error fetching trending: {e}")
        return []

@app.get("/api/trending")
async def get_trending():
    return await fetch_trending_solana()

@app.get("/api/user/{user_id}")
async def get_user(user_id: str):
    if user_id not in users:
        users[user_id] = {
            "balance": 1000,
            "bets": []
        }
    return users[user_id]

@app.post("/api/bet")
async def place_bet(user_id: str, token: str, amount: float, direction: str):
    if user_id not in users:
        return {"error": "User not found"}
    
    user = users[user_id]
    if amount > user["balance"]:
        return {"error": "Insufficient balance"}
    
    bet_id = f"bet_{len(user['bets'])}"
    bet = {
        "id": bet_id,
        "token": token,
        "amount": amount,
        "direction": direction,
        "timestamp": str(datetime.now()),
        "status": "active"
    }
    
    user["balance"] -= amount
    user["bets"].append(bet)
    
    return {"success": True, "bet": bet, "balance": user["balance"]}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            trending = await fetch_trending_solana()
            await websocket.send_json({
                "type": "trending",
                "data": trending
            })
            await asyncio.sleep(10)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)