![GitHub](https://img.shields.io/github/license/brightbock/lambda-layers-python) ![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/brightbock/lambda-layers-python) ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/brightbock/lambda-layers-python/terraform.yml?branch=main)

# Lambda Layers for Python

## How to use:

1. Add a module definition to your Terraform. See the example below.

```
module "lambda_layers_python" {
  source                = "git::https://github.com/brightbock/lambda-layers-python.git?ref=v0.1.0"
  # providers             = { aws = aws.use1 }
}
```

