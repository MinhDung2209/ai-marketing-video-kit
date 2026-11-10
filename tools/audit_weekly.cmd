@echo off
rem Kiem URL danh muc am thanh + meme hang tuan (Task Scheduler "KitAuditWeb"). Log: D:\agent-cache\kit-audit.log
cd /d D:\Projects\ai-marketing-video-kit
echo ==== %date% %time% >> D:\agent-cache\kit-audit.log
.venv\Scripts\python.exe -X utf8 tools\audio_harvest.py audit >> D:\agent-cache\kit-audit.log 2>&1
