# Run the API first:  python -m api.server
# Then run:           powershell -ExecutionPolicy Bypass -File scripts\curl_tests.ps1
# Uses curl.exe (built into Windows 10/11), not the PowerShell "curl" alias.
$Base = "http://127.0.0.1:8000"
$User = if ($env:MOMO_API_USER) { $env:MOMO_API_USER } else { "admin" }
$Pass = if ($env:MOMO_API_PASS) { $env:MOMO_API_PASS } else { "password123" }
Set-Location $PSScriptRoot

Write-Host "=== 1. GET all transactions (valid credentials) ===" -ForegroundColor Cyan
curl.exe -i -u "${User}:${Pass}" "$Base/transactions"

Write-Host "`n=== 2. GET one transaction ===" -ForegroundColor Cyan
curl.exe -i -u "${User}:${Pass}" "$Base/transactions/1"

Write-Host "`n=== 3. Unauthorized: wrong credentials ===" -ForegroundColor Cyan
curl.exe -i -u "admin:wrongpass" "$Base/transactions"

Write-Host "`n=== 4. POST new transaction ===" -ForegroundColor Cyan
curl.exe -i -u "${User}:${Pass}" -X POST -H "Content-Type: application/json" --data "@new_transaction.json" "$Base/transactions"

Write-Host "`n=== 5. PUT update transaction 1 ===" -ForegroundColor Cyan
curl.exe -i -u "${User}:${Pass}" -X PUT -H "Content-Type: application/json" --data "@update_transaction.json" "$Base/transactions/1"

Write-Host "`n=== 6. DELETE transaction 2 ===" -ForegroundColor Cyan
curl.exe -i -u "${User}:${Pass}" -X DELETE "$Base/transactions/2"

Write-Host "`n=== 7. GET deleted transaction (expect 404) ===" -ForegroundColor Cyan
curl.exe -i -u "${User}:${Pass}" "$Base/transactions/2"
