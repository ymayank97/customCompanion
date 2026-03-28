# Installation Guide

Complete step-by-step installation guide for the CBIC Customs Data Scraper.

## System Requirements

- Python 3.8 or higher
- Internet connection
- 500 MB free disk space
- Windows, macOS, or Linux

## Step 1: Verify Python Installation

```bash
python --version
# Should show: Python 3.8.x or higher
```

If Python is not installed:
- **Windows:** Download from [python.org](https://www.python.org/downloads/)
- **macOS:** `brew install python3`
- **Linux:** `sudo apt-get install python3 python3-pip`

## Step 2: Navigate to Project Directory

```bash
cd "C:\Users\Mayank\OneDrive\Desktop\Workspace\Projects\cth finder\backend\scraper"
```

Or on macOS/Linux:
```bash
cd "/path/to/cth finder/backend/scraper"
```

## Step 3: Create Virtual Environment (Recommended)

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

## Step 4: Install Required Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- requests (HTTP client)
- beautifulsoup4 (HTML parsing)
- lxml (XML/HTML parser)
- pdfplumber (PDF processing)
- pandas (data handling)
- python-dateutil (date utilities)
- python-dotenv (environment config)

**Expected output:**
```
Successfully installed beautifulsoup4-4.12.0 lxml-4.9.0 pdfplumber-0.10.0 requests-2.31.0 ...
```

## Step 5: Install Optional Dependencies

### For Indian Trade Portal (JavaScript-heavy site)

```bash
pip install playwright
playwright install chromium
```

This downloads Chromium browser (~200 MB).

## Step 6: Verify Installation

Run the test suite:

```bash
python test_scraper.py
```

Expected output:
```
# CBIC CUSTOMS DATA SCRAPER - TEST SUITE

TEST 1: Import Verification
  ✓ scrape_cbic imported
  ✓ utils imported
  ✓ config imported
  ...

TEST SUMMARY
  ✓ PASS - Imports
  ✓ PASS - Utilities
  ✓ PASS - Configuration
  ...

🎉 All tests passed!
```

## Step 7: Configure (Optional)

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to customize settings:
```bash
# Windows
notepad .env

# macOS/Linux
nano .env
```

## Step 8: Test Scraping

Run a quick test:

```bash
python scrape_cbic.py
```

This will:
- Scrape chapter 01
- Fetch recent notifications
- Parse a sample PDF

**Note:** First run takes 10-15 seconds due to rate limiting.

## Troubleshooting

### Issue: "pip: command not found"

**Solution:** Use `python -m pip` instead:
```bash
python -m pip install -r requirements.txt
```

### Issue: "Permission denied"

**Solution:** Run with user flag:
```bash
pip install --user -r requirements.txt
```

### Issue: "SSL Certificate Error"

**Solution:** Upgrade pip and certifi:
```bash
pip install --upgrade pip certifi
```

### Issue: "playwright: command not found"

**Solution:** Install playwright after pip package:
```bash
pip install playwright
python -m playwright install chromium
```

### Issue: Virtual environment not activating

**Windows PowerShell:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

### Issue: Import errors after installation

**Solution:** Verify you're in virtual environment:
```bash
which python  # Should show venv path
pip list      # Should show installed packages
```

## Verification Checklist

Before using the scraper, verify:

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] All required packages installed (`pip list`)
- [ ] Test suite passes (`python test_scraper.py`)
- [ ] Configuration file created (optional)
- [ ] Internet connection working

## Next Steps

Once installation is complete:

1. **Quick start:** Read [QUICKSTART.md](QUICKSTART.md)
2. **Full documentation:** Read [README.md](README.md)
3. **Run examples:** `python example_usage.py`
4. **Start scraping:** `python scrape_cbic.py`

## Uninstallation

To remove the scraper:

1. Deactivate virtual environment:
   ```bash
   deactivate
   ```

2. Delete virtual environment:
   ```bash
   # Windows
   rmdir /s venv

   # macOS/Linux
   rm -rf venv
   ```

3. Delete project directory (if desired)

## Getting Help

If installation fails:

1. Check Python version: `python --version`
2. Check pip version: `pip --version`
3. Review error messages carefully
4. Check internet connection
5. Try updating pip: `pip install --upgrade pip`
6. Try without virtual environment (not recommended)

## Platform-Specific Notes

### Windows
- Use `python` (not `python3`)
- Use `\` for paths (or `/` works too)
- Activate venv: `venv\Scripts\activate`

### macOS/Linux
- Use `python3` (not `python`)
- Use `/` for paths
- Activate venv: `source venv/bin/activate`
- May need sudo for system-wide installs

### Proxy/Firewall Issues

If behind corporate proxy:

```bash
# Set proxy
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"

# Install with proxy
pip install --proxy http://proxy.company.com:8080 -r requirements.txt
```

## Updating

To update to latest version:

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Update packages
pip install --upgrade -r requirements.txt
```

## Development Setup

For development/contribution:

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Run code formatter
black scrape_cbic.py utils.py

# Run linter
flake8 scrape_cbic.py

# Run type checker
mypy scrape_cbic.py
```

## System Resources

Expected resource usage:
- **Disk:** 500 MB (packages + data)
- **RAM:** 100-200 MB during operation
- **Network:** Minimal (respects rate limits)
- **CPU:** Low (I/O bound operations)

## Security Considerations

- Never commit `.env` file to version control
- Store API keys/passwords securely
- Review scraped data before sharing
- Follow data protection regulations

## Support

For installation issues:
- Check error logs: `scrape_errors.log`
- Review this guide
- Check Python/pip versions
- Verify internet connectivity
