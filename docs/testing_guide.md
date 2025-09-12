# GameForge Testing Guide
Generated: 2025-09-04T16:24:36.360931

## 🧪 Local Testing (No Docker Required)

### Prerequisites
1. Python 3.8+ installed
2. Git repository cloned
3. Virtual environment activated

### Quick Start
```bash
# Windows
start_local_server.bat

# Linux/Mac  
chmod +x start_local_server.sh
./start_local_server.sh
```

### Manual Setup
```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start server
python gameforge_production_server.py
```

## 🔍 Testing Endpoints

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0"
}
```

### API Documentation
Visit: http://localhost:8000/docs

### Test Asset Generation (requires GPU)
```bash
curl -X POST http://localhost:8000/api/v1/assets/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "medieval sword",
    "category": "weapons"
  }'
```

## 🗄️ Database Testing (Optional)

### Install PostgreSQL locally
```bash
# Windows: Download from postgresql.org
# Mac: brew install postgresql
# Ubuntu: sudo apt install postgresql
```

### Setup database
```bash
psql -U postgres -f database_setup.sql
```

### Test connection
```python
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    database="gameforge_production", 
    user="gameforge_prod",
    password="your_password"
)
print("Database connected!")
```

## 🔴 Redis Testing (Optional)

### Install Redis locally
```bash
# Windows: Download from redis.io
# Mac: brew install redis
# Ubuntu: sudo apt install redis-server
```

### Start Redis
```bash
redis-server
```

### Test connection
```python
import redis
r = redis.Redis(host='localhost', port=6379)
r.ping()  # Should return True
```

## 🚀 Production Testing Checklist

### Basic Functionality
- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] API documentation loads
- [ ] Authentication endpoints work
- [ ] Rate limiting functions

### GPU Integration
- [ ] Vast.ai instance is running
- [ ] GPU endpoint accessible
- [ ] Asset generation works
- [ ] GPU utilization monitored

### Security Testing
- [ ] JWT authentication works
- [ ] API keys function correctly
- [ ] Rate limiting enforced
- [ ] CORS policies applied

### Performance Testing
- [ ] Response times acceptable
- [ ] Memory usage stable
- [ ] Concurrent requests handled
- [ ] Error handling works

## 🐛 Troubleshooting

### Common Issues

#### "Module not found" errors
```bash
pip install -r requirements.txt
```

#### "Permission denied" on scripts
```bash
chmod +x start_local_server.sh
```

#### "Port already in use"
```bash
# Find process using port 8000
netstat -ano | findstr :8000
# Kill the process
taskkill /PID <process_id> /F
```

#### GPU not accessible
- Check Vast.ai instance status
- Verify GPU endpoint URL
- Test network connectivity

### Debug Mode
Start with debug logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python gameforge_production_server.py
```

## 📊 Monitoring Local Deployment

### Log Files
- Check console output for errors
- Monitor GPU utilization
- Watch memory usage

### Performance Metrics
- Response time: < 200ms for health
- Asset generation: 10-30 seconds
- Memory usage: < 2GB base

### Success Criteria
✅ Server starts and responds to health checks
✅ All endpoints accessible
✅ Authentication system works
✅ GPU integration functional (if available)
✅ No critical errors in logs

## 🎯 Next Steps
1. ✅ Local testing successful
2. 🐳 Docker deployment
3. ☸️ Kubernetes deployment  
4. 🌐 Production infrastructure
5. 🚀 Go live!
