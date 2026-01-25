# Quick Start Guide

## Installation

1. **Run setup**

   ```batch
   setup.bat
   ```

2. **Add API key**
   - Open `.env` file
   - Add: `OPENAI_API_KEY=your-key-here`

3. **Start system**

   ```batch
   start.bat
   ```

4. **Access dashboard**
   - Open: http://localhost:8501

## Usage

### Upload Documents

1. Click "Browse files" in sidebar
2. Select PDF, DOCX, TXT, or MD files
3. Click "Upload All"

### Ask Questions

1. Type question in chat input
2. Click "Ask"
3. View answer with citations

### Manage Documents

- View uploaded documents in sidebar
- Check system statistics
- Delete documents as needed

## Troubleshooting

### API Won't Start

```batch
# Check if port is in use
netstat -ano | findstr :8001

# Kill process if needed
taskkill /PID <process_id> /F
```

### Import Errors

```batch
pip install -r requirements.txt --force-reinstall
```

### Dashboard Can't Connect

1. Verify API is running: http://localhost:8001/health
2. Check `.env` has correct API_PORT
3. Restart both services

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [docs/API.md](docs/API.md) for API reference
- See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment
