param(
    [string]$TargetPath = ".env",
    [string]$ExamplePath = ".env.example"
)

if (-not (Test-Path $ExamplePath)) {
    Write-Error "未找到示例文件 $ExamplePath"
    exit 1
}

if (Test-Path $TargetPath) {
    Write-Output "已存在 $TargetPath，无需创建。"
    exit 0
}

Copy-Item $ExamplePath $TargetPath
Write-Output "已根据 $ExamplePath 创建 $TargetPath。请按需修改其中的配置值。"