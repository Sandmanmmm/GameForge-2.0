"""
Minimal test to debug the lifespan manager issue
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test lifespan manager"""
    print("🚀 Starting test application...")
    
    # Simple startup tasks
    await asyncio.sleep(0.1)  # Simulate startup time
    
    print("🎉 Test application startup complete!")
    
    try:
        yield
        print("📱 Application is running...")
    except Exception as e:
        print(f"❌ Error during runtime: {e}")
        raise
    finally:
        print("🛑 Shutting down test application...")
        await asyncio.sleep(0.1)  # Simulate cleanup
        print("👋 Test application shutdown complete!")


def create_test_app() -> FastAPI:
    """Create test FastAPI app"""
    app = FastAPI(
        title="Test App",
        lifespan=test_lifespan
    )
    
    @app.get("/")
    async def root():
        return {"message": "Hello World"}
    
    return app


app = create_test_app()