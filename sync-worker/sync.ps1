$ErrorActionPreference = "Stop"

$mockApiUrl = "http://localhost:8003/api/v1/products/"
$visionUrl = "http://localhost:8002/vectorize"
$storeId = "b632373b-398a-4e21-9b17-a99b511f8c47"

Write-Host "Fetching products from Mock API..."
try {
    $response = Invoke-RestMethod -Uri $mockApiUrl -Headers @{"X-Store-ID"=$storeId} -Method Get
} catch {
    Write-Host "Failed to fetch products: $_"
    exit 1
}

$successCount = 0
$failCount = 0

foreach ($product in $response) {
    $productId = $product.id
    $shopId = $product.store_id

    foreach ($variation in $product.variations) {
        $imageUrl = $variation.image
        
        if ([string]::IsNullOrWhiteSpace($imageUrl)) {
            continue
        }

        Write-Host "Vectorizing Image for product: $productId (Variation: $($variation.id))..."
        $body = @{
            image_url = $imageUrl
            product_id = [string]$productId
            shop_id = [string]$shopId
        } | ConvertTo-Json

        try {
            $visionRes = Invoke-RestMethod -Uri $visionUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
            Write-Host "  -> Success: $($visionRes.status)"
            $successCount++
        } catch {
            Write-Host "  -> Failed: $_"
            $failCount++
        }
    }
}

Write-Host "Sync Complete! Success: $successCount, Failed: $failCount"
