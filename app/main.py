from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes import temperature, geocoding

app = FastAPI(
    title="Climate Change Explorer API",
    description="""
    Air Quality Monitoring and Climate Data API providing real-time environmental data,
    historical temperature trends, snow/frost statistics, and reverse geocoding services.
    """,
    version="1.0.0",
    servers=[
        {"url": "http://localhost:8000", "description": "Local development server"},
        {"url": "http://188.245.105.237:8000", "description": "External Weather API server"}
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(temperature.router)
app.include_router(geocoding.router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for health check"""
    return {
        "status": "ok",
        "message": "Climate Change Explorer API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Global exception handler for HTTPExceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "message": "An unexpected error occurred",
            "code": "INTERNAL_SERVER_ERROR"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

