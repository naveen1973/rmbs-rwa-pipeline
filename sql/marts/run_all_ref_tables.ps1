# Run all ref_* table creation scripts against BigQuery
# Usage: .\run_all_ref_tables.ps1

$scripts = @(
    "ref_occupancy.sql",
    "ref_account_status.sql",
    "ref_employment_status.sql",
    "ref_income_verification.sql",
    "ref_origination_channel.sql",
    "ref_loan_purpose.sql",
    "ref_shared_ownership.sql",
    "ref_repayment_method.sql",
    "ref_payment_frequency.sql",
    "ref_lien.sql",
    "ref_interest_rate_type.sql",
    "ref_interest_rate_index.sql",
    "ref_forbearance_type.sql",
    "ref_region.sql",
    "ref_property_type.sql",
    "ref_valuation_type.sql",
    "ref_epc_rating.sql",
    "ref_postcode_to_region.sql"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

foreach ($script in $scripts) {
    $path = Join-Path $scriptDir $script
    Write-Host "Running $script..." -ForegroundColor Cyan
    Get-Content $path | bq query --use_legacy_sql=false
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK" -ForegroundColor Green
    } else {
        Write-Host "  FAILED" -ForegroundColor Red
    }
}

Write-Host "`nDone. Check rmbs_marts dataset in BigQuery console." -ForegroundColor Yellow
