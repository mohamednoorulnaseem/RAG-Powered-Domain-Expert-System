# 🔧 TROUBLESHOOTING GUIDE

## System Won't Start? Follow These Steps

### Option 1: Use Manual Start Script

```batch
start_manual.bat
```

This will:

1. Activate virtual environment
2. Install missing packages
3. Start API server
4. Start dashboard
5. Open browser

---

### Option 2: Start Services Individually

#### Step 1: Open Command Prompt

- Press `Win + R`
- Type `cmd`
- Press Enter

#### Step 2: Navigate to Project

```batch
cd "c:\Users\moham\All Projects\RAG-Powered Domain Expert System"
```

#### Step 3: Activate Virtual Environment

```batch
venv\Scripts\activate.bat
```

You should see `(venv)` in your prompt.

#### Step 4: Install Missing Package

```batch
pip install langchain-text-splitters
```

#### Step 5: Start API Server

```batch
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

Keep this window open. You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

#### Step 6: Open Another Command Prompt

- Open a NEW command prompt
- Navigate to project folder again
- Activate venv again

#### Step 7: Start Dashboard

```batch
streamlit run dashboard\app.py --server.port 8501
```

You should see:

```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

#### Step 8: Open Browser

Go to: http://localhost:8501

---

### Option 3: Check for Issues

#### Check if Virtual Environment Exists

```batch
dir venv
```

If you see "File Not Found", run:

```batch
setup.bat
```

#### Check if Python is Installed

```batch
python --version
```

Should show Python 3.10 or higher.

#### Check if Packages are Installed

```batch
venv\Scripts\activate.bat
pip list
```

Look for:

- fastapi
- uvicorn
- streamlit
- langchain
- langchain-text-splitters
- openai

#### Check if .env File Exists

```batch
type .env
```

Should show your OPENAI_API_KEY.

---

### Common Errors and Solutions

#### Error: "Virtual environment not found"

**Solution:**

```batch
setup.bat
```

#### Error: "Module not found: langchain_text_splitters"

**Solution:**

```batch
venv\Scripts\activate.bat
pip install langchain-text-splitters
```

#### Error: "Port already in use"

**Solution:**

```batch
# Find what's using the port
netstat -ano | findstr :8001

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F
```

#### Error: "OpenAI API key not set"

**Solution:**

1. Open `.env` file
2. Add your API key:
   ```
   OPENAI_API_KEY=your-key-here
   ```
3. Save and restart

#### Error: "Cannot import name..."

**Solution:**

```batch
venv\Scripts\activate.bat
pip install -r requirements.txt --force-reinstall
```

---

### Quick Diagnostic

Run this to check everything:

```batch
python verify_system.py
```

This will tell you exactly what's wrong.

---

### Still Not Working?

1. **Check Python Version**

   ```batch
   python --version
   ```

   Must be 3.10 or higher

2. **Reinstall Everything**

   ```batch
   rmdir /s /q venv
   setup.bat
   ```

3. **Check Logs**
   - Look in the `logs/` folder
   - Check error messages in terminal

4. **Verify Files**
   ```batch
   python test_imports.py
   ```

---

### Manual Installation (If All Else Fails)

```batch
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
venv\Scripts\activate.bat

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install requirements
pip install -r requirements.txt

# 5. Install missing package
pip install langchain-text-splitters

# 6. Verify
python verify_system.py

# 7. Start API
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001

# 8. In another terminal, start dashboard
streamlit run dashboard\app.py --server.port 8501
```

---

### Need Help?

1. Run: `python verify_system.py`
2. Check output for specific errors
3. Follow the error-specific solutions above
4. Check `.env` file has your API key

---

**Most Common Issue:** Missing `langchain-text-splitters` package

**Quick Fix:**

```batch
venv\Scripts\activate.bat
pip install langchain-text-splitters
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

Then in another terminal:

```batch
venv\Scripts\activate.bat
streamlit run dashboard\app.py --server.port 8501
```
