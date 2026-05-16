@echo off
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="CLOUDFLARE_API_TOKEN" set CLOUDFLARE_API_TOKEN=%%b
)
npx wrangler deploy
echo.
echo ✅ Worker deployed!
pause