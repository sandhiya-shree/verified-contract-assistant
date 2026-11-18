# Verified Contract Assistant

An AI-powered Streamlit app that checks a legal contract register, flags upcoming notice deadlines, drafts reminder letters, and answers questions with verified facts.

## Features
- **Data quality checks:** flags missing fields, duplicate contract IDs, invalid dates, negative values and end dates before start dates
- **Renewal deadline alerts:** calculates each contract's notice date and flags those due within 60 days
- **Document automation:** fills a Word reminder letter template with each contract's details
- **Claude assistant:** answers questions by calling custom Python tools (Claude Agent SDK) instead of guessing
- **Validation layer:** checks dates, client names and amounts in each answer against the register, marking them ✅ verified or ⚠️ flagged

## Reusable design
All industry-specific settings (column names, currency, alert window) live in one `SETTINGS` block, so the app can be adapted to insurance policies, leases or licences by changing one section.

## Built with
Python, Streamlit, pandas, python-docx, Claude Agent SDK

## How to run
1. `pip install -r requirements.txt`
2. Sign in to Claude Code with a Claude account
3. `streamlit run app.py`
4. Upload `contract_register.csv` (sample data with deliberate errors)

*All client names in the sample data are fictional.*
