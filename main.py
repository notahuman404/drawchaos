import socketio
import uvicorn 

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os 
basdir = os.getcwd()
sio = socketio.AsyncServer(async_mode = "asgi", cors_allowed_origins='*')
app = FastAPI()
socket_app = socketio.ASGIApp(sio, other_asgi_app = app)
app.mount(f"{basdir}/static", StaticFiles(directory=f"{basdir}/static"), name="static")

@app.get("/")
async def root(request: Request):
#    return FileResponse(f"{basdir}/static/templates/index.html")
    return JSONResponse({"message": "Basic structure working"})
if __name__ == "__main__":
    uvicorn.run("main:socket_app", host="0.0.0.0", port=8000, reload=True)