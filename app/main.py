from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.routers import auth, users, admin, payments, funds
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(title="Fund Management System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(funds.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(payments.router)

# Root redirect
@app.get("/")
async def root(request: Request):
    from fastapi import Request as FastAPIRequest
    # Check if user is logged in
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse(url="/funds")
    return RedirectResponse(url="/login")

# Custom middleware to handle token from cookie
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.datastructures import MutableHeaders

class CookieAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        # Check if token is in cookie and add to header if not present
        token = request.cookies.get("access_token")
        if token and "authorization" not in request.headers:
            # Modify headers to include authorization
            headers = MutableHeaders(request._headers)
            headers["authorization"] = f"Bearer {token}"
            request._headers = headers
        response = await call_next(request)
        return response

app.add_middleware(CookieAuthMiddleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3434)

